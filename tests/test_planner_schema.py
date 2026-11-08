"""Planner schema, prompt, and compile fix-up. No network except local loopback."""

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import ValidationError

from atg.executor import execute
from atg.llm import LLMError, MockLLM, OllamaClient, OpenAICompatClient, ollama_format_schema
from atg.metrics import Metrics
from atg.planner import (
    ChildNode,
    CompileError,
    Decomposition,
    PlanningNode,
    RefBinding,
    decomposition_gbnf,
    planning_model,
    compile_task,
)
from atg.run import run_task
from atg.tools import ToolRegistry
from atg.types import ID_HEAD, ID_TAIL, REF_PATTERN, NodeStatus, TaskNode, parse_ref


def _registry() -> ToolRegistry:
    registry = ToolRegistry()

    def add(a: int, b: int) -> dict:
        return {"value": a + b}

    registry.register(
        add,
        name="add",
        description="Add integers a and b. Returns value.",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    )
    return registry


def _good() -> Decomposition:
    return Decomposition(
        nodes=[
            ChildNode(
                id="total",
                name="total",
                tool_name="add",
                inputs={"a": 2, "b": 3},
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )


def _missing_sink() -> Decomposition:
    return Decomposition(
        nodes=[
            ChildNode(
                id="total",
                name="total",
                tool_name="add",
                inputs={"a": 2, "b": 3},
                declared_outputs=[],
                refine=False,
            )
        ]
    )


def _patterns(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        pattern = value.get("pattern")
        if isinstance(pattern, str):
            found.append(pattern)
        for item in value.values():
            found.extend(_patterns(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_patterns(item))
    return found


class _Recording(MockLLM):
    def __init__(self, scripted: list) -> None:
        super().__init__(scripted)
        self.seen: list[list[dict]] = []

    def complete_structured(self, messages: list[dict], schema: type) -> object:
        self.seen.append(messages)
        return super().complete_structured(messages, schema)


def test_planning_schema_matches_the_graph_ref_pattern_and_rejects_a_short_ref():
    schema = planning_model(("add", "mul"), require_declared_output=True).model_json_schema()
    assert REF_PATTERN in _patterns(schema)
    assert set(PlanningNode.model_fields) == set(ChildNode.model_fields)
    with pytest.raises(ValueError, match="outputs"):
        parse_ref({"$ref": "add_step.value"})
    with pytest.raises(ValidationError):
        RefBinding.model_validate({"$ref": "add_step.value"})
    parsed = parse_ref({"$ref": "add_step.outputs.value"})
    assert parsed is not None and parsed.node_id == "add_step" and parsed.field == "value"
    binding = RefBinding.model_validate({"$ref": "add_step.outputs.value"})
    assert binding.ref == "add_step.outputs.value"


def test_planning_schema_rejects_a_tool_that_is_not_in_the_registry():
    model = planning_model(("add",), require_declared_output=True)
    body = {
        "nodes": [
            {
                "id": "total",
                "name": "total",
                "tool_name": "missing",
                "inputs": {"a": 1, "b": 2},
                "declared_outputs": ["value"],
                "refine": False,
            }
        ],
        "edges": [],
    }
    with pytest.raises(ValidationError):
        model.model_validate(body)
    body["nodes"][0]["tool_name"] = "add"
    model.model_validate(body)
    with pytest.raises(ValidationError):
        model.model_validate(
            {
                "nodes": [
                    {
                        "id": "total",
                        "name": "total",
                        "tool_name": "add",
                        "inputs": {},
                        "declared_outputs": [],
                        "refine": False,
                    }
                ],
                "edges": [],
            }
        )


def _ref_producers(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        raw = value.get("$ref")
        if isinstance(raw, str) and set(value) == {"$ref"}:
            found.append(raw.split(".outputs.", 1)[0])
        else:
            for item in value.values():
                found.extend(_ref_producers(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_ref_producers(item))
    return found


def test_prompt_uses_a_catalog_few_shot_and_credits_the_paper():
    registry = _registry()
    root = TaskNode(id="job", name="Add 2 and 3.", declared_outputs=["value"])
    mock = _Recording([_good()])
    compile_task(root, registry, mock, metrics=Metrics())
    system = mock.seen[0][0]["content"]
    user = json.loads(mock.seen[0][1]["content"])
    example = user["example"]
    node_ids = {node["id"] for node in example["nodes"]}
    assert "Zhang et al." in system
    assert "2607.01942" in system
    assert ".outputs." in system
    assert "Never emit an id that starts with example_" in system
    assert "two operations to the same value in parallel" in system
    assert example["nodes"][0]["tool_name"] == "add"
    assert example["nodes"][0]["inputs"] == {"a": 1, "b": 2}
    assert example["edges"] == []
    assert _ref_producers(example) == []
    assert "$ref" not in mock.seen[0][1]["content"]
    assert node_ids == {"example_dst"}
    assert "example_src" not in mock.seen[0][1]["content"]
    assert "step" not in mock.seen[0][1]["content"]
    assert user["sink_outputs"] == ["value"]
    assert "validator_error" not in user


def test_example_copies_a_parent_ref_instead_of_an_example_id():
    """A repair parent already names the external producer. The example must too."""

    registry = _registry()
    root = TaskNode(
        id="region",
        name="Replace the failed product.",
        inputs={"left": {"$ref": "a_left.outputs.value"}},
        declared_outputs=["value"],
    )
    repaired = Decomposition(
        nodes=[
            ChildNode(
                id="total",
                name="total",
                tool_name="add",
                inputs={"a": {"$ref": "a_left.outputs.value"}, "b": 1},
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )
    mock = _Recording([repaired])
    graph, _history = compile_task(root, registry, mock, metrics=Metrics())
    assert graph.get("total").inputs["a"] == {"$ref": "a_left.outputs.value"}
    example = json.loads(mock.seen[0][1]["content"])["example"]
    node_ids = {node["id"] for node in example["nodes"]}
    assert _ref_producers(example) == ["a_left"]
    assert "a_left" not in node_ids
    assert all(not producer.startswith("example_") for producer in _ref_producers(example))
    assert "step" not in mock.seen[0][1]["content"]
    assert "example_src" not in mock.seen[0][1]["content"]


def test_compile_fixup_sends_the_validator_error_and_then_runs():
    registry = _registry()
    root = TaskNode(id="job", name="Add 2 and 3.", declared_outputs=["value"])
    mock = _Recording([_missing_sink(), _good()])
    metrics = Metrics()
    graph, _history = compile_task(root, registry, mock, metrics=metrics)
    execute(graph, registry, metrics=metrics)
    assert graph.get("total").outputs == {"value": 5}
    assert metrics.compile_retries == 1
    assert metrics.repairs == 0
    assert metrics.tool_calls == 1
    first = json.loads(mock.seen[0][1]["content"])
    second = json.loads(mock.seen[1][1]["content"])
    assert "validator_error" not in first
    assert "sinks missing declared outputs ['value']" in second["validator_error"]


def test_compile_fixup_stops_at_the_budget_and_does_not_run_tools():
    registry = _registry()
    called: list[tuple[int, int]] = []

    def add(a: int, b: int) -> dict:
        called.append((a, b))
        return {"value": a + b}

    registry.get("add").fn = add
    root = TaskNode(id="job", name="Add 2 and 3.", declared_outputs=["value"])
    mock = MockLLM([_missing_sink(), _missing_sink()])
    metrics = Metrics()
    with pytest.raises(CompileError, match="sinks missing declared outputs"):
        compile_task(root, registry, mock, metrics=metrics, max_compile_attempts=2)
    assert mock.calls == 2
    assert metrics.compile_retries == 1
    assert metrics.repairs == 0
    assert called == []


def test_repair_fixup_is_not_counted_as_a_second_repair():
    calls = {"keep": 0, "work": 0}
    registry = ToolRegistry()

    def keep() -> dict:
        calls["keep"] += 1
        return {"value": 1}

    def work() -> dict:
        calls["work"] += 1
        if calls["work"] == 1:
            raise RuntimeError("boom")
        return {"value": 7}

    registry.register(keep, name="keep", description="keep")
    registry.register(work, name="work", description="work")
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    first = Decomposition(
        nodes=[
            ChildNode(id="keep", name="keep", tool_name="keep", declared_outputs=["value"], refine=False),
            ChildNode(id="work", name="work", tool_name="work", declared_outputs=["value"], refine=False),
        ]
    )
    bad = Decomposition(
        nodes=[
            ChildNode(
                id="work2",
                name="work2",
                tool_name="work",
                declared_outputs=["other"],
                refine=False,
            )
        ]
    )
    good = Decomposition(
        nodes=[
            ChildNode(
                id="work2",
                name="work2",
                tool_name="work",
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )
    result = run_task(root, registry, MockLLM([first, bad, good]))
    assert result.metrics.repairs == 1
    assert result.metrics.compile_retries == 1
    assert calls == {"keep": 1, "work": 2}
    assert result.graph.get("keep").status == NodeStatus.frozen
    assert result.graph.get("work2").outputs == {"value": 7}


def test_gbnf_uses_the_graph_identifier_classes():
    text = decomposition_gbnf(["mul", "add"])
    assert f"ident ::= [{ID_HEAD}] [{ID_TAIL}]*" in text
    assert 'ident ".outputs." ident' in text
    assert '"\\"add\\""' in text
    assert '"\\"mul\\""' in text
    assert text.index('"\\"add\\""') < text.index('"\\"mul\\""')


class _Server(ThreadingHTTPServer):
    allow_reuse_address = True


class _Capture(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw.decode())
        self.server.requests.append({"path": self.path, "body": body})
        if self.path.startswith("/v1/"):
            payload = {"choices": [{"message": {"role": "assistant", "content": self.server.good}}]}
        else:
            payload = {"message": {"role": "assistant", "content": self.server.good}}
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def _serve(good: str):
    server = _Server(("127.0.0.1", 0), _Capture)
    server.requests = []
    server.good = good
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((str(host), int(port)), timeout=0.2):
                break
        except OSError:
            time.sleep(0.01)
    else:
        server.shutdown()
        raise AssertionError("server did not listen")
    return server, thread


def _schema_keys(node: object, key: str) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        if key in node:
            found.append(key)
        for value in node.values():
            found.extend(_schema_keys(value, key))
    elif isinstance(node, list):
        for value in node:
            found.extend(_schema_keys(value, key))
    return found


def _patterns(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        pattern = node.get("pattern")
        if isinstance(pattern, str):
            found.append(pattern)
        for value in node.values():
            found.extend(_patterns(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_patterns(value))
    return found


def test_ollama_format_drops_a_ref_property():
    raw = planning_model(("add", "mul"), require_declared_output=True).model_json_schema()
    assert "$defs" in raw
    wire = ollama_format_schema(raw)
    assert _schema_keys(wire, "$ref") == []
    assert _schema_keys(wire, "$defs") == []
    assert REF_PATTERN in _patterns(wire)


def test_ollama_format_is_the_planning_schema():
    good = _good().model_dump_json()
    schema = planning_model(("add",), require_declared_output=True)
    server, thread = _serve(good)
    try:
        host, port = server.server_address
        client = OllamaClient("qwen2.5:14b", host=f"http://{host}:{port}", timeout_s=5)
        client.complete_structured(
            [{"role": "user", "content": "compile"}],
            schema,
        )
        body = server.requests[0]["body"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
    assert server.requests[0]["path"] == "/api/chat"
    assert body["format"] == ollama_format_schema(schema.model_json_schema())
    assert _schema_keys(body["format"], "$ref") == []
    assert body["think"] is False
    assert body["stream"] is False
    assert "grammar" not in body


def test_ollama_http_error_includes_the_response_body():
    class _Deny(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                self.rfile.read(length)
            msg = b'{"error":"type must be string, but is object"}'
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Deny)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        client = OllamaClient("qwen2.5:14b", host=f"http://{host}:{port}", timeout_s=5)
        with pytest.raises(LLMError, match="type must be string, but is object"):
            client.complete_structured(
                [{"role": "user", "content": "compile"}],
                planning_model(("add",), require_declared_output=True),
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_openai_grammar_replaces_response_format():
    good = _good().model_dump_json()
    grammar = decomposition_gbnf(["add"])
    server, thread = _serve(good)
    try:
        host, port = server.server_address
        client = OpenAICompatClient(
            "qwen2.5:14b",
            base_url=f"http://{host}:{port}",
            api_key="",
            timeout_s=5,
            grammar=grammar,
        )
        client.complete_structured(
            [{"role": "user", "content": "compile"}],
            Decomposition,
        )
        body = server.requests[0]["body"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
    assert body["grammar"] == grammar
    assert "response_format" not in body


def test_a_transport_error_is_not_retried_as_a_bad_plan():
    registry = _registry()
    root = TaskNode(id="job", name="Add 2 and 3.", declared_outputs=["value"])

    class _Down(MockLLM):
        def complete_structured(self, messages: list[dict], schema: type) -> object:
            self.calls += 1
            raise LLMError("ollama request failed for qwen2.5:14b: down")

    mock = _Down([])
    metrics = Metrics()
    with pytest.raises(LLMError, match="ollama request failed"):
        compile_task(root, registry, mock, metrics=metrics, max_compile_attempts=3)
    assert mock.calls == 1
    assert metrics.compile_retries == 0
