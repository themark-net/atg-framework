# Handoff: publish atg-framework on X

**Status:** strategy and drafts for a later session. Do not post while implementing features in this repo.  
**Account:** unset. A session posts only after the operator names the account and tells that session to post.  
**Paper:** Yue Zhang, Sihan Chen, Ziwen Huang, Hanyun Cui, Kangye Ji, and Zhi Wang. *Atomic Task Graph: A Unified Framework for Agentic Planning and Execution.* arXiv:2607.01942, 2026. https://arxiv.org/abs/2607.01942  
**Code:** https://github.com/themark-net/atg-framework · MIT · independent reimplementation, not an official author release.  
**How to run it:** [`../USING.md`](../USING.md). Policy: [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

The reason to post is that the control loop is real enough to run. The offline example prints a two-branch result, and the unit tests cover parallel execution and a frozen sibling. Many code posts stop at a repository link. These posts should contain the command, the output, and enough Python that a reader can see the implementation. The long copy-paste form stays in `docs/USING.md` so a truncated post cannot become the only copy.

## Operator

You are announcing work you can reproduce, at three depths:

| Reader | Post job | They can do this afterward |
|--------|----------|----------------------------|
| Newcomer | 1 and 2 | Clone, sync, run the offline example, read `value` 25 |
| Practitioner | 3 and 4 | Register a function, call `run_task`, read waves and repairs |
| Integrator | 5 and 6 | Point `OllamaClient` at a 7B–14B tag on an APU like nimo, or call the one-way adapter |

Post the thread in that order. Each post stands alone if someone sees only that one: it still names the paper authors and says this repository is a separate MIT implementation.

## Claims a post may make

- Zhang et al. (2026) introduce Atomic Task Graph. Name the authors and the arXiv id.
- This repository implements the control loop from that paper: compile a task to a DAG, run independent tools in a wave, freeze successful nodes, repair a failed region.
- The offline example prints `mock total={'value': 25} waves=2 parallel=2` when run as in Level 1 of `docs/USING.md`. Re-run it before posting and use the line you just printed.
- The repair behavior under test is: the successful sibling is called once and ends `frozen`, the failed tool is replaced, `metrics.repairs == 1`. The test is `test_repair_freezes_successful_sibling_and_reruns_failure`.
- The package is MIT, pre-alpha, version 0.2.0, Python 3.11+, and it does not require Grok. `OllamaClient` uses the standard library. LiteLLM is an optional extra.
- On 2026-10-05 the live path had not exited 0. Hardware used for that statement: host `nimo`, AMD Ryzen AI MAX+ 395 with Radeon 8060S, 107 GiB unified memory, Strix Halo integrated graphics. Quote a newer run if you executed one.

The paper evaluates ALFWorld, WebShop, and ScienceWorld with 7B–8B open models and GPT baselines ([`ARCHITECTURE.md`](../ARCHITECTURE.md) §2.4). A post may point readers at the paper for those numbers, and the same post states that this repository has not re-run those benchmarks (Decision 0018). Leave social-media summaries of the paper’s scores out of this repository’s results.

## Claims a post must leave out

- This repository proposes ATG, or is the authors’ official code.
- This code beat GPT-4, or reproduced a paper accuracy number.
- The live toy succeeds, unless the session just saw exit 0 and pastes that output.
- A production agent, a hosted API, or a pfy-mentat integration that has not shipped. The pfy decision procedure is [`pfy-mentat-handoff.md`](pfy-mentat-handoff.md).
- Endorsement by the paper authors. Do not @-mention them as if they released this repo.
- Screenshots of benchmark bars for ALFWorld, WebShop, or ScienceWorld.

pfy `sources/x-posts.md` Entry 001 is the 2026-07-11 paper post (status `2075994424484732984`). Do not reply under that post unless the operator asks. If they do, the reply distinguishes the paper’s results from this repository’s offline example.

## Before anything is posted

Run these in a clean checkout of the commit you will link. Use a permalink (`https://github.com/themark-net/atg-framework/blob/<sha>/...`), not a floating `main` URL, inside the thread.

```bash
git fetch origin
git status -sb
uv sync --extra dev
uv run pytest -q -m "not integration"
uv run python examples/toy_parallel.py
```

Stop if the example does not print `mock total={'value': 25} waves=2 parallel=2`. Update `docs/USING.md` and the drafts below to the real line, then post. If pytest fails, do not post.

Optional live line, only when `ollama ps` is empty:

```bash
uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only
```

If you skip it, post 5 keeps the 2026-10-05 failure statement. If it exits 0, post 5 quotes the new stdout and says Decision 0017 is the place the default tag changes. Do not load a 35B, coder-only, cloud, or 120B tag to make the post look better.

Character budget: write each draft as one post. If the account is limited to 280 characters, split on the blank lines marked `--- split ---` and keep the code block in the earliest part that can hold it. The repository file is the source of the full script. A post that only says “link in bio” is a failed draft.

## Drafts

Replace `<SHA>` with the commit you verified. Replace the output line if the re-run differs.

### Post 1 — newcomer, the result you can run

Atomic Task Graph is Zhang, Chen, Huang, Cui, Ji, and Wang (2026), arXiv:2607.01942.

We implemented the control loop as a MIT Python library. It is not the authors’ code release. No Grok process is required.

```bash
uv sync --extra dev
uv run python examples/toy_parallel.py
```

That prints:

```text
mock total={'value': 25} waves=2 parallel=2
```

Two tools run together (2+3 and 4*5). A third adds their outputs. The scripted model is in the example, so this run does not call Ollama.

https://github.com/themark-net/atg-framework/blob/<SHA>/examples/toy_parallel.py

--- split ---

Paper: https://arxiv.org/abs/2607.01942

### Post 2 — newcomer, what the graph is

The parent task declares one output, `value`. The compiled graph has three nodes:

- `s` calls `add(2, 3)`
- `p` calls `mul(4, 5)`
- `t` calls `add` with `{"$ref": "s.outputs.value"}` and `{"$ref": "p.outputs.value"}`

Edges are `s → t` and `p → t`. `s` and `p` share a wave, so `waves=2` and `parallel=2`. The sink’s `value` is 25, which is the parent’s declared output.

Full write-up, including a one-function program: https://github.com/themark-net/atg-framework/blob/<SHA>/docs/USING.md

### Post 3 — practitioner, the smallest program

A tool is a Python function and a JSON schema. `run_task` compiles, checks, and executes. This one calls `add` only. On 2026-10-05 it printed `value={'value': 5} status=done waves=1 parallel=1 repairs=0`.

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
        "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"],
    },
)
root = TaskNode(id="job", name="Add 2 and 3.", declared_outputs=["value"])
plan = Decomposition(nodes=[ChildNode(
    id="s", name="sum", tool_name="add",
    inputs={"a": 2, "b": 3}, declared_outputs=["value"], refine=False,
)])
result = run_task(root, registry, MockLLM([plan]))
print(result.graph.get("s").outputs, result.metrics.waves)
```

Inputs are literals or `{"$ref": "node_id.outputs.field"}`. The parallel version is the file linked in post 1.

### Post 4 — practitioner, failure and freeze

When one tool raises, descendants of that node wait. A sibling that already succeeded is frozen and its function is not called again.

The unit test `test_repair_freezes_successful_sibling_and_reruns_failure` does this with a scripted model:

- `keep` is called once and ends `frozen`
- `work` raises `RuntimeError: boom` on the first call
- repair compiles a replacement node, `work2`
- `work`’s function runs a second time and `work2` returns `{'value': 7}`
- `metrics.repairs` is 1

That is the localized repair from Zhang et al., implemented and tested here. It is not an ALFWorld score. Decision 0018 leaves those benchmarks deferred.

Source: https://github.com/themark-net/atg-framework/blob/<SHA>/tests/test_runtime.py

### Post 5 — integrator, cheap local hardware

The offline path needs Python 3.11+ and pydantic. No GPU.

The live client is `OllamaClient` against `http://127.0.0.1:11434` (`ATG_OLLAMA_HOST`), or `OpenAICompatClient` for another local `/v1` server. Default tag `qwen2.5:14b` (Decision 0023). Automatic fallback `gemma4:latest`. The band for the default path is about 7B–14B. A 35B tag is a separate measurement and is not the default.

