# TODO — Master Backlog (atg-framework)

**Purpose:** Ordered next steps and phase gates.

**Status legend:** `[ ]` todo · `[x]` done · `[!]` blocked (see OQ)

## Current focus

1. **Phase 2 executor landed** (2026-09-03): ready-queue + thread runner + metrics.
2. Next code: Phase 3 planner mock compile (Decision 0012), or chat OQ-0008 / OQ-0009.

## Session checkpoint — resume here (2026-09-03)

**State:** Phase 1–2 in tree. Gate: `PYTHONPATH=src pytest` green, no LLM. Parallel diamond test asserts max_parallel ≥ 2.

```
1. git pull
2. Read AGENTS.md, docs/TODO.md, docs/DECISIONS.md (0005–0016)
3. Start Phase 3 planner unless user asks for remaining OQs (0008, 0009)
```

## Phase 2 — Executor

| Done | Item | Refs |
|------|------|------|
| [x] | Parallel runtime default | Decision 0010 |
| [x] | Ready-queue executor | Decision 0011 |
| [x] | Node state transitions + metrics hooks | ARCH §5.6 |
| [x] | Tests: parallel width ≥ 2 | Decision 0004 |

Remaining human OQs: OQ-0008 thought experiment, OQ-0009 repair LCA, OQ-0012 benchmarks (deferred).
