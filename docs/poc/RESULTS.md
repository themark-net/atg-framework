# Toy-scale reproduction of Atomic Task Graph claims

This note records what `atg-framework` reproduced on 2026-10-06. It is a miniature synthetic-tool run. It is not a reproduction of the paper's ALFWorld, WebShop, or ScienceWorld tables. Those scores stay Zhang et al. (2026), arXiv:2607.01942 (`zhang2026atg`). Decision 0018 defers those environments.

The method ideas (typed graph compilation, parallel waves, localized repair) are from that paper. This repository is an independent reimplementation. See `docs/ATTRIBUTION.md`.

## What the offline suite reproduces

`MockLLM`, 12 tasks, 4 of them with one injected tool failure. Report: `docs/poc/offline-report.json`. Decision 0022 defines the metrics.

| Arm | Success | LLM calls | Tool calls | Frozen nodes reused | Repairs | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 12/12 | 16 | 37 | 6 | 4 | 3 |
| Global replan | 12/12 | 20 | 43 | 0 | 4 | 3 |
| Sequential | 12/12 | 12 | 43 | 0 | 0 | 1 |

Localized repair used fewer LLM calls than global replan at the same success count. That is the paper's §4.3 claim at toy scale: freeze the siblings that already succeeded and recompile the failed region. The sequential arm uses still fewer calls because it never replans. Its widest wave is 1.

Typed validation rejects a short `$ref` such as `add_step.value` before any tool runs (`CompileError`, Decision 0024).

## What the live `qwen3.6:35b` suite did

Command: `uv run python examples/poc_suite.py --live --model qwen3.6:35b --only --report docs/poc/live-qwen36-35b.json`

Ollama on this host. The first attempt aborted before a report. Decision 0024 made that failure a per-task compile error. The retry wrote the report and exited 1 because 11 of 12 tasks did not succeed. Exit 1 here is the measurement, not a crash.

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 1/12 | 1/12 | 12 | 5 | 0 | 0 | 856 s | 3 |
| Global replan | 1/12 | 1/12 | 12 | 5 | 0 | 0 | 851 s | 3 |
| Sequential | 1/12 | 1/12 | 12 | 5 | 0 | 0 | 851 s | 1 |

The one success on every arm is `three_wide`: sink `value` 12, one LLM call, five tool calls, no repair. Localized and global replan reached a ready-queue width of 3 on that task. Sequential stayed at width 1.

The other 11 plans were rejected before a tool ran. The errors were a sink that dropped declared output `value`, a `$ref` that was not `node_id.outputs.field`, or a `$ref` whose producer was not an ancestor. Because those graphs never executed, localized repair had no failed region to freeze. LLM calls match global replan. This live tag does not show the offline call reduction.

Token rate was not re-measured. pfy-mentat `docs/dogfood/LOCAL-BENCH-5-RUNTIMES.md` already records this tag on Ollama: load 16.9 s, prefill 791 tok/s, decode 96.4 tok/s, 79.2% on that bench's 48 cases, RSS about 20.5 GiB.

## Runtimes that were not loaded

| Runtime | This session | Why |
| --- | --- | --- |
| `qwen3-coder-next` via llama-server `--no-mmap` | Not loaded | Blob is 51,741,599,936 bytes (48.19 GiB). The gate is that size plus 25 GiB, about 73.2 GiB. After unloading `qwen3.6:35b`, MemAvailable was 65.3 GiB. |
| Lemonade on port 13305 | Not loaded | LOCAL-BENCH-5: no downloaded models. A load would start a large pull. |
| vLLM | Not loaded | LOCAL-BENCH-5: import fails (`librocprofiler-sdk.so.1`). The wheel wants ROCm 7.2.3. This host is 7.1.x. Nothing was installed to change that. |

`DEFAULT_MODEL` stays `qwen2.5:14b` (Decision 0023). The 14B toy on 2026-10-06 exited 0: sink `{'add_results': {'value': 25}}`, two waves, width 2. This sweep does not change that default.

## Structured-output rerun (started 2026-11-08)

Decision 0025. The planner schema is built from `REF_PATTERN` in `src/atg/types.py` (the same pattern as `parse_ref`). Ollama receives it as `format`. A plan that fails validation is sent back with that error, up to 3 attempts. Those extra calls are `compile_retries`. They are included in `llm_calls` and are not `repairs`. The prompt credits Zhang et al. (2026) and includes one few-shot example taken from the tool catalog.

