# TODO — Master Backlog (atg-framework)

**Purpose:** Ordered next steps and phase gates.

**Status legend:** `[ ]` todo · `[x]` done · `[!]` blocked (see OQ)

## Current focus

1. **Phases 3–5 first pass landed** (2026-09-20): planner, thought experiment, repair, LLM port, `ATGAgent`, offline example.
2. Next: validate the real-LLM path (Phase 5 gate) with a small local model; then decide OQ-0008 / OQ-0009 / OQ-0016 / OQ-0017 → ADRs.

## Session checkpoint — resume here (2026-09-20)

**State:** Phases 1–5 in tree as a first pass. Gate: `pytest` green (49 tests, mocks only). `python examples/weekend_trip.py` shows parallel width 3, one localized repair, two frozen nodes reused.

```
1. git pull
2. Read AGENTS.md, docs/TODO.md, docs/OPEN_QUESTIONS.md (0008, 0009, 0016, 0017)
3. Run examples/weekend_trip.py --real against ATG_MODEL; fix prompt/schema issues found on a small model
```

## Phase 3 — Planner

| Done | Item | Refs |
|------|------|------|
| [x] | `Decomposition` structured schema; `LLMClient.complete_structured` | Decision 0012, OQ-0005 |
| [x] | Interface-preserving splice (`$parent` inputs, `output_bindings`, consumer rewiring) | paper §4.1, Decision 0007 |
| [x] | Recursive refine loop with depth cap 6, `refine=False` honored | Decision 0007 |
| [x] | Snapshot after every refine step; lineage records | Decision 0009 |
| [ ] | Prompt tuning for 7B–8B class local models | OQ-0015, Phase 5 |

## Phase 4 — Thought experiment + repair

| Done | Item | Refs |
|------|------|------|
| [x] | Rules-based pre-check (atomicity, params, `$ref` fields); optional LLM judge flag | OQ-0008 (open — implemented per recommendation) |
| [x] | LCA over lineage; re-abstract region; freeze validated nodes; recompile only region | OQ-0009 (open — implemented per recommendation) |
| [x] | Failure-injection tests: frozen nodes never re-called | ARCH §3.3 criterion 4 |
| [ ] | Decide escalation policy | OQ-0016 |
| [ ] | Decide decomposition mini-language details | OQ-0017 |

## Phase 5 — Real LLM path

| Done | Item | Refs |
|------|------|------|
| [x] | `LiteLLMClient` behind `[llm]` extra; `ATG_MODEL` env | Decisions 0003, 0015 |
| [x] | `examples/weekend_trip.py` (`--real` flag) | — |
| [ ] | Documented run against a current small instruct model; record failure modes | ARCH §4.1 |
| [ ] | Optional `@pytest.mark.integration` e2e test | ARCH §5.5 |

## Housekeeping

| Done | Item | Refs |
|------|------|------|
| [ ] | Backfill ADR bodies 0011–0016 in `docs/DECISIONS.md` (index rows exist, text missing) | `docs/adr/README.md` |
| [ ] | Add `ruff` config + CI (`uv run pytest`) | Decision 0008 |
| [ ] | Module docs pass (`/docs`) for planner/thought/repair/agent | AGENTS.md |

## Phase 2 — Executor

| Done | Item | Refs |
|------|------|------|
| [x] | Parallel runtime default | Decision 0010 |
| [x] | Ready-queue executor | Decision 0011 |
| [x] | Node state transitions + metrics hooks | ARCH §5.6 |
| [x] | Tests: parallel width ≥ 2 | Decision 0004 |

Remaining human OQs: OQ-0008 thought experiment, OQ-0009 repair LCA, OQ-0016 escalation, OQ-0017 decomposition schema, OQ-0012 benchmarks (deferred).
