"""Model-agnostic LLM port (Decision 0003).

Core code depends only on the ``LLMClient`` protocol. ``MockLLMClient`` is
the deterministic test double used by planner / thought / repair tests.
``LiteLLMClient`` is the optional real path (``pip install atg-framework[llm]``)
and reads the model tag from ``ATG_MODEL`` (Decision 0015) so that no paper-era
checkpoint name is ever pinned in library code.
"""

from __future__ import annotations

import json
import os
import re
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

Messages = list[dict[str, Any]]
ModelT = TypeVar("ModelT", bound=BaseModel)

StructuredHandler = Callable[[Messages, type[BaseModel], dict[str, Any]], Any]


class LLMError(RuntimeError):
    """The model could not produce a usable (structured) answer."""


class LLMClient(Protocol):
    """Chat-completions port with a structured-output method.

    ``context`` carries planner metadata (node id, attempt, reason). Real
    clients may ignore it; mocks may key scripted answers on it.
    """

    def complete(self, messages: Messages, **kwargs: Any) -> str: ...

    def complete_structured(
        self,
        messages: Messages,
        schema: type[ModelT],
        *,
        context: dict[str, Any] | None = None,
    ) -> ModelT: ...


def coerce_structured(raw: Any, schema: type[ModelT]) -> ModelT:
    """Accept a model instance, a dict, or a JSON string (optionally fenced)."""
    if isinstance(raw, schema):
        return raw
    if isinstance(raw, BaseModel):
        raw = raw.model_dump()
    if isinstance(raw, str):
        raw = json.loads(extract_json(raw))
    try:
        return schema.model_validate(raw)
    except ValidationError as exc:
        raise LLMError(f"Structured output failed validation: {exc}") from exc


def extract_json(text: str) -> str:
    """Strip Markdown fences and leading prose around the first JSON object."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


class MockLLMClient:
    """Scripted client for tests and offline demos.

    ``structured`` may be:

    * a mapping ``{context["node_id"]: response | [response, ...]}`` — lists are
      consumed one per call so retries can return different plans;
    * a sequence of responses consumed in order;
    * a callable ``(messages, schema, context) -> response``.

    Responses may be schema instances, dicts, or JSON strings.
    """

    def __init__(
        self,
        structured: Mapping[str, Any] | Sequence[Any] | StructuredHandler | None = None,
        text: Sequence[str] | None = None,
    ) -> None:
        self._by_key: dict[str, deque[Any]] | None = None
        self._queue: deque[Any] | None = None
        self._handler: StructuredHandler | None = None
        if callable(structured):
            self._handler = structured
        elif isinstance(structured, Mapping):
            self._by_key = {
                key: deque(val if isinstance(val, list) else [val])
                for key, val in structured.items()
            }
        elif structured is not None:
            self._queue = deque(structured)
        self._text = deque(text or [])
        self.calls: list[dict[str, Any]] = []

    def complete(self, messages: Messages, **kwargs: Any) -> str:
        self.calls.append({"kind": "text", "messages": messages, "kwargs": kwargs})
        if not self._text:
            raise LLMError("MockLLMClient has no scripted text responses left")
        return self._text.popleft()

    def complete_structured(
        self,
        messages: Messages,
        schema: type[ModelT],
        *,
        context: dict[str, Any] | None = None,
    ) -> ModelT:
        context = dict(context or {})
        self.calls.append(
            {
                "kind": "structured",
                "messages": messages,
                "schema": schema,
                "context": context,
            }
        )
        if self._handler is not None:
            raw = self._handler(messages, schema, context)
        elif self._by_key is not None:
            key = str(context.get("node_id"))
            bucket = self._by_key.get(key)
            if not bucket:
                raise LLMError(
                    f"MockLLMClient has no scripted response for node {key!r}"
                )
            raw = bucket[0] if len(bucket) == 1 else bucket.popleft()
        elif self._queue is not None:
            if not self._queue:
                raise LLMError(
                    "MockLLMClient has no scripted structured responses left"
                )
            raw = self._queue.popleft()
        else:
            raise LLMError("MockLLMClient was created without structured responses")
        return coerce_structured(raw, schema)


class LiteLLMClient:
    """Real client over LiteLLM (Ollama, OpenAI-compatible, ...).

    Requires the ``[llm]`` extra. Model tag comes from ``model`` or the
    ``ATG_MODEL`` environment variable (Decision 0015); nothing is pinned here.
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        temperature: float = 0.0,
        max_retries: int = 2,
        **completion_kwargs: Any,
    ) -> None:
        self.model = model or os.environ.get("ATG_MODEL")
        if not self.model:
            raise LLMError("Set ATG_MODEL (e.g. 'ollama/<tag>') or pass model=")
        self.temperature = temperature
        self.max_retries = max_retries
        self.completion_kwargs = completion_kwargs
        try:
            import litellm  # noqa: F401  (optional dependency)
        except ImportError as exc:  # pragma: no cover - depends on extras
            raise LLMError(
                "Install the [llm] extra: pip install 'atg-framework[llm]'"
            ) from exc
        self._litellm = litellm

    def complete(self, messages: Messages, **kwargs: Any) -> str:
        params = {"temperature": self.temperature, **self.completion_kwargs, **kwargs}
        response = self._litellm.completion(
            model=self.model, messages=messages, **params
        )
        return response["choices"][0]["message"]["content"] or ""

    def complete_structured(
        self,
        messages: Messages,
        schema: type[ModelT],
        *,
        context: dict[str, Any] | None = None,
    ) -> ModelT:
        schema_json = json.dumps(schema.model_json_schema(), indent=None)
        instruction = {
            "role": "system",
            "content": (
                "Respond with a single JSON object and nothing else. It must "
                f"validate against this JSON Schema:\n{schema_json}"
            ),
        }
        convo = [instruction, *messages]
        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            text = self.complete(convo, response_format={"type": "json_object"})
            try:
                return coerce_structured(text, schema)
            except (LLMError, json.JSONDecodeError) as exc:
                last_error = exc
                convo = [
                    *convo,
                    {"role": "assistant", "content": text},
                    {
                        "role": "user",
                        "content": f"That was invalid ({exc}). Return only corrected JSON.",
                    },
                ]
        raise LLMError(f"Structured output failed after retries: {last_error}")