We measured this on a machine called nimo: AMD Ryzen AI MAX+ 395, Radeon 8060S, Strix Halo integrated graphics, 107 GiB unified memory. Similar boxes are the ones that already run those Ollama tags. The unit tests also run on a machine with much less memory, because they use `MockLLM`.

Checked command, when `ollama ps` is empty:

```bash
uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only
```

On 2026-10-05 that live path exited 1 for the 8B tag (180s timeout), the 14B tag (an edge named the parent), and `gemma4:latest` (the sink omitted `value`). On 2026-10-06 the same 14B command exited 0: the model named the sink `add_results`, `value` was 25, and the widest wave was 2. A later `qwen3.6:35b` toy suite succeeded on 1 of 12 tasks (`three_wide`, value 12, width 3) and rejected the other plans before any tool ran. Do not read this thread as a paper-benchmark result.

### Post 6 — integrator, drop-in boundary

```python
from atg.llm import OllamaClient
from atg.integrations import as_langgraph_node, as_dspy_forward

llm = OllamaClient("qwen2.5:14b", timeout_s=180)
# as_langgraph_node(root, registry, llm) returns atg_outputs, atg_metrics, atg_ok
# as_dspy_forward(root, registry, llm) returns metrics and ok
```

Those callables do not import LangGraph or DSPy. Core stays a plain library (Decisions 0002 and 0016). `save_history(result.history, "runs/job.json")` writes a JSON checkpoint by replace.

License: MIT. Citation of the method: Zhang et al., 2026, arXiv:2607.01942. Citation of the software is `CITATION.cff` in the repo, and it still asks you to cite the paper.

## After posting

Append one block under [Posted](#posted) in this file, in a commit on `main`:

- Date, account, and URL of post 1
- Commit SHA the permalinks used
- The exact toy stdout you pasted
- Whether post 5 included a new live run or the 2026-10-05 failure statement

If the operator also wants the thread in the pfy-mentat catalog, that is a separate session. Use [`pfy-mentat-handoff.md`](pfy-mentat-handoff.md) and pfy `/catalog-docs` seed mode. Add a new `sources/x-posts.md` entry. Do not edit Entry 001 into a code release.

## Agent

### Definition of done

- Operator named the account and said to post. Without that, the draft stays in this file.
- Pre-post commands were run on the SHA linked in the thread. Stdout matches the posts.
- Posts 1–6 use only the claims lists above.
- This file’s Posted section contains the URL, or the session stopped before posting and says why.
- No paper figure, no invented metric, no `DEFAULT_MODEL` edit done only so the thread looks finished.

### Do not

- Do not post from a session whose task was a code change, a live remeasure, or the pfy decision.
- Do not schedule posts, buy promotion, or mention authors as endorsers.
- Do not start Ollama while `ollama ps` shows a runner.
- Do not shorten the thread by deleting the command and the output. Those two lines are the post.

## Posted

None yet.
