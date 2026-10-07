# Handoff — atg-finish (2026-10-06)

Branch `build/atg-finish` in `/tmp/atg-finish`, from `origin/main` `29bca8a`. The founder checkout `~/DEVELOP/atg-framework` was not edited. Nine autonomous decisions are in `docs/ops/AUTONOMOUS-DECISIONS-2026-10-06.md`. This branch is not merged.

## What landed

| Phase | Result |
| --- | --- |
| A OpenAI client | Decision 0021. Malformed reply then a valid plan, sink 25. Timeout raises `LLMError`. |
| B PoC suite | Decision 0022. Offline localized 16 LLM calls, global replan 20, sequential 12. Success 12/12. Frozen reuse 6. |
| AB | `uv run pytest -q -m "not integration"` → 40 passed, 1 deselected after Decision 0024 (the gate commit itself was 38). |
| C 14B toy | Exit 0. `model=qwen2.5:14b ok=True repairs=0 waves=2 parallel=2 outputs={'add_results': {'value': 25}}`. Decision 0023. Default is `qwen2.5:14b`. Fallback `gemma4:latest` only. |
| D Sweep | `qwen3.6:35b` each arm 1/12 success, 1/12 valid plans, 12 LLM calls, 0 repairs, wall about 851–856s. Width 3 on localized and global, 1 on sequential. The success is `three_wide` value 12. coder-next not loaded. Lemonade and vLLM not loaded. |
| E Claims | `docs/poc/RESULTS.md`. Toy-scale. Paper numbers stay Zhang et al. (2026). |
| F pfy | Separate repo. Live compile exit 0, 2/10 sink-correct, wall 478s. Stage I2. Not I3. |
| G | This note. PRs not merged. Nothing posted on X. |

## Commands

```bash
cd /tmp/atg-finish
uv run pytest -q -m "not integration"
uv run python examples/poc_suite.py
uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only
uv run python examples/poc_suite.py --live --model qwen3.6:35b --only --report docs/poc/live-qwen36-35b.json
```

The 35B command needs a quiet host: empty `ollama ps`, no other model server, MemAvailable at least 22 GiB + 25 GiB. Unload with `keep_alive: 0` when finished.

## Measured numbers

Offline (`docs/poc/offline-report.json`): localized llm_calls 16, global_replan 20, sequential 12, success 12/12, frozen reuse 6, sequential max_parallel 1.

Live 35B (`docs/poc/live-qwen36-35b.json`): success 1, plan_ok 1, llm_calls 12, tool_calls 5, repairs 0, max_parallel 3 / 3 / 1. Wall 856s, 851s, 851s.

pfy live (`pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json` on `build/local-lane-atg`): n_valid 2, n_sink_correct 2, repairs 0, wall 478s, SHA `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16`.

Speed was not re-benched. pfy `docs/dogfood/LOCAL-BENCH-5-RUNTIMES.md` records Ollama `qwen3.6:35b` decode 96.4 tok/s.

## Blocked

| Item | Reason | Next step |
| --- | --- | --- |
| `qwen3-coder-next` llama-server `--no-mmap` | Blob 51,741,599,936 bytes. After the 35B unload, MemAvailable was 65.3 GiB. The gate is blob + 25 GiB. | Retry only when MemAvailable clears that sum, and only that process is yours to stop. |
| Lemonade port 13305 | LOCAL-BENCH-5: no downloaded models. A load starts a large pull. | Do not install a backend in this session. |
| vLLM | LOCAL-BENCH-5: `import vllm` fails (`librocprofiler-sdk.so.1`). Wheel wants ROCm 7.2.3. Host is 7.1.x. | Do not install system packages. |
| GitHub PR creation | `gh auth status` says not logged in. | Open the compare URLs below. Bodies are `/tmp/pr-atg-finish.md` and `/tmp/pr-pfy-local-lane.md`. |

## Pull requests

- atg-framework: https://github.com/themark-net/atg-framework/compare/main...build/atg-finish?expand=1
- pfy-mentat: https://github.com/themark-net/pfy-mentat/compare/main...build/local-lane-atg?expand=1

Tester and Reviewer merge. Do not merge from this handoff.
