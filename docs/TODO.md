# TODO — Master Backlog (atg-framework)

**Purpose:** Ordered next steps and phase gates.  
**Not for:** Long-form design (→ [`ARCHITECTURE.md`](ARCHITECTURE.md)), binding choices (→ [`DECISIONS.md`](DECISIONS.md)), parked questions (→ [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md)).

**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked (see OQ)

---

## Current focus

1. **Phase 1 skeleton landed** (2026-09-03): `src/atg` + pytest green, no LLM.  
2. Next code: Phase 2 executor consuming `TaskGraph.ready_set()` (Decision 0011).  

**Recently closed:** OQ-0007→**0011**; OQ-0005→**0012**; OQ-0013→**0013**; OQ-0014→**0014**; OQ-0015→**0015**; OQ-0011→**0016**.

---

## Session checkpoint — resume here (2026-09-03)

**State:** Phase 1 foundations in tree: `src/atg` (types, graph, history, tools, validation) + tests. Gate: `PYTHONPATH=src pytest` green, no LLM.

### Done this session

Phase 1 package + tests landed. Decisions 0011–0016 accepted from chat.

### How agents should resume

```
1. git pull
2. Read AGENTS.md, docs/TODO.md, docs/DECISIONS.md (0005–0016)
3. Start Phase 2 executor unless user asks for remaining OQs (0008, 0009)
```

---

## Phase 1 — Foundations (MVP critical path)

**Gate:** `pytest` green; DAG create/topo/cycle/freeze without LLM.

| Done | Item | Refs |
|------|------|------|
| [x] | Decide packaging layout | Decision 0008 |
| [x] | `pyproject.toml` + `src/atg` package skeleton | Decision 0008 |
| [x] | `atg.types` + `atg.graph` | ARCH §5.1–5.2 |
| [x] | `atg.history` full snapshot list | Decision 0009 |
| [x] | `atg.validation` | ARCH §5.5 |
| [x] | Unit tests | ARCH §3.3 |
| [x] | Package `__init__` attribution blurb | ATTRIBUTION.md |

## Phase 2 — Executor

| Done | Item | Refs |
|------|------|------|
| [x] | Parallel runtime default | Decision 0010 |
| [ ] | Ready-queue executor | Decision 0011 |
| [ ] | Node state transitions + metrics hooks | ARCH §5.6 |
| [ ] | Tests: parallel width ≥ 2 | Decision 0004 |

Remaining human OQs: OQ-0008 thought experiment, OQ-0009 repair LCA, OQ-0012 benchmarks (deferred).
