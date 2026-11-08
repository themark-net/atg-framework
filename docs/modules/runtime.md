# Module: atg runtime

Operator walkthrough, by skill level: [`../USING.md`](../USING.md). Ordered next work: [`../NEXT.md`](../NEXT.md).

**Architecture layer:** Planner, executor, thought experiment, repair (`docs/ARCHITECTURE.md` §5.3)  
**Code:** `src/atg/planner.py`, `executor.py`, `thought.py`, `repair.py`, `run.py`, `llm.py`, `persist.py`, `integrations/`  
**Related ADR / Decisions:** 0003, 0007, 0009, 0010, 0011, 0012, 0013, 0014, 0015, 0016, 0017, 0020, 0021, 0025, 0026

Paper stages in this layer are Zhang et al. (2026), `zhang2026atg`: §4.1 compilation, §4.2 dependency-aware execution and the thought experiment, §4.3 minimal repair. Independent reimplementation. Policy: `docs/ATTRIBUTION.md`.

## Operator

### What it does

`run_task` compiles an abstract node into atomic tool calls, checks the graph, and repairs a thought-experiment error that names a live node before any tool runs. It then runs independent tools together, and on a tool exception replaces the failed region. Successful nodes outside that region are frozen and their functions are not called again. A node left `running` from an earlier process is marked `failed` at the start of `execute` and its tool is not called.

### How to run

```bash
uv sync --extra dev
uv run pytest
uv run python examples/toy_parallel.py
ATG_MODEL=llama3.1:8b uv run python examples/toy_parallel.py --live
ATG_JUDGE=1 uv run python examples/toy_parallel.py
```

The default pytest run does not call Ollama. `ATG_RUN_INTEGRATION=1 uv run pytest -m integration` does.

### Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| `CompileError` depth cap | The model kept emitting non-atomic nodes | Lower the task or raise `max_depth` for one run. The default cap is 6 (Decision 0007). |
| `CompileError` / `RepairError` interface | The decomposition dropped a parent `$ref` or a sink output, and the compile fix-up budget is spent | The planner already sent the validator text back, up to `max_compile_attempts` (default 3). `metrics.compile_retries` counts those extra calls. `metrics.repairs` does not. The graph from before the failed replacement is unchanged. |
| `LLMError` | Ollama is down, the tag returned non-JSON, or either client saw an HTTP error, URL error, or socket timeout | The message names up to three schema fields when the JSON does not match. The Ollama HTTP message includes a truncated response body (Decision 0026). Check `ollama list` for the default client. For `--client openai`, check `ATG_BASE_URL`. The live script tries `qwen2.5:14b`, then `gemma4:latest`. |
| Tool node `failed` after two repairs | The callable raised twice, or a pre-execution repair used the same budget | `RunResult.metrics.repairs` counts both. The cap is `max_repairs` (default 2). |
| Thought check fails and nothing runs | The error names no live node, often an unscoped judge reason | That is Decision 0020. A named node is repaired before `execute`. |
| `frozen nodes cannot be reset` | `reset_for_repair` on a frozen node | That refusal is Decision 0014. Repair must replace a different region. |
| Live script exit 1 | No tag produced a parallel graph whose sink value matches the toy | Read stderr. Decision 0017 records the 2026-10-05 run. Re-run `--model qwen2.5:14b --only` when `ollama ps` is empty. |

## Configuration / variables

| Name | Where | Purpose |
|------|-------|---------|
| `ATG_MODEL` | environment, read by `OllamaClient`, `OpenAICompatClient`, and `LiteLLMClient` | Model tag. Default `qwen2.5:14b` in `src/atg/llm.py` (Decision 0023). |
| `ATG_OLLAMA_HOST` | environment | Default `http://127.0.0.1:11434`. Do not point this at llama-server, Lemonade, or vLLM (Decision 0021). |
| `ATG_BASE_URL` | environment, read by `OpenAICompatClient` | Server root. Default `http://127.0.0.1:8000`. The client posts `{base}/v1/chat/completions`. |
| `ATG_API_KEY` | environment, read by `OpenAICompatClient` | Optional. When set, send `Authorization: Bearer <key>`. When unset, send no auth header. |
| `ATG_JUDGE` | environment, `1` enables | One judge call after structural checks pass (Decision 0013). |
| `max_depth` | `compile_task` / `run_task` argument | Refine cap. Default 6. |
| `max_repairs` | `run_task` argument | Default 2. Counts `repair_graph` calls only. |
| `max_compile_attempts` | `compile_task` / `run_task` / `repair_graph` argument | Default 3, including the first plan (Decision 0025). Extra calls are `metrics.compile_retries`. |
| `ThreadRunner.max_workers` | constructor | `None` uses the stdlib pool default (Decision 0010). |
| History JSON | path passed to `save_history` | Not written unless the caller asks (Decision 0015). |

