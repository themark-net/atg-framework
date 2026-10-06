# RUN-LOG atg-finish

Branch: `build/atg-finish` from `origin/main` at `29bca8a`. Main checkout is not used. Date: 2026-10-06.

| Phase | Status | Note |
|-------|--------|------|
| A OpenAI client | DONE | Decision 0021. `tests/test_openai_client.py` 2 passed. Malformed reply then valid plan, sink 25. Timeout raises LLMError. |
| B PoC suite | DONE | Decision 0022. Offline llm_calls localized 16, global_replan 20, sequential 12. Success 12/12. Frozen reuse 6. |
| AB pytest gate | DONE | `uv run pytest -q -m "not integration"` → 38 passed, 1 deselected. |
| C Live toy 14B | DONE | Exit 0. `model=qwen2.5:14b ok=True repairs=0 waves=2 parallel=2 outputs={'add_results': {'value': 25}}`. Decision 0023. Model unloaded with keep_alive 0. |
| D Runtime sweep | PENDING | cite LOCAL-BENCH-5 for speed; skip Lemonade and vLLM |
| E Paper claims | PENDING | |
| F pfy integration | PENDING | only after a live pass |
| G Handoff and PR | PENDING | |

Host at start: `ollama ps` empty. MemAvailable about 71 GiB. No llama-server or vLLM process. LOCAL-BENCH-5: Lemonade skipped (no models). vLLM import blocked (`librocprofiler-sdk.so.1`, wheel wants ROCm 7.2.3, system is 7.1). Do not re-bench those speeds.
