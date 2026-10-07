# Handoff: toy PoC suite

**Status:** offline metrics for localized repair. Not a paper reproduction.
**Paper:** Zhang, Chen, Huang, Cui, Ji, and Wang (2026), arXiv:2607.01942, §4.3. This library is an independent reimplementation. See [`../ATTRIBUTION.md`](../ATTRIBUTION.md). Decision 0022.

## Command

```bash
uv run python examples/poc_suite.py
```

That writes `docs/poc/offline-report.json` and `docs/poc/offline-report.md` with MockLLM. No network. `--live` calls local Ollama and is not part of the unit test.

## What the test checks

`tests/test_poc_suite.py` runs the offline suite in-process and reads the JSON. Localized repair and global replan both succeed on all 12 tasks. The inequality is `localized llm_calls < global_replan llm_calls`. Localized `nodes_frozen_reused` is greater than 0. Sequential `max_parallel` is 1, and on the four tasks that fail once its `tool_calls` are greater than localized, because the replay runs finished tools again.

These numbers are toy-scale. They are not the paper's ALFWorld, WebShop, or ScienceWorld scores.
