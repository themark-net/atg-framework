# Using atg-framework

**Architecture layer:** the compile / run / repair loop in [`ARCHITECTURE.md`](ARCHITECTURE.md) §5, implemented in `src/atg/`.  
**Decisions:** 0002–0004, 0007, 0011–0020.  
**Paper:** Yue Zhang, Sihan Chen, Ziwen Huang, Hanyun Cui, Kangye Ji, and Zhi Wang, *Atomic Task Graph* (2026), arXiv:2607.01942. BibTeX key `zhang2026atg`. This repository is an independent reimplementation. It is not an official author release. Policy: [`ATTRIBUTION.md`](ATTRIBUTION.md).

Module detail for the same code lives in [`modules/foundations.md`](modules/foundations.md) and [`modules/runtime.md`](modules/runtime.md). This page is the operator path, split by how much you want to build.

| You want to… | Read |
|--------------|------|
| Run the tested example and see a number | [Level 1](#level-1--run-the-offline-example) |
| Register your own Python functions and call `run_task` | [Level 2](#level-2--register-tools-and-call-run_task) |
| Run it on a local model, on hardware like nimo | [Level 3](#level-3--a-local-model-on-nimo-class-hardware) |
| Save the graph, or call it from LangGraph or DSPy | [Level 4](#level-4--checkpoints-and-other-frameworks) |
| Decide whether pfy-mentat should depend on it | [`ops/pfy-mentat-handoff.md`](ops/pfy-mentat-handoff.md) |

## Is this useful?

Yes, as a small Python control library. It does not import Grok, and the offline path does not call a model.

What is implemented and tested (version 0.2.0, 35 unit tests, 1 integration test left off unless `ATG_RUN_INTEGRATION=1`):

- Compile one task into an explicit DAG whose edges are data dependencies.
- Run independent registered tools in the same wave. A wave counts as one step (Decision 0011).
- Freeze a successful node and skip its function on a later repair (Decision 0014).
- Replace a failed region and keep the parent’s external interface.
- Store full graph snapshots in memory, and write them to a JSON file when the caller asks (Decision 0015).

The offline example is the proof you can run in a minute:

```text
mock total={'value': 25} waves=2 parallel=2
```

That line means two tools ran together (`2 + 3` and `4 * 5`), then a third tool added their outputs (`5 + 20`). The repair test in `tests/test_runtime.py` (`test_repair_freezes_successful_sibling_and_reruns_failure`) is the other proof: the successful sibling is called once and left `frozen`, the failing tool is replaced, and `metrics.repairs` is 1.

What this repository has not shown:

- On 2026-10-06, `qwen2.5:14b` produced the toy graph: two waves, parallel width 2, sink value 25 (Decision 0023). The 2026-10-05 failures are still on Decision 0017.
- The paper’s ALFWorld, WebShop, and ScienceWorld numbers are the paper’s results. This repository has not re-run those benchmarks (Decision 0018).
- The package is pre-alpha. The classifier in `pyproject.toml` says so.

The part worth using today is the control loop. Zhang et al. argue that an explicit graph, parallel tool execution, and localized repair let a 7B–8B model keep finished work. This library is that control loop, with a scripted model in tests and an optional Ollama client for a machine you already have. It is not a general agent, and it is not a claim that a 7B model on this hardware beat GPT-4.

## What you need

| Requirement | Offline path | Live model path |
|-------------|----------------|-----------------|
| Python | 3.11 or newer. This machine runs CPython 3.12.12. | Same |
| Install | `uv sync --extra dev`, or `pip install -e .` | Same |
| Packages that always install | `pydantic` | Same |
| Grok | Not used | Not used |
| GPU | Not used | Whatever Ollama uses for the tag you name |
| Ollama | Not used | Daemon at `ATG_OLLAMA_HOST` (default `http://127.0.0.1:11434`) |
| LiteLLM | Not used | Only if you construct `LiteLLMClient` (`pip install -e '.[llm]'`) |

`OllamaClient` talks to the daemon with the Python standard library. Core modules do not import LangGraph or DSPy (Decision 0002, Decision 0016).

## Level 1 — Run the offline example

From a clone of this repository:

```bash
uv sync --extra dev
uv run pytest -q -m "not integration"
uv run python examples/toy_parallel.py
```

Checked on 2026-10-05: pytest printed `35 passed, 1 deselected`, and the example printed `mock total={'value': 25} waves=2 parallel=2`.

The example registers two functions, `add` and `mul`. A scripted `MockLLM` returns one decomposition:

- `s` calls `add(2, 3)` and declares `value`
- `p` calls `mul(4, 5)` and declares `value`
- `t` calls `add` with `{"$ref": "s.outputs.value"}` and `{"$ref": "p.outputs.value"}`
- Edges are `s → t` and `p → t`

`s` and `p` have no dependency on each other, so they share a wave. `t` waits. The parent node `job` declares `value`, and the sink `t` declares `value`, so the external interface is preserved.

If pytest fails, the install is wrong or the tree is not this version. If the example prints a different total, stop and read `examples/toy_parallel.py` before trusting a write-up of the result.

## Level 2 — Register tools and call `run_task`

A tool is a Python function plus a JSON schema of the same name (Decision 0007). Inputs are literals or exactly `{"$ref": "node_id.outputs.field"}`. A node id matches `^[A-Za-z_][A-Za-z0-9_-]*$`.

This program is the smallest complete call. It was run on 2026-10-05 and printed `value={'value': 5} status=done waves=1 parallel=1 repairs=0`.

```python
from atg.llm import MockLLM
from atg.planner import ChildNode, Decomposition
from atg.run import run_task
from atg.tools import ToolRegistry
from atg.types import TaskNode

registry = ToolRegistry()

def add(a: int, b: int) -> dict:
    return {"value": a + b}

registry.register(
    add,
    name="add",
    description="Add integers a and b. Returns value.",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"},
        },
        "required": ["a", "b"],
    },
)

root = TaskNode(id="job", name="Add 2 and 3.", declared_outputs=["value"])
plan = Decomposition(
    nodes=[
        ChildNode(
            id="s",
            name="sum",
            tool_name="add",
            inputs={"a": 2, "b": 3},
            declared_outputs=["value"],
            refine=False,
        )
    ]
)
result = run_task(root, registry, MockLLM([plan]))
node = result.graph.get("s")
print(
    f"value={node.outputs} status={node.status.value} "
    f"waves={result.metrics.waves} parallel={result.metrics.max_parallel} "
    f"repairs={result.metrics.repairs}"
)
```

`MockLLM` pops one scripted `Decomposition` per planner call. Use it when you already know the graph, in tests, and in demos. The parallel graph is `examples/toy_parallel.py`. Copy that file when you want two branches.

To let a model write the graph, pass `OllamaClient` instead of `MockLLM`. The model must return JSON matching `Decomposition`. The system prompt in `src/atg/planner.py` tells it to use registered tool names, set `refine` false on a tool node, copy sink outputs from the parent, and keep the parent id off the edges.

`run_task(root, registry, llm, *, runner=None, max_depth=6, max_repairs=2, judge=None)` returns `RunResult`:

| Field | Meaning |
|-------|---------|
| `graph` | Final `TaskGraph`. `graph.get(node_id).outputs` is the tool dict. |
| `history` | Snapshots, including the graph from before a repair. |
| `metrics` | `waves`, `tool_calls`, `max_parallel`, `failures`, `repairs`, `nodes_frozen_reused`, `judge_disagreements`, `notes`. |
| `thought` | Structural check. `thought.ok` is false when the graph was not executed. |

A function that returns a dict stores that dict. A function that returns a bare value stores it under the single declared output name, or under `result`.

Status on a node moves `pending → ready → running → done → frozen`. A tool exception moves `running → failed` and stores `error`. A failure blocks descendants. Siblings can still run. `failed` does not go back to `pending` through `transition`. Repair builds a replacement region (Decision 0011, Decision 0014).

`max_repairs` defaults to 2 and counts a pre-execution repair and a runtime repair together. `judge=None` reads `ATG_JUDGE`. The judge stays off unless that variable is `1` or you pass `judge=True` (Decision 0013).

## Level 3 — A local model on nimo-class hardware

Measured on the machine named `nimo` on 2026-10-05, while this page was written:

| Item | Value |
|------|--------|
| CPU | AMD Ryzen AI MAX+ 395 with Radeon 8060S, 16 cores, 32 threads |
| GPU | AMD Strix Halo integrated graphics, PCI `1002:1586` (Radeon 8060S class). `nvidia-smi` does not apply. |
| Memory | 107 GiB unified. At the sample, about 39 GiB was available because other jobs held the rest. |
| Ollama | `ollama ps` was empty. No model was loaded. |
| Python | CPython 3.12.12 under `uv` |

This is a consumer APU with a large unified memory pool. It is the class of box that can hold a 7B–14B instruct tag in Ollama without a discrete NVIDIA GPU and without a hosted API. The offline tests do not need that memory. A smaller machine can run Level 1 and Level 2. The live check below is aimed at tags that already fit this class of box.

Intended model band (Decision 0017):

| Role | Tag |
|------|-----|
| Default | `qwen2.5:14b` (`ATG_MODEL`, `DEFAULT_MODEL`, Decision 0023) |
| First fallback | `qwen2.5:14b` |
| Second fallback | `gemma4:latest` |

Leave coder-only tags, tags much above about 15B, and `deepseek-v4-flash:cloud` out of this check. Do not load `qwen3.6:35b` or a 120B tag to try the toy.

Use cases that match this hardware:

1. **Develop the agent control flow with the GPU idle.** Level 1 and Level 2. CI does the same. No model download.
2. **Fan out local Python tools from one small model.** Two or more registered functions that do not depend on each other (parse two files, call two local calculators, then join). The graph is the thing that lets the 8B or 14B tag plan once while the machine runs the tools side by side. The join waits. This is the toy, with your functions in place of `add` and `mul`.
3. **Keep finished tool work when one branch fails.** The tested shape is a sibling that already returned, frozen, while the failed node is compiled again. That matters on a local model because a linear trace would repeat the finished call and spend the memory and time again.
4. **Inspect the run after the model is unloaded.** Level 4 writes the snapshot list to JSON. You can read which node failed without leaving the tag resident.

The live command, only when `ollama ps` prints no model:

```bash
uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only
```

Success is exit 0, `parallel` at least 2, and sink output `{'value': 25}`. The script also requires `thought.ok` and zero `failures`. The client in that script uses a 180 second timeout. `OllamaClient` itself defaults to 120 seconds when you construct it in your own program.

2026-10-05 result, already recorded on Decision 0017: `llama3.1:8b` timed out at 180 seconds, `qwen2.5:14b` emitted an edge that named the parent id (the compiler now drops edges whose endpoints are outside the child set), and `gemma4:latest` left the sink without declared output `value`. None of those runs is a success. A later 14B retry was killed while another bench loaded a 120B tag. That kill is not a model result. Do not start the live command while `ollama ps` shows a runner.

```python
import os
from atg.llm import OllamaClient
from atg.run import run_task

llm = OllamaClient(os.environ.get("ATG_MODEL", "qwen2.5:14b"), timeout_s=180)
# result = run_task(root, registry, llm)
```

Set `ATG_OLLAMA_HOST` when the daemon is not on `http://127.0.0.1:11434`.

Lemonade and vLLM speak `/v1/chat/completions`. Point `ATG_BASE_URL` at that server and pass `--client openai`. Do not point `ATG_OLLAMA_HOST` at those ports. Which of those servers is worth a scored comparison is [OQ-0017](OPEN_QUESTIONS.md). The default remains Ollama `qwen2.5:14b`.

## Level 4 — Checkpoints and other frameworks

JSON history is optional. The runtime keeps snapshots in memory either way.

```python
from atg.persist import load_history, save_history

save_history(result.history, "runs/job.json")
history = load_history("runs/job.json")
```

`save_history` writes `job.json.tmp` and replaces `job.json`. A failed write deletes the temporary file and leaves the previous checkpoint (Decision 0015). SQLite is not the current store.

LangGraph and DSPy adapters are one function each. They do not import those packages. You pass the callable into your own graph or module.

```python
from atg.integrations import as_dspy_forward, as_langgraph_node

langgraph_node = as_langgraph_node(root, registry, llm)
dspy_forward = as_dspy_forward(root, registry, llm)
```

`langgraph_node(state)` returns `atg_outputs`, `atg_metrics`, `atg_ok`, and `state_seen`. `dspy_forward` ignores keyword arguments and returns `metrics`, `ok`, and `ignored_kwargs` (Decision 0016). Neither adapter pauses mid-run for a framework checkpoint.

## Configuration

| Name | Where | Purpose |
|------|--------|---------|
| `ATG_MODEL` | Environment. `OllamaClient` and `LiteLLMClient` read it. | Tag. Default `llama3.1:8b` in `src/atg/llm.py`. |
| `ATG_OLLAMA_HOST` | Environment | Default `http://127.0.0.1:11434`. |
| `ATG_JUDGE` | Environment. `1` turns the judge on. | One judge call after structural checks pass. |
| `ATG_RUN_INTEGRATION` | Environment. `1` enables the pytest mark. | Default pytest does not contact Ollama. |
| `max_depth` | `run_task` / `compile_task` argument | Default 6. |
| `max_repairs` | `run_task` argument | Default 2. |
| History path | Argument to `save_history` | Nothing is written until you call it. |

## Failure modes

| What you see | What to do |
|--------------|------------|
| `CompileError` about depth | The model kept returning a non-atomic node. Simplify the task, or raise `max_depth` for that call. |
| `CompileError` or `RepairError` about the interface | A child dropped a parent `$ref`, or a sink omitted a declared output. The graph from before the failed replacement is unchanged. |
| `LLMError` | The daemon is down, or the tag returned JSON that is not a `Decomposition`. `ollama list` shows whether the tag is installed. |
| Thought check fails and no tool runs | The error text does not start with a live node id. An unscoped judge reason does not select a repair region (Decision 0020). |
| `metrics.repairs` hits 2 and a node is still `failed` | The repair budget is spent. Read `graph.get(node_id).error`. |
| Live script exit 1 | stderr lists the tag and the exception. Decision 0017 holds the 2026-10-05 log. Re-run the Level 3 command only when `ollama ps` is empty. |

More rows: [`modules/runtime.md`](modules/runtime.md).

## Agent

### Entry points

`import atg` exports `compile_task`, `execute`, `run_task`, `repair_graph`, `thought_experiment`, `MockLLM`, `OllamaClient`, `save_history`, `load_history`, `TaskNode`, `ToolRegistry`, and the errors in `src/atg/__init__.py`. Adapters stay on `atg.integrations`.

### Invariants

- Credit Zhang et al. (2026), arXiv:2607.01942, on user-facing text. Do not write that this repository proposes ATG or is official code.
- Core stays free of LangGraph, DSPy, NetworkX, and a hard LiteLLM import.
- Tool inputs are literals or one `$ref` object. There is no `$parent` mini-language.
- `reset_for_repair` is not how `repair_graph` reopens a node, and it refuses frozen nodes.
- A node still `running` when `execute` starts becomes `failed` with error `interrupted before completion` and its tool is not called.
- Paper benchmark ports stay out (Decision 0018).
- OQ-0016 (widen the repair region after a second failure) is open. Do not implement `escalate_after` without a new decision.

### Do not

- Do not claim the offline total of 25 is a paper benchmark score.
- Do not change `DEFAULT_MODEL` unless the Level 3 command exits 0 with `max_parallel >= 2` and sink `value` 25.
- Do not load a model for that check while `ollama ps` shows a runner.
