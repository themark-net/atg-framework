# RUN-LOG atg-finish

Branch: `build/atg-finish` from `origin/main` at `29bca8a`. Main checkout is not used. Date: 2026-10-06.

| Phase | Status | Note |
|-------|--------|------|
| A OpenAI client | DONE | Decision 0021. `tests/test_openai_client.py` 2 passed. Malformed reply then valid plan, sink 25. Timeout raises LLMError. |
| B PoC suite | DONE | Decision 0022. Offline llm_calls localized 16, global_replan 20, sequential 12. Success 12/12. Frozen reuse 6. |
| AB pytest gate | DONE | `uv run pytest -q -m "not integration"` → 38 passed, 1 deselected. |
| C Live toy 14B | DONE | Exit 0. `model=qwen2.5:14b ok=True repairs=0 waves=2 parallel=2 outputs={'add_results': {'value': 25}}`. Decision 0023. Model unloaded with keep_alive 0. |
| D Runtime sweep | DONE | `qwen3.6:35b` retry exit 1 with a report: each arm success 1/12, plan_ok 1/12, llm_calls 12, repairs 0, wall ~851–856s. Localized and global max_parallel 3; sequential 1. The success is `three_wide` value 12. coder-next BLOCKED (48.19 GiB blob + 25 GiB > 65.3 GiB MemAvailable). Lemonade SKIP and vLLM SKIP, cited from LOCAL-BENCH-5. Model unloaded with keep_alive 0. Speed not re-benched (Ollama decode 96.4 tok/s in that note). |
| E Paper claims | DONE | `docs/poc/RESULTS.md`. Offline localized 16 LLM calls vs global 20 at 12/12. Live 35B does not show that gap. |
| F pfy integration | DONE | Offline `241641e`. Live `qwen3.6:35b` exit 0, 2/10 sink-correct, repairs 0, wall 478s. Catalog I2. coder-next blocked on memory. Not I3. |
| G Handoff and PR | DONE | Handoff this file's date. `gh` is not logged in. Compare URLs are in the handoff. Not merged. |

Host at start: `ollama ps` empty. MemAvailable about 71 GiB. No llama-server or vLLM process. LOCAL-BENCH-5: Lemonade skipped (no models). vLLM import blocked (`librocprofiler-sdk.so.1`, wheel wants ROCm 7.2.3, system is 7.1). Do not re-bench those speeds.
