"""Model port. Core stays free of vendor SDKs (Decision 0003).

Structured subgraphs are JSON that validates as ``Decomposition``
(Decision 0012). ``OllamaClient`` talks to a local daemon with the
stdlib. ``OpenAICompatClient`` posts to ``/v1/chat/completions``
(Decision 0021). ``LiteLLMClient`` is the optional multi-provider adapter.
Independent reimplementation of the ATG planner's model boundary;
see docs/ATTRIBUTION.md (``zhang2026atg``).
"""

import json
import os
from typing import Any
from urllib import error, request

from pydantic import BaseModel, ValidationError

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
# Paper-scale local instruct model already installed here (Decision 0017).
# Coder-only tags and cloud tags are not the default.
DEFAULT_MODEL = "llama3.1:8b"
# Tried, in order, when the default cannot emit a valid decomposition.
FALLBACK_MODELS = ("qwen2.5:14b", "gemma4:latest")


class LLMError(Exception):
    """The model port could not return a valid completion."""


class MockLLM:
    """Scripted structured responses. Each call pops the next item."""

    def __init__(self, scripted: list[Any]) -> None:
        self.scripted = list(scripted)
        self.calls = 0

    def complete(self, messages: list[dict], **kwargs: Any) -> str:
        value = self.scripted[0] if self.scripted else ""
        if isinstance(value, BaseModel):
            return value.model_dump_json()
        return str(value)

    def complete_structured(self, messages: list[dict], schema: type[BaseModel]) -> BaseModel:
        self.calls += 1
        self.messages = messages
        if not self.scripted:
            raise LLMError("mock LLM has no scripted responses left")
        item = self.scripted.pop(0)
        if isinstance(item, schema):
            return item
        if isinstance(item, BaseModel):
            return schema.model_validate(item.model_dump())
        if isinstance(item, str):
            return schema.model_validate_json(item)
        return schema.model_validate(item)


class OllamaClient:
    """Local Ollama ``/api/chat``. ``format`` is the Pydantic JSON schema."""

    def __init__(
        self,
        model: str | None = None,
        *,
        host: str | None = None,
        timeout_s: float = 120,
    ) -> None:
        self.model = model or os.environ.get("ATG_MODEL", DEFAULT_MODEL)
        self.host = (host or os.environ.get("ATG_OLLAMA_HOST", DEFAULT_OLLAMA_HOST)).rstrip("/")
        self.timeout_s = timeout_s

    def complete(self, messages: list[dict], **kwargs: Any) -> str:
        body = self._post(messages, schema=None)
        return str(body["message"]["content"])

    def complete_structured(self, messages: list[dict], schema: type[BaseModel]) -> BaseModel:
        body = self._post(messages, schema=schema.model_json_schema())
        content = str(body["message"]["content"])
        try:
            return _parse_model(content, schema)
        except ValidationError as exc:
            raise LLMError(f"{self.model} returned invalid structured output") from exc

    def _post(self, messages: list[dict], schema: dict | None) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0},
        }
        if schema is not None:
            payload["format"] = schema
        data = json.dumps(payload).encode()
        req = request.Request(
            f"{self.host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_s) as response:
                return json.loads(response.read().decode())
        except error.URLError as exc:
            raise LLMError(f"ollama request failed for {self.model}: {exc}") from exc


class OpenAICompatClient:
    """OpenAI ``/v1/chat/completions`` for llama-server, Lemonade, or vLLM.

    Stdlib only (Decision 0021). One schema retry, then ``LLMError``.
    HTTP errors, URL errors, and socket timeouts are ``LLMError`` and are
    not retried.
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 120,
    ) -> None:
        self.model = model or os.environ.get("ATG_MODEL", DEFAULT_MODEL)
        self.base_url = (
            base_url or os.environ.get("ATG_BASE_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        key = api_key if api_key is not None else os.environ.get("ATG_API_KEY")
        self.api_key = key or None
        self.timeout_s = timeout_s

    def complete(self, messages: list[dict], **kwargs: Any) -> str:
        return self._content(messages, response_format=None)

    def complete_structured(self, messages: list[dict], schema: type[BaseModel]) -> BaseModel:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
            },
        }
        content = self._content(messages, response_format=response_format)
        try:
            return _parse_model(content, schema)
        except (ValidationError, json.JSONDecodeError):
            follow_up = list(messages)
            follow_up.append(
                {
                    "role": "user",
                    "content": (
                        "The previous content was not valid JSON for the schema. "
                        "Return only JSON."
                    ),
                }
            )
            retry = self._content(follow_up, response_format=None)
            try:
                return _parse_model(retry, schema)
            except (ValidationError, json.JSONDecodeError) as exc:
                raise LLMError(f"{self.model} returned invalid structured output") from exc

    def _content(self, messages: list[dict], *, response_format: dict | None) -> str:
        body = self._post(messages, response_format=response_format)
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"openai-compat response for {self.model} had no message content"
            ) from exc
        if content is None:
            return ""
        return str(content)

    def _post(self, messages: list[dict], *, response_format: dict | None) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "stream": False,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        data = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_s) as response:
                raw = response.read().decode()
        except error.HTTPError as exc:
            raise LLMError(f"openai-compat request failed for {self.model}: {exc}") from exc
        except error.URLError as exc:
            raise LLMError(f"openai-compat request failed for {self.model}: {exc}") from exc
        except TimeoutError as exc:
            raise LLMError(f"openai-compat request timed out for {self.model}: {exc}") from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"openai-compat response for {self.model} was not JSON") from exc
        if not isinstance(parsed, dict):
            raise LLMError(f"openai-compat response for {self.model} was not a JSON object")
        return parsed


class LiteLLMClient:
    """Optional extra ``[llm]``. Import is lazy so core tests stay light."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("ATG_MODEL", f"ollama/{DEFAULT_MODEL}")

    def complete(self, messages: list[dict], **kwargs: Any) -> str:
        litellm = _litellm()
        response = litellm.completion(model=self.model, messages=messages, temperature=0)
        return str(response.choices[0].message.content)

    def complete_structured(self, messages: list[dict], schema: type[BaseModel]) -> BaseModel:
        litellm = _litellm()
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=0,
            response_format=schema,
        )
        content = response.choices[0].message.content
        return _parse_model(str(content), schema)


def _litellm():
    try:
        import litellm
    except ImportError as exc:
        raise LLMError("LiteLLM is not installed. Use OllamaClient or pip install 'atg-framework[llm]'.") from exc
    return litellm


def _parse_model(content: str, schema: type[BaseModel]) -> BaseModel:
    try:
        return schema.model_validate_json(content)
    except ValidationError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return schema.model_validate_json(content[start : end + 1])
        raise
