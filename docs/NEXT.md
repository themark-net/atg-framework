# What’s next

Ordered work from 2026-10-05. Phase checkboxes stay in [`TODO.md`](TODO.md). Binding choices stay in [`DECISIONS.md`](DECISIONS.md). How to run the library, by skill level, is [`USING.md`](USING.md).

The MVP in Decision 0004 is in tree: synthetic tools, a mock model, parallel execution, and localized repair. Version 0.2.0. On 2026-10-06, `uv run pytest -q -m "not integration"` → 40 passed, 1 deselected. The software license is MIT (Decision 0019).

The 2026-10-05 count was 35. The later tests cover the OpenAI-compatible client, the offline PoC, and a short `$ref` rejected before any tool runs (Decision 0024).

## 1. Live toy remeasure — done 2026-10-06

`uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only` exited 0: `waves=2 parallel=2` and sink `value` 25 (`add_results`). Decision 0023 sets `DEFAULT_MODEL` to `qwen2.5:14b` and supersedes Decision 0017.

The command that produced that line, kept here so a later session can repeat it when `ollama ps` shows no runner:

```bash
uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only
```

Supersede Decision 0017 and set `DEFAULT_MODEL` to `qwen2.5:14b` only if that process exits 0, `max_parallel >= 2`, and the sink output is `{'value': 25}`. A later comparison against `llama3.1:8b` needs a timeout above 180 seconds. Do not repeat the identical 180 second `llama3.1:8b` call from 2026-10-05.

Leave the default alone when the command exits non-zero. Record the stderr on Decision 0017’s revisit note, or in a superseding decision if the failure mode is new.

Do not load `qwen3.6:35b`, a coder-only tag, `deepseek-v4-flash:cloud`, or a 120B tag for this check. Do not start it while another bench holds Ollama. A killed process (the earlier retry ended 143) is not a model result.

## 2. Leave OQ-0016 open

[`OQ-0016`](OPEN_QUESTIONS.md) asks whether a second failure of the same repair region should widen to the parent. Decision 0014 retries that region until `max_repairs` (default 2) and does not widen.

Keep that behavior until a live run shows the same region failing twice for a reason a wider parent would fix. Then write a superseding decision before changing `repair_graph`. The Cursor branch’s `escalate_after` was not copied. That branch is `1982c58` and was deleted on 2026-10-07.

[`OQ-0017`](OPEN_QUESTIONS.md) asks whether the next live comparison should stay on Ollama, move to the home vLLM environment, or move to Lemonade. The default stays `qwen2.5:14b` on Ollama until a decision says otherwise.

## 3. pfy-mentat: I2 probe is on `build/local-lane-atg`

On 2026-10-06 the pfy branch `build/local-lane-atg` added the `llamacpp-nommap` lane and an atg-compile bench. A quiet-host run on Ollama `qwen3.6:35b` exited 0 with 2/10 sink-correct cases. That pull request merged as pfy-mentat #279. The catalog stage there is I2, not I3.

This repository does not import pfy. The scored tree was `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16`; the bench pin moved to `3c686b6` before the merge.

## 4. Publish on X from the handoff, not from a feature session

[`ops/x-publishing-handoff.md`](ops/x-publishing-handoff.md) is the thread plan, the claims a post may make, and the checks to run before anything is posted. Draft and post only in a session that is asked to do that, and only after naming the account.

The paper’s benchmark sentences stay attributed to Zhang et al. (2026). This repository’s demonstrated results are the offline toy, the unit tests, the 2026-10-06 14B live toy (sink value 25, width 2), and the toy PoC in [`poc/RESULTS.md`](poc/RESULTS.md). Do not post from a session that was not asked to post.

## 5. Stay inside the decisions that already closed scope

- Paper environments (ALFWorld, WebShop, ScienceWorld) stay deferred (Decision 0018, OQ-0012 wont-do).
- Core stays free of LangGraph, DSPy, and NetworkX imports (Decision 0002, Decision 0005, Decision 0016).
- History stays in memory, with a JSON file when the caller asks. SQLite waits on Decision 0015’s size trigger.
- The default model is `qwen2.5:14b` (Decision 0023). A larger tag in the sweep does not change it.

## Operator

Run step 1 only when the machine is free. Steps 3 and 4 have their own definitions of done in the handoff files. Step 2 is a watch item: if you see a live double failure, write it down on OQ-0016 and stop for a decision.

## Agent

Before editing code, `git fetch` and compare `HEAD` with `origin/main`, and list the other remote branches. Read those commits before writing a second copy of the same work.

| Next action | Allowed in this repo now | Stop when |
|-------------|--------------------------|-----------|
| Live remeasure | Yes, when `ollama ps` is empty | Exit 0 with the sink at 25, or a new decision note that records the failure |
| `escalate_after` / wider repair | No | A superseding ADR exists |
| Import this package from pfy | Already probed on `build/local-lane-atg` at I2. Do not merge that PR from here. | Tester and Reviewer merge it |
| Post to X | No, unless that session was asked to post and names the account | The X handoff’s pre-post checks pass |
| Port a paper benchmark | No | Decision 0018 is superseded |

Entry points, env vars, and invariants: [`USING.md`](USING.md) agent section and [`modules/runtime.md`](modules/runtime.md).
