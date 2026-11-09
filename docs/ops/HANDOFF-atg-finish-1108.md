# Handoff: atg-finish 2026-11-08

This note is the status of the finish run Mark approved on 2026-11-08 ("Do items 1 through 4, including the ALFWorld benchmark with GPU runs"). The method is from Zhang et al. (2026), "Atomic Task Graph", arXiv:2607.01942 (`zhang2026atg`). This repository is an independent reimplementation. See [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

Read this file before another finish session. Per-task sinks stay in [`../poc/RESULTS.md`](../poc/RESULTS.md). Binding choices stay in [`../DECISIONS.md`](../DECISIONS.md).

Observed while writing this note:

- `origin/main` and this worktree (`bot/atg-finish-1108`) were `ae4891a302f82ee9755873eb310fcce8c699d33c`.
- The founder checkout `~/DEVELOP/atg-framework` was still `9393767`, behind `origin/main` by the nine commits below. It was not edited.
- `pfy-mentat` was not edited. There is no `ATG_SHA` file under `/home/mark/DEVELOP/atg-framework/tmp/finish/`.
- `NEEDS_MARK.md` does not exist. `STATUS.json` has `needs_mark: false` and `landed: {}`. The only park file is `1.parked`. There is no `LANDED_*` file. `LAST_LANDED_1` is `ae4891a302f82ee9755873eb310fcce8c699d33c`.
- Driver pid 3552321. Progress line: item 1 parked after round 6, then "item 1 did not land; items 2-4 gated (not started)".

"Did not land" means the item definition of done failed. The commits themselves are on `origin/main`.

## Status: stopped 2026-11-08, negative result

Mark stopped this finish run on 2026-11-08 at 4:21pm PT. Record the negative result. Do not start another finish session for items 1 to 4.

- Item 1 (six sessions, `qwen2.5:14b` and `qwen3.6:35b`, 12-task suite): graph validity is mostly fine (best arm 10/12, best localized 9/12 on `qwen3.6:35b` in session 5). Localized repair never beat full replan on model calls while succeeding at least as often. Session 5: `qwen3.6:35b` localized 9/12 with 23 calls, replan 10/12 with 16 calls, sequential 10/12 with 12 calls; `qwen2.5:14b` localized 5/12 with 23 calls, replan 8/12 with 18 calls, sequential 8/12 with 12 calls. The paper's localized-repair advantage did not reproduce at this scale. Write-up `ae4891a`. This handoff `31fda31`.
- Items 2 to 4 (ALFWorld, OQ-0016 / adapters / metrics, pfy-mentat plans with ATG) are cancelled by Mark. They never started.
- OQ-0016 and OQ-0017 are closed as `wont-do` in [`../OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md).

The old finish driver (pid 3552321) is gone. Do not relaunch `tmp/finish`.

## Item status

| Item | Status | SHAs | Numbers |
| --- | --- | --- | --- |
| 1. Valid graphs from local models | Parked. Both halves of the bar were required. The success half was met. The comparison half was not. | Code and scores are the nine commits under "Commits on main". Last measurement `b83acea`. Score writeup `ae4891a`. | Best arm 10/12. Best localized 9/12 with more model calls than full replan. See the table below. |
| 2. ALFWorld | Cancelled by Mark on 2026-11-08. Never started. | None. | No adapter, no extra, no `ALFWORLD_DATA`, no `docs/poc/ALFWORLD.md`, no eval numbers. |
| 3. OQ-0016, adapters, metrics | Cancelled by Mark on 2026-11-08. Never started. OQ-0016 and OQ-0017 closed as `wont-do`. | None. | Adapters stay Decision 0016 stubs. `Metrics` has no token or latency fields. |
| 4. pfy plans with ATG | Cancelled by Mark on 2026-11-08. Never started. | No new pin. | No live receipt, no model-call count. pfy-mentat records the negative result and holds ATG at I2. |

## What is parked, and why

Item 1 bar, from the ticket: at least 8/12 on one of `qwen2.5:14b` and `qwen3.6:35b`, and localized `llm_calls` below full replan with success no worse, on the 12-task suite with real models.

Six sessions ran. Five of them are scored plan-quality passes. Session 6 recorded session 5 and parked. GBNF was not used. The misses that remained were valid JSON: a wrong sink, a missing sink, an example id, or a repair that left a parent output unconsumed. A grammar does not fix those.

Best arm across the five scored passes: 10/12 (session 1 and session 4, `qwen2.5:14b` full replan and sequential; session 5, `qwen3.6:35b` full replan and sequential).

Best localized score: session 5, `qwen3.6:35b`, 9/12 with 23 model calls. The same pass full-replanned 10/12 with 16 calls.

Closest comparison: session 3, `qwen3.6:35b`, a tie at 2/12 and 32 calls (invalid structured output on ten tasks). Every other scored pass has fewer localized successes and more localized model calls than full replan.

The offline mock suite still shows the inequality the live runs did not: localized 12/12 and 16 LLM calls, global replan 12/12 and 20, sequential 12/12 and 12 (`docs/poc/offline-report.json`, Decision 0022). That is toy scale. It is not an ALFWorld score.

`DEFAULT_MODEL` stays `qwen2.5:14b` (Decision 0023). Decision 0014 stays: the same repair region, stop at `max_repairs`. `escalate_after` stays out.

## Scored live passes

Ollama 0.30.8. Tags already present, no pull: `qwen2.5:14b` `7cdf5a0187d5`, `qwen3.6:35b` `a7eb95c53bcf`. Grammar off. Both process exits were 1 on every scored pass because some tasks missed the sink. Exit 1 is the measurement.

Counts are success and `llm_calls`. L is localized repair, G is full replan, S is sequential replay.

| Pass | Code under test | Writeup commit | 14b L | 14b G | 14b S | 35b L | 35b G | 35b S |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `a80a4ba` | `ec0144e` | 7/12, 20 | 10/12, 17 | 10/12, 13 | 7/12, 22 | 9/12, 16 | 8/12, 12 |
| 2 | `d8bbe78` | `1aadcb6` | 7/12, 25 | 9/12, 21 | 9/12, 13 | 7/12, 20 | 9/12, 16 | 9/12, 12 |
| 3 | `3bf47f9` | `55de9a6` | 5/12, 30 | 6/12, 23 | 6/12, 17 | 2/12, 32 | 2/12, 32 | 2/12, 32 |
| 4 | `55de9a6` | `b83acea` | 5/12, 26 | 10/12, 20 | 10/12, 14 | 7/12, 20 | 9/12, 16 | 8/12, 12 |
| 5 | `b83acea` | `ae4891a` | 5/12, 23 | 8/12, 18 | 8/12, 12 | 9/12, 23 | 10/12, 16 | 10/12, 12 |

JSON reports: `docs/poc/live-qwen25-14b-2026-11-08.json` and `docs/poc/live-qwen36-35b-2026-11-08.json` for pass 1, then the same names with `-s2`, `-s3`, `-s4`, and `-s5`.

An earlier pass at `940d0ca` is not in that table. Every plan returned HTTP 400 (`json_schema: type must be string, but is object`) because the schema property was named `$ref`. `qwen2.5:14b` was 0/12 on every arm. `qwen3.6:35b` was stopped after 4 tasks. That is Decision 0026, not a plan-quality score. Journals from that pass are not in git (`tmp/jobs/rejected-400/`).

The 2026-10-06 `qwen3.6:35b` suite, before Decisions 0025-0027, was 1/12 valid plans on every arm (`docs/poc/live-qwen36-35b.json`). Repair never ran. Do not quote that table as the current planner.

## Commits on main

These nine commits are on `origin/main` at `ae4891a`. The driver landed each session head after a quick check. Full hashes:

| Short | Full | What it is |
| --- | --- | --- |
| `940d0ca` | `940d0caad3c3cd2c65def2cbc7838860d04f84ef` | Decision 0025. Schema from `REF_PATTERN`. Compile fix-up, up to 3 plans. `compile_retries` is separate from `repairs`. |
| `a80a4ba` | `a80a4ba2e82001d348e94a3b3468b7715050290b` | Decision 0026. Ollama `format` inlines `$defs`, omits a property named `$ref`, and sets `think` false. Code under test for pass 1. |
| `ec0144e` | `ec0144ea92e0ccb1bf58d17815ee27672184ff60` | Pass 1 reports. Landed, round 1. |
| `d8bbe78` | `d8bbe78756fceddaa6a2d21e712d451ae98bbda9` | Few-shot ids start with `example_`. Sibling rule. Code under test for pass 2. |
| `1aadcb6` | `1aadcb628370454eacd316a09903fcbd4e91bd19` | Pass 2 reports. Landed, round 2. |
| `3bf47f9` | `3bf47f94dbd9efba8a86c04121927cecd0137eb8` | Root example is literals only. Code under test for pass 3. Landed, round 3. |
| `55de9a6` | `55de9a6cbb5734d2ec1227aa65659827d65ca931` | Pass 3 reports, and the root example shows a child `$ref` again. Code under test for pass 4. Landed, round 4. |
| `b83acea` | `b83acead7fb5e5399a79fba7e9a2bd660f46617a` | Pass 4 reports and Decision 0027 (drop a self-edge, add the edge an internal `$ref` already names). Code under test for pass 5. Landed, round 5. |
| `ae4891a` | `ae4891a302f82ee9755873eb310fcce8c699d33c` | Pass 5 reports, OQ-0016 note, park. Landed, round 6. |

`$ref` strings are not rewritten (Decision 0024, Decision 0025, Decision 0027).

## Items 2, 3, and 4

Item 2 was going to supersede Decision 0018 ("Mark approved 2026-11-08: reproduce ALFWorld"), set OQ-0012 accordingly, add an `alfworld` extra, put data in `/home/mark/DEVELOP/atg-framework/tmp/finish/data/alfworld`, and write `docs/poc/ALFWORLD.md`. None of that is in the tree. `pyproject.toml` extras are `dev` and `llm` only. OQ-0012 status is still `wont-do`. Decision 0018 is still accepted. Mark's approval is in the finish brief. It is not an ADR. A later session that starts ALFWorld has to record the superseding decision first and must not edit the old ADR text except for a superseded-by link.

Item 3 was going to settle OQ-0016 from item 1 and item 2 evidence, replace the LangGraph and DSPy stubs with real libraries under optional extras, and add per-step model calls, prompt and completion tokens, latency, and repair scope to `src/atg/metrics.py`. None of that started. `src/atg/integrations/langgraph_adapter.py` and `dspy_adapter.py` still return plain callables and do not import either framework (Decision 0016). `Metrics` fields are `waves`, `tool_calls`, `max_parallel`, `failures`, `repairs`, `compile_retries`, `nodes_frozen_reused`, `judge_disagreements`, and `notes`. Suite reports count `llm_calls` outside that model. There is no token field and no latency field.

The session 5 note on OQ-0016 is evidence, not a settlement. On `qwen2.5:14b`, localized `scale_sum` and `parallel_prod` each spent `repairs=2` and finished with no unique sink. Full replan of those two tasks also finished with no unique sink. A wider parent is not shown to fix them. Recommendation stays: keep Decision 0014 until a live run shows a double failure that a wider parent would fix.

Item 4 was a pfy-mentat change: re-pin ATG, plan through ATG on a live local-model path, and commit a receipt with a real model call. No session ran. Catalog stage for atomic-task-graph-atg stays where pfy-mentat #279 left it (I2). Do not raise that ceiling from this repo.

## What needs Mark

1. Whether the parked item 1 result is enough, or whether another prompt or compiler pass is worth a new bar. Do not treat 10/12 on a replan arm as the item being done. Do not launch another suite from the session 1-5 journals. Those journals match older prompts. Resuming them skips finished rows.
2. Whether items 2, 3, and 4 should start after this park. The 2026-11-08 approval said to do them. The driver stopped because item 1 parked. Starting item 2 still requires a superseding ADR. Decision 0018 is the text in the repo today.
3. Nothing is blocked on a model download. No pull over 25 GB was requested. `NEEDS_MARK.md` was not created.
4. OQ-0017 stays open. The 2026-10-07 home vLLM toy (`Qwen/Qwen2.5-14B-Instruct-AWQ` on `127.0.0.1:8001`) exited 1. Do not load that checkpoint again for the same check. Lemonade is still unscored. `DEFAULT_MODEL` stays `qwen2.5:14b`.
5. Do not post on X from this note. Allowed claims are in [`x-publishing-handoff.md`](x-publishing-handoff.md). This run did not reproduce ALFWorld, WebShop, or ScienceWorld. Localized repair did not beat full replan on the live 12-task suite.
6. This session does not push. The driver lands the handoff commit.

## Commands

Run these from a checkout that contains `ae4891a` or a descendant that has not changed `src/atg/planner.py`, `src/atg/repair.py`, or `src/atg/llm.py`. Pass 5 was measured at `b83acea`. `ae4891a` did not change those files.

Offline suite. This rewrites `docs/poc/offline-report.json` and `docs/poc/offline-report.md`, including `wall_time_s`. The success counts to expect are 12/12, 16, 20, and 12 LLM calls. Do not commit a wall-time-only diff.

```bash
uv run --inexact python examples/poc_suite.py
```

Unit tests, no live model:

```bash
uv run --inexact --extra dev pytest -q -m "not integration"
```

On 2026-11-08, after this note was drafted and before it was committed, that command was 63 passed and 1 deselected (3.99s). Session 6 had recorded the same count. `ae4891a` did not change tests. The integration marker is the live Ollama test and stays deselected unless `ATG_RUN_INTEGRATION=1`.

14B toy, only when `ollama ps` is empty. Decision 0023 already passed this on 2026-10-06 (exit 0, `waves=2`, `parallel=2`, sink value 25). It is not the 12-task suite.

```bash
uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only
```

Live 12-task suite. One tag at a time, inside the model lock, on a fresh report path. The lock waits while another lane holds `~/.cache/pfy/locks/local-model.lock`. A new `--report` path creates a new journal (`<report>.jsonl`). A path that already has a journal skips rows that are already in it.

```bash
/home/mark/DEVELOP/atg-framework/tmp/finish/model_lock.sh \
  uv run --inexact python examples/poc_suite.py --live --model qwen2.5:14b --only \
  --report tmp/jobs/rerun-qwen25-14b.json
/home/mark/DEVELOP/atg-framework/tmp/finish/model_lock.sh \
  uv run --inexact python examples/poc_suite.py --live --model qwen3.6:35b --only \
  --report tmp/jobs/rerun-qwen36-35b.json
```

The command that produced pass 5, from `tmp/jobs/s5-suite.sh`, was the same `uv` line with `--report tmp/jobs/s5-qwen25-14b.json` and `--report tmp/jobs/s5-qwen36-35b.json`. Those journals are complete. Resuming them does not remeasure. Both processes exited 1.

Do not add `--grammar` on the Ollama client. `examples/poc_suite.py --grammar` requires `--client openai` and a llama-server. That path was not the measured one.

## ALFWorld

There is no command that reruns an ALFWorld eval in this repository. Item 2 did not start. `examples/poc_suite.py` states that its numbers are not ALFWorld, WebShop, or ScienceWorld scores. The paper's environment tables stay Zhang et al. (2026).

Do not invent a runner. When an ADR supersedes Decision 0018, the finish ticket's setup was: optional extra `alfworld`, data directory `/home/mark/DEVELOP/atg-framework/tmp/finish/data/alfworld` (`ALFWORLD_DATA`), adapter and offline tests outside core, then a smoke slice and the eval split under `model_lock.sh`. Until that ADR and that code exist, the only honest statement is that this tree has no ALFWorld result.

## Open questions

| ID | Status | What this run did |
| --- | --- | --- |
| OQ-0012 | `wont-do` (Decision 0018) | Unchanged. Mark approved ALFWorld in the finish brief. No session recorded that as an ADR. |
| OQ-0016 | `open` | Session 5 appended a note. Two 14b tasks hit `max_repairs` and full replan missed the same sinks. Not promoted. |
| OQ-0017 | `open` | Untouched. Home vLLM toy remains the 2026-10-07 exit 1. Lemonade remains unscored. |

No new OQ was opened. The parked bar is a measured result, not a new design question. A decision to change repair width, the default model, or the benchmark deferral still needs an ADR.

## Agent

- Entry point for this run's status: this file. Last live code: `b83acead7fb5e5399a79fba7e9a2bd660f46617a`. Last score commit: `ae4891a302f82ee9755873eb310fcce8c699d33c`.
- Do not write `ITEM_DONE` for item 1. The comparison half of the bar is unmet.
- Do not import LangGraph, DSPy, or NetworkX from core (Decision 0002).
- Do not rewrite a short `$ref` (Decision 0024).
- Do not set `DEFAULT_MODEL` from a larger tag in the sweep (Decision 0023).
- Do not push. Do not edit the founder checkout or `pfy-mentat` from a finish worktree.
