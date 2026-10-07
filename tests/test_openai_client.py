"""OpenAI-compatible client against a local stdlib HTTP server."""

import importlib.util
import json
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from atg import LLMError, OpenAICompatClient
from atg.planner import Decomposition

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("toy_parallel", _ROOT / "examples" / "toy_parallel.py")
assert _SPEC is not None and _SPEC.loader is not None
toy_parallel = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(toy_parallel)

_RETRY_TEXT = "The previous content was not valid JSON for the schema. Return only JSON."


class _Server(ThreadingHTTPServer):
    allow_reuse_address = True


class _RetryHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw.decode())
        self.server.requests.append({"path": self.path, "body": body})
        content = "not-json" if len(self.server.requests) == 1 else self.server.good_json
        encoded = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": content}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


class _HangHandler(BaseHTTPRequestHandler):
    """Accept the POST and write nothing, so the client hits timeout_s."""

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length:
            self.rfile.read(length)
        self.server.hits += 1
        self.server.accepted.set()
        self.server.hold.wait()

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def _serve(handler: type[BaseHTTPRequestHandler], **attrs: object):
    server = _Server(("127.0.0.1", 0), handler)
    for key, value in attrs.items():
        setattr(server, key, value)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _wait_until_listening(server)
        yield server
    finally:
        hold = getattr(server, "hold", None)
        if hold is not None:
            hold.set()
        server.shutdown()
        server.server_close()
        thread.join(5)


def _wait_until_listening(server: _Server) -> None:
    host, port = server.server_address
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((str(host), int(port)), timeout=0.2):
                return
        except OSError:
            time.sleep(0.01)
    raise AssertionError(f"server not listening on {host}:{port}")


def _base_url(server: _Server) -> str:
    host, port = server.server_address
    return f"http://{host}:{port}"


def test_malformed_reply_is_retried_once_and_is_not_the_graph():
    good = toy_parallel.scripted().model_dump_json()
    with _serve(_RetryHandler, requests=[], good_json=good) as server:
        client = OpenAICompatClient(
            "llama3.1:8b",
            base_url=_base_url(server),
            api_key="",
            timeout_s=5,
        )
        result = toy_parallel.run_task(toy_parallel.root(), toy_parallel.registry(), client)
        requests = list(server.requests)

    assert len(requests) == 2
    assert [item["path"] for item in requests] == [
        "/v1/chat/completions",
        "/v1/chat/completions",
    ]
    first, second = (item["body"] for item in requests)
    assert first["model"] == "llama3.1:8b"
    assert first["temperature"] == 0
    assert first["stream"] is False
    assert first["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "Decomposition",
            "schema": Decomposition.model_json_schema(),
        },
    }
    assert "response_format" not in second
    assert second["messages"][:-1] == first["messages"]
    assert second["messages"][-1] == {"role": "user", "content": _RETRY_TEXT}
    assert set(result.graph.node_ids()) == {"s", "p", "t"}
    assert set(result.graph.edges()) == {("s", "t"), ("p", "t")}
    assert "not-json" not in result.graph.node_ids()
    assert result.graph.get("s").outputs == {"value": 5}
    assert result.graph.get("p").outputs == {"value": 20}
    assert result.graph.get("t").outputs == {"value": 25}
    assert result.thought.ok


def test_silent_server_raises_llm_error_before_ten_seconds():
    with _serve(
        _HangHandler,
        hits=0,
        accepted=threading.Event(),
        hold=threading.Event(),
    ) as server:
        client = OpenAICompatClient(
            "llama3.1:8b",
            base_url=_base_url(server),
            api_key="",
            timeout_s=1,
        )
        assert client.timeout_s < 2
        caught: list[BaseException] = []

        def invoke() -> None:
            try:
                client.complete_structured(
                    [{"role": "user", "content": "compile"}],
                    Decomposition,
                )
            except BaseException as exc:
                caught.append(exc)

        started = time.monotonic()
        worker = threading.Thread(target=invoke, daemon=True)
        worker.start()
        worker.join(10)
        elapsed = time.monotonic() - started
        alive = worker.is_alive()
        hits = server.hits

    assert not alive
    assert elapsed < 10
    assert hits == 1
    assert len(caught) == 1
    assert isinstance(caught[0], LLMError)