## Agent

### Entry points

`import atg` re-exports the names below. Adapters stay on `atg.integrations`.

- `compile_task`, `Decomposition`, `CompileError`
- `execute`, `resolve_inputs`
- `structural_thought`, `thought_experiment`
- `repair_graph`, `lowest_common_ancestor`, `repair_region`
- `run_task`, `RunResult`
- `MockLLM`, `OllamaClient`, `OpenAICompatClient`, `LiteLLMClient`
- `save_history`, `load_history`
- `as_langgraph_node`, `as_dspy_forward`
- `TaskGraph.replace_node`, `TaskGraph.reset_for_repair`

### Data shapes

- `Decomposition`: `{nodes: [{id, name, tool_name, inputs, declared_outputs, refine}], edges: [{src, dst}]}`.
- `JudgeVerdict`: `{ok, reason}`.
- `Metrics`: `waves`, `tool_calls`, `max_parallel`, `failures`, `repairs`, `compile_retries`, `nodes_frozen_reused`, `judge_disagreements`. `compile_retries` is the planner fix-up (Decision 0025), not an execution repair.
- Tool return: a dict is stored as outputs. A scalar is stored under the single `declared_outputs` name, or under `result`.

### Callers / callees

- `run_task` calls compile, thought, repair, and execute. Thought repairs that name a node run before execute (Decision 0020).
- `compile_task` and `repair_graph` call `propose_subgraph`, which calls `complete_structured` with `planning_model` and then `assert_interface_preserved`. A validator failure is sent back until `max_compile_attempts`.
- The few-shot example takes its tool name from the registry. A root compile shows two `example_` nodes, one child `$ref`, and the edge that makes that child an ancestor. A repair does not. When the parent already has a `$ref`, the example copies that ref and does not add `example_src`. The prompt forbids emitting the `example_` prefix. A plan that copies it is a compile error and is sent back. That is not a rewrite of the `$ref` (Decision 0024).
- `OllamaClient` turns that schema into `ollama_format_schema` (no `$defs`, no property named `$ref`) and sets `think` false (Decision 0026). `OpenAICompatClient` sends the Pydantic schema unchanged.
- `execute` calls `mark_ready`, `transition`, and the runner. It does not call the LLM.
- Adapters call `run_task` only. They do not import LangGraph or DSPy.

### Invariants

- A parallel wave counts as one `waves` step (Decision 0011).
- Status changes during a wave are applied after the pool returns, on the calling thread.
- `ATG_JUDGE` unset means no judge call.
- Frozen nodes are outside the repair region and their callables are not invoked again (measured in `tests/test_runtime.py`).
- `reset_for_repair` cannot clear a frozen node.
- Core modules do not import LiteLLM, LangGraph, or DSPy.
- A node that is still `running` at the start of `execute` becomes `failed` and its callable is not invoked (Decision 0020).
- `save_history` replaces the checkpoint. A failed write leaves the previous file.
- A repair example does not introduce a producer id. A root example may, and only with the `example_` prefix. A copied `example_` id fails compilation and is retried. Short `$ref` strings are still not rewritten (Decision 0024).

### Extension points

- A new model port implements `complete` and `complete_structured`.
- A new runner implements `map`.
- Benchmark adapters wait on Decision 0018.

### Do not

- Do not import LangGraph, DSPy, or NetworkX from core modules.
- Do not default `ATG_MODEL` to a cloud tag or a coder-only tag.
- Do not add ALFWorld, WebShop, or ScienceWorld here.
- The software license is MIT (Decision 0019). Do not replace it without a superseding decision.
- Do not widen `transition` to allow `failed → pending`. Use `reset_for_repair`.