The scripted suite is unchanged on the comparison that Decision 0022 defined: localized 12/12 and 16 LLM calls, global replan 12/12 and 20, sequential 12/12 and 12, `compile_retries` 0. That is `docs/poc/offline-report.json`.

First live pass, git `940d0caad3c3cd2c65def2cbc7838860d04f84ef`, Ollama 0.30.8. Both tags were already installed (`qwen2.5:14b` id `7cdf5a0187d5`, `qwen3.6:35b` id `a7eb95c53bcf`). No pull. Command, under the model lock:

```bash
uv run --inexact python examples/poc_suite.py --live --model qwen2.5:14b --only --report tmp/jobs/live-qwen25-14b.json
uv run --inexact python examples/poc_suite.py --live --model qwen3.6:35b --only --report tmp/jobs/live-qwen36-35b.json
```

`qwen2.5:14b` finished every arm at success 0/12, `plan_ok` false, `llm_calls` 12, `compile_retries` 0, `tool_calls` 0. All 36 rows are `LLMError: ollama request failed for qwen2.5:14b: HTTP Error 400: Bad Request`. The 35b arm was stopped after 4 tasks (`add_pair`, `mul_pair`, `scale_sum`, `parallel_sums` on the localized arm), each the same HTTP 400, so it is not a 12-task score. llama-server's body was `json_schema: type must be string, but is object`. The schema's `RefBinding` property is named `$ref`. That is Decision 0026. This pass did not measure plan quality. The last measured generation result remains the 1/12 table above.

Corrected client, Decision 0026, git `a80a4ba2e82001d348e94a3b3468b7715050290b`. Same command and the same two tags. Ollama 0.30.8. No pull. The run started `2026-11-08T12:24:02-08:00` and finished `2026-11-08T12:43:04-08:00`. Reports: `docs/poc/live-qwen25-14b-2026-11-08.json` and `docs/poc/live-qwen36-35b-2026-11-08.json`. Both process exits were 1 because some tasks missed the expected sink. That is the measurement.

`qwen2.5:14b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 7/12 | 11/12 | 20 | 33 | 5 | 3 | 4 | 274 s | 3 |
| Global replan | 10/12 | 12/12 | 17 | 48 | 0 | 4 | 1 | 286 s | 3 |
| Sequential | 10/12 | 12/12 | 13 | 45 | 0 | 0 | 1 | 203 s | 1 |

`qwen3.6:35b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 7/12 | 9/12 | 22 | 24 | 0 | 1 | 6 | 180 s | 3 |
| Global replan | 9/12 | 12/12 | 16 | 48 | 0 | 4 | 0 | 118 s | 3 |
| Sequential | 8/12 | 12/12 | 12 | 42 | 0 | 0 | 0 | 81 s | 1 |

Per task, actual sink (`Y` expected value, `n` miss). `L` localized, `G` global replan, `S` sequential.

| Task | Expected | 14b L | 14b G | 14b S | 35b L | 35b G | 35b S |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| add_pair | 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 |
| mul_pair | 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 |
| scale_sum | 20 | Y 20 | Y 20 | Y 20 | Y 20 | Y 20 | Y 20 |
| parallel_sums | 10 | Y 10 | Y 10 | Y 10 | Y 10 | Y 10 | Y 10 |
| parallel_prod | 29 | Y 29 | Y 29 | Y 29 | Y 29 | Y 29 | Y 29 |
| diamond | 18 | n 14 | n 14 | n 14 | n 12 | n 12 | n 12 |
| three_wide | 12 | Y 12 | Y 12 | Y 12 | Y 12 | Y 12 | Y 12 |
| nested_chain | 36 | Y 36 | Y 36 | Y 36 | Y 36 | Y 36 | Y 36 |
| fail_parallel | 25 | n | Y 25 | Y 25 | n | n | n |
| fail_chain | 21 | n 20 | Y 21 | Y 21 | n | n | n |
| fail_diamond | 14 | n 24 | n 24 | n 24 | n 2 | Y 14 | n |
| fail_wide | 12 | n 8 | Y 12 | Y 12 | n | Y 12 | Y 12 |

