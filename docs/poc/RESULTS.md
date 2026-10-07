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

## What this repository does not claim

The paper's environment scores are Zhang et al.'s. This run did not execute those environments (Decision 0018). A valid-plan rate of 1/12 on `qwen3.6:35b` is a property of this prompt and this tag on this day. It is not a ranking against GPT-4 or against the paper's 7B–8B agents.
