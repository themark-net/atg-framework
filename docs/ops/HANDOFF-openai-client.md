# Handoff: OpenAI-compatible local client

**Decision:** 0021 (Accepted, 2026-10-06)  
**Status:** implemented in this worktree. Not committed.

Independent reimplementation of Zhang et al. (2026), Atomic Task Graph, arXiv:2607.01942. This repository does not propose ATG and is not official code. See [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

## What changed

- `OpenAICompatClient` in `src/atg/llm.py`. Stdlib only (`urllib`, `json`, `os`, pydantic). Same methods as `OllamaClient`: `complete` and `complete_structured`.
- `model`: argument, else `ATG_MODEL`, else `DEFAULT_MODEL` (`llama3.1:8b`, unchanged).
- `base_url`: argument, else `ATG_BASE_URL`, else `http://127.0.0.1:8000`. Trailing slash stripped. This is the server root. The client posts `{base_url}/v1/chat/completions`.
- `api_key`: argument, else `ATG_API_KEY`. A set key sends `Authorization: Bearer <key>`. An unset key sends no auth header.
- Structured calls send `response_format` json_schema once. If `_parse_model` rejects the content, one follow-up is sent without `response_format`, asking for only JSON. A second invalid reply raises `LLMError`. HTTP errors, URL errors, and socket timeouts raise `LLMError` and are not retried. `urlopen` uses `timeout_s`.
- Exported from `src/atg/__init__.py` `__all__`.
- `examples/toy_parallel.py --client {ollama,openai}` defaults to `ollama`. Offline stays `MockLLM` and the offline print line is unchanged. `--live --client openai` constructs `OpenAICompatClient(model, timeout_s=180)`.

## Tests

```bash
uv run pytest -q tests/test_openai_client.py tests/test_package.py --tb=short
```

1. `test_malformed_reply_is_retried_once_and_is_not_the_graph` — stdlib `http.server` on `127.0.0.1` port 0. The first `/v1/chat/completions` content is `not-json`. The second is the toy `Decomposition` from `examples/toy_parallel.py` (add 2+3, mul 4*5, add the two refs). `run_task(root(), registry(), client)` sink output is `{'value': 25}`. The server saw 2 requests. The malformed reply is not the graph.
2. `test_silent_server_raises_llm_error_before_ten_seconds` — the server accepts and writes no response. `timeout_s` is under 2 seconds. `complete_structured` raises `LLMError` before 10 seconds. The call runs on a thread joined with that bound.

## Not in this change

Do not point `ATG_OLLAMA_HOST` at llama-server, Lemonade, or vLLM. Use `--client openai` and `ATG_BASE_URL`. The default live path stays `OllamaClient`. OQ-0017 (which server runs the live toy) stays open. Do not install a backend or download a model for this client.