Localized repair did not beat full replan. On both tags it solved fewer tasks and used more model calls. The best arm is global replan on `qwen2.5:14b` at 10/12. The bar (8/12 and localized calls below replan with success no worse) is not met. `diamond` compiled on every arm and still returned the wrong sink, so repair never started. The 14b localized repair of `fail_parallel` exhausted the compile budget on an external `$ref` to `step.outputs.value`, which is the id in the few-shot example. GBNF was not used for this Ollama rerun.

## Prompt pass (2026-11-08, session 2)

Git `d8bbe78756fceddaa6a2d21e712d451ae98bbda9`. The few-shot no longer uses the id `step`. When the parent already has a `$ref`, the example copies that ref. Otherwise the example ids start with `example_`, and the prompt forbids emitting that prefix. The prompt also says that two operations on the same value in parallel are siblings. Ollama 0.30.8. Same tags, no pull: `qwen2.5:14b` `7cdf5a0187d5`, `qwen3.6:35b` `a7eb95c53bcf`. Started `2026-11-08T12:58:04-08:00`, finished `2026-11-08T13:18:53-08:00`. Fresh journals (the Decision 0026 JSONL was not resumed). Both process exits were 1 because some tasks missed the sink. Reports: `docs/poc/live-qwen25-14b-2026-11-08-s2.json` and `docs/poc/live-qwen36-35b-2026-11-08-s2.json`.

```bash
uv run --inexact python examples/poc_suite.py --live --model qwen2.5:14b --only --report tmp/jobs/s2-qwen25-14b.json
uv run --inexact python examples/poc_suite.py --live --model qwen3.6:35b --only --report tmp/jobs/s2-qwen36-35b.json
```

`qwen2.5:14b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 7/12 | 10/12 | 25 | 28 | 7 | 4 | 7 | 342 s | 3 |
| Global replan | 9/12 | 12/12 | 21 | 43 | 0 | 6 | 3 | 338 s | 3 |
| Sequential | 9/12 | 12/12 | 13 | 42 | 0 | 0 | 1 | 199 s | 1 |

`qwen3.6:35b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 7/12 | 10/12 | 20 | 30 | 0 | 2 | 4 | 174 s | 3 |
| Global replan | 9/12 | 12/12 | 16 | 47 | 0 | 4 | 0 | 117 s | 3 |
| Sequential | 9/12 | 12/12 | 12 | 42 | 0 | 0 | 0 | 78 s | 1 |

Per task, actual sink (`Y` expected value, `n` miss, `n null` when the sink was missing or not unique). `L` localized, `G` global replan, `S` sequential.

| Task | Expected | 14b L | 14b G | 14b S | 35b L | 35b G | 35b S |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| add_pair | 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 |
| mul_pair | 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 |
| scale_sum | 20 | Y 20 | n null | n null | Y 20 | Y 20 | Y 20 |
| parallel_sums | 10 | Y 10 | Y 10 | Y 10 | Y 10 | Y 10 | Y 10 |
| parallel_prod | 29 | n null | n null | n null | Y 29 | Y 29 | Y 29 |
| diamond | 18 | Y 18 | Y 18 | Y 18 | n 10 | n 10 | n 10 |
| three_wide | 12 | Y 12 | Y 12 | Y 12 | Y 12 | Y 12 | Y 12 |
| nested_chain | 36 | Y 36 | Y 36 | Y 36 | Y 36 | Y 36 | Y 36 |
| fail_parallel | 25 | n | Y 25 | Y 25 | n null | n null | n null |
| fail_chain | 21 | n null | Y 21 | Y 21 | n 5 | n null | n null |
| fail_diamond | 14 | n | n null | n 18 | n | Y 14 | Y 14 |
| fail_wide | 12 | n 8 | Y 12 | Y 12 | n | Y 12 | Y 12 |

Localized repair still does not beat full replan. On both tags it solved fewer tasks and used more model calls (14b 25 vs 21, 35b 20 vs 16). The best arm on this run is 9/12. The bar is not met. `qwen2.5:14b` `diamond` is 18 on every arm, so the sibling rule landed for that tag. `qwen3.6:35b` `diamond` is 10 on every arm, three tool calls, no repair: a valid plan with the wrong sink. The 14b localized repair of `fail_parallel` no longer cites `step`. It stops on a self-edge (`product_4_and_5` to itself). The 14b localized repair of `fail_diamond` still emits `example_src.outputs.a`, which the prompt forbids. That id is still in the example when the parent has no `$ref` to copy. GBNF was not used. `DEFAULT_MODEL` stays `qwen2.5:14b`.

## Literals-only root example (2026-11-08, session 3)

Git `3bf47f94dbd9efba8a86c04121927cecd0137eb8`. The root few-shot is one `example_dst` node with literal inputs and no edges. A `$ref` is copied only when that producer is already on the parent. `example_src` is not in the example. The sibling rule is unchanged. Ollama 0.30.8. Same tags, no pull: `qwen2.5:14b` `7cdf5a0187d5`, `qwen3.6:35b` `a7eb95c53bcf`. The run waited on the model lock, then started `2026-11-08T13:50:23-08:00` and finished `2026-11-08T14:19:45-08:00`. Fresh journals (session 2 and the Decision 0026 JSONL were not resumed). Both process exits were 1. Reports: `docs/poc/live-qwen25-14b-2026-11-08-s3.json` and `docs/poc/live-qwen36-35b-2026-11-08-s3.json`.

```bash
uv run --inexact python examples/poc_suite.py --live --model qwen2.5:14b --only --report tmp/jobs/s3-qwen25-14b.json
uv run --inexact python examples/poc_suite.py --live --model qwen3.6:35b --only --report tmp/jobs/s3-qwen36-35b.json
```

`qwen2.5:14b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 5/12 | 9/12 | 30 | 19 | 10 | 7 | 9 | 389 s | 2 |
| Global replan | 6/12 | 10/12 | 23 | 40 | 0 | 5 | 6 | 373 s | 3 |
| Sequential | 6/12 | 10/12 | 17 | 34 | 0 | 0 | 5 | 267 s | 1 |

`qwen3.6:35b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 2/12 | 2/12 | 32 | 2 | 0 | 0 | 20 | 254 s | 1 |
| Global replan | 2/12 | 2/12 | 32 | 2 | 0 | 0 | 20 | 237 s | 1 |
| Sequential | 2/12 | 2/12 | 32 | 2 | 0 | 0 | 20 | 242 s | 1 |

Per task, actual sink (`Y` expected value, `n` miss, `n null` when the sink was missing or not unique). `L` localized, `G` global replan, `S` sequential. A bare `n` on `qwen3.6:35b` is `CompileError: returned invalid structured output` after two compile retries.

| Task | Expected | 14b L | 14b G | 14b S | 35b L | 35b G | 35b S |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| add_pair | 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 |
| mul_pair | 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 |
| scale_sum | 20 | n null | n | n | n | n | n |
| parallel_sums | 10 | Y 10 | Y 10 | Y 10 | n | n | n |
| parallel_prod | 29 | n null | n null | n null | n | n | n |
| diamond | 18 | Y 18 | Y 18 | Y 18 | n | n | n |
| three_wide | 12 | n | n | n | n | n | n |
| nested_chain | 36 | Y 36 | Y 36 | Y 36 | n | n | n |
| fail_parallel | 25 | n | Y 25 | Y 25 | n | n | n |
| fail_chain | 21 | n 20 | n null | n null | n | n | n |
| fail_diamond | 14 | n null | n 20 | n 20 | n | n | n |
| fail_wide | 12 | n | n null | n null | n | n | n |

This pass is worse than session 2 on both tags. Localized repair still does not beat full replan. The best arm is 6/12. The bar is not met. `qwen2.5:14b` `diamond` stays 18. `three_wide` and `scale_sum` compiled a `$ref` whose producer is not an ancestor (the edge is missing). `qwen3.6:35b` solved only `add_pair` and `mul_pair`. The other ten tasks on every arm are `invalid structured output`, with no tool call. Removing the `$ref` object from the root example matches that collapse. `example_src` does not appear in the 14b errors. GBNF was not used. `DEFAULT_MODEL` stays `qwen2.5:14b`.

## Root example shows a child `$ref` again (2026-11-08, session 4)

Git `55de9a6cbb5734d2ec1227aa65659827d65ca931`. A root compile shows `example_src`, `example_dst`, a `$ref`, and the edge. A repair does not show `example_src`. A plan that emits an `example_` id is a compile retry. Schema failures name up to three fields. Ollama 0.30.8. Same tags, no pull: `qwen2.5:14b` `7cdf5a0187d5`, `qwen3.6:35b` `a7eb95c53bcf`. The run waited on the model lock, then started `2026-11-08T14:42:43-08:00` and finished `2026-11-08T15:02:50-08:00`. Fresh journals (session 3, session 2, and the Decision 0026 JSONL were not resumed). Both process exits were 1. Reports: `docs/poc/live-qwen25-14b-2026-11-08-s4.json` and `docs/poc/live-qwen36-35b-2026-11-08-s4.json`.

```bash
uv run --inexact python examples/poc_suite.py --live --model qwen2.5:14b --only --report tmp/jobs/s4-qwen25-14b.json
uv run --inexact python examples/poc_suite.py --live --model qwen3.6:35b --only --report tmp/jobs/s4-qwen36-35b.json
```

`qwen2.5:14b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 5/12 | 9/12 | 26 | 23 | 7 | 5 | 7 | 323 s | 3 |
| Global replan | 10/12 | 12/12 | 20 | 42 | 0 | 5 | 3 | 319 s | 3 |
| Sequential | 10/12 | 12/12 | 14 | 41 | 0 | 0 | 2 | 216 s | 1 |

`qwen3.6:35b`:

| Arm | Success | Valid plans | LLM calls | Tool calls | Frozen reuse | Repairs | Compile retries | Wall | Widest wave |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Localized repair | 7/12 | 10/12 | 20 | 27 | 0 | 2 | 4 | 156 s | 3 |
| Global replan | 9/12 | 12/12 | 16 | 47 | 0 | 4 | 0 | 111 s | 3 |
| Sequential | 8/12 | 12/12 | 12 | 42 | 0 | 0 | 0 | 82 s | 1 |

Per task, actual sink (`Y` expected value, `n` miss, `n null` when the sink was missing or not unique). `L` localized, `G` global replan, `S` sequential.

| Task | Expected | 14b L | 14b G | 14b S | 35b L | 35b G | 35b S |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| add_pair | 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 | Y 5 |
| mul_pair | 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 | Y 42 |
| scale_sum | 20 | n null | n null | n null | Y 20 | Y 20 | Y 20 |
| parallel_sums | 10 | Y 10 | Y 10 | Y 10 | Y 10 | Y 10 | Y 10 |
| parallel_prod | 29 | n null | Y 29 | Y 29 | Y 29 | Y 29 | Y 29 |
| diamond | 18 | n 28 | Y 18 | Y 18 | n 10 | n 10 | n 10 |
| three_wide | 12 | Y 12 | Y 12 | Y 12 | Y 12 | Y 12 | Y 12 |
| nested_chain | 36 | Y 36 | Y 36 | Y 36 | Y 36 | Y 36 | Y 36 |
| fail_parallel | 25 | n | n null | n null | n null | n null | n null |
| fail_chain | 21 | n 20 | Y 21 | Y 21 | n | n 41 | n 41 |
| fail_diamond | 14 | n | Y 14 | Y 14 | n 2 | Y 14 | n null |
| fail_wide | 12 | n | Y 12 | Y 12 | n | Y 12 | Y 12 |

Localized repair still does not beat full replan. The best arm is 10/12, on `qwen2.5:14b` full replan and sequential. The bar is not met. `qwen2.5:14b` recovered from the session 3 collapse (`qwen3.6:35b` is no longer stuck on `invalid structured output`). The localized misses that never ran a tool are structural: `fail_parallel` and `fail_diamond` ended on a self-edge, and `fail_wide` named `join_results.outputs.value` without the edge `join_results -> final_join`. On `qwen3.6:35b`, the localized repairs of `fail_chain` and `fail_wide` reused a parent producer id, so the subgraph did not consume the parent inputs. `diamond` on that tag is 10 on every arm (three tool calls, no repair): a valid plan with the wrong sink. GBNF was not used. Decision 0027 drops a self-edge, adds the edge an internal `$ref` already names, and puts the original task sentence on the repair note. `DEFAULT_MODEL` stays `qwen2.5:14b`.

## What this repository does not claim

The paper's environment scores are Zhang et al.'s. This run did not execute those environments (Decision 0018). A valid-plan rate of 1/12 on `qwen3.6:35b` is a property of this prompt and this tag on this day. It is not a ranking against GPT-4 or against the paper's 7B–8B agents.
