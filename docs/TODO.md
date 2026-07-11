# TODO — Master Backlog (atg-framework)

**Purpose:** Ordered next steps and phase gates.  
**Not for:** Long-form design (→ [`ARCHITECTURE.md`](ARCHITECTURE.md)), binding choices (→ [`DECISIONS.md`](DECISIONS.md)), parked questions (→ [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md)).

**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked (see OQ)

---

## Current focus

1. **All Phase-1 P0 OQs closed.** Optional next interactive: OQ-0007 (ready-queue, P1) or start Phase 1 code.  
2. Implement Phase 1 skeleton: `src/atg` (0008) + graph (0005) + types (0006) + tools (0007) + history (0009) + tests.  

**Recently closed:** … OQ-0002→0009; OQ-0006→**0010**.

---

## Session checkpoint — resume here (2026-07-11)

**State:** Design/docs phase complete for MVP P0 decisions. **No application code yet** (`src/atg/` not created). Working tree at this checkpoint is documentation + process only.

### Done this session

| Area | Outcome |
|------|---------|
| Paper credit | `CITATION.cff`, `docs/citations.bib`, `docs/ATTRIBUTION.md`, README citation, `/attribution` skill |
| Master design | `docs/ARCHITECTURE.md` (goals, paper map, outdated model stack, package design, phases) |
| ADR log | `docs/DECISIONS.md` **0001–0010** Accepted; index `docs/adr/README.md` |
| Open questions | `docs/OPEN_QUESTIONS.md` — P0s promoted; remaining are P1+ |
| Backlog | This file restructured to phase gates + OQ/ADR refs |
| Agent guide | `AGENTS.md` |

### Binding decisions to implement next (do not re-litigate without superseding ADR)

| ID | Summary |
|----|---------|
| 0005 | Stdlib-only graph (no NetworkX in core) |
| 0006 | Pydantic v2 public node/result models |
| 0007 | OpenAI-style tool schema + same-name callable; abstract non-atomic; depth 6; `refine=False`; literals+`$ref` |
| 0008 | `src/atg/`, uv + pyproject, optional extras |
| 0009 | Full graph snapshots for history |
| 0010 | Pluggable parallel runner; ThreadPoolExecutor default |

Also: 0001 docs system, 0002 custom core (not LangGraph-first), 0003 model-agnostic LLM, 0004 synthetic MVP not paper benchmarks.

### Next session — recommended order

1. Read `AGENTS.md` + `docs/ARCHITECTURE.md` §5 + Decisions **0005–0010**.  
2. **Code Phase 1 gate:** `pytest` green without LLM:  
   - `pyproject.toml` + `src/atg/` skeleton (0008)  
   - `types` (0006) + `graph` (0005) + `history` (0009) + `tools` (0007) + `validation`  
   - unit tests: topo, cycle, freeze, snapshot, tool registry  
3. Optional chat OQ before Phase 2: **OQ-0007** (ready-queue vs static levels).  
4. Process: keep asking remaining OQs **in chat** (user preference); promote answers to ADR.

### Still open (not blocking Phase 1 skeleton)

P1: OQ-0005 planner structured output · OQ-0007 ready-queue · OQ-0008 thought experiment · OQ-0009 repair LCA  
P2+: license, adapters, persistence, example model tags, paper benchmarks  

### How agents should resume

```
1. git pull
2. Read AGENTS.md, docs/TODO.md (this checkpoint), docs/DECISIONS.md (0005–0010)
3. Start Phase 1 code unless user asks for more OQ Q&A
```

---

## Phase 0 — Documentation & process

| Done | Item | Refs |
|------|------|------|
| [x] | Master architecture / design doc | `ARCHITECTURE.md` |
| [x] | ADR log + index with rejected alternatives | `DECISIONS.md`, `adr/README.md`, Decisions 0001–0007 |
| [x] | Central open questions log | `OPEN_QUESTIONS.md` |
| [x] | Attribution for Zhang et al. (2026) | `ATTRIBUTION.md`, `CITATION.cff` |
| [x] | README points at doc system | README |
| [x] | AGENTS.md one-pager for agents | root |

---

## Phase 1 — Foundations (MVP critical path)

**Gate:** `pytest` green; DAG create/topo/cycle/freeze without LLM.

| Done | Item | Refs |
|------|------|------|
| [x] | Decide packaging layout | **Decision 0008** (was OQ-0010): `src/atg`, uv, extras |
| [x] | Decide graph representation | **Decision 0005** (was OQ-0001) |
| [x] | Modeling standard for node/result types | **Decision 0006** (was OQ-0003; fields may evolve in PRs) |
| [x] | Tool registry / atomic definition | **Decision 0007** (was OQ-0004) |
| [ ] | `pyproject.toml` + `src/atg` package skeleton | Decision 0008 |
| [ ] | `atg.types` + `atg.graph` (DAG ops, freeze marks) | ARCH §5.1–5.2 |
| [ ] | `atg.history` full snapshot list | **Decision 0009** |
| [ ] | `atg.validation` acyclicity + basic interface checks | ARCH §5.5 |
| [ ] | Unit tests for graph/history/validation | ARCH §3.3 |
| [ ] | Package `__init__` attribution blurb | `ATTRIBUTION.md` |

---

## Phase 2 — Executor

**Gate:** Independent mock tools run concurrently; dependent tools respect order.

| Done | Item | Refs |
|------|------|------|
| [x] | Choose parallel runtime default | **Decision 0010** (was OQ-0006): pluggable, threads default |
| [ ] | Ready-queue executor | [OQ-0007](OPEN_QUESTIONS.md#oq-0007-ready-queue-vs-static-topo-only), paper §4.2 |
| [ ] | Node state transitions + metrics hooks | ARCH §5.6 |
| [ ] | Tests: parallel width ≥ 2; order constraints | Decision 0004 |

---

## Phase 3 — Planner

**Gate:** Multi-level compile from mock structured LLM; interface preservation held.

| Done | Item | Refs |
|------|------|------|
| [ ] | `LLMClient` protocol + mock | Decision 0003 |
| [ ] | Recursive compile loop + history snapshots | paper §4.1, OQ-0002 |
| [ ] | Structured decomposition path | [OQ-0005](OPEN_QUESTIONS.md#oq-0005-decomposition--structured-output-strategy) |
| [ ] | Fixture-based planner tests (no network) | ARCH §5.5 |

---

## Phase 4 — Thought experiment & repair

**Gate:** Injected failure repairs subgraph; frozen successful nodes not re-executed.

| Done | Item | Refs |
|------|------|------|
| [ ] | Structural thought/pre-check | [OQ-0008](OPEN_QUESTIONS.md#oq-0008-failure-detection--thought-experiment) |
| [ ] | Failure localization + minimal repair | [OQ-0009](OPEN_QUESTIONS.md#oq-0009-repair-localization-algorithm), paper §4.3 |
| [ ] | Freeze validated regions | Decision 0004 metrics story |
| [ ] | Failure-injection tests | ARCH §3.3 |

---

## Phase 5 — Real LLM path & examples

**Gate:** Documented example runs with Ollama/LiteLLM via env model.

| Done | Item | Refs |
|------|------|------|
| [ ] | LiteLLM-backed `LLMClient` | Decision 0003 |
| [ ] | Example: multi-step toy task with ≥1 parallel branch | ARCH §3.3 |
| [ ] | Example model via `ATG_MODEL` | [OQ-0015](OPEN_QUESTIONS.md#oq-0015-default-example-model-tags) |
| [ ] | Optional `@pytest.mark.integration` | ARCH §5.5 |

---

## Phase 6 — Integrations & polish

**Gate:** Optional extras; CI; clear contrib docs.

| Done | Item | Refs |
|------|------|------|
| [ ] | Metrics export (steps, repairs, frozen reuse) | paper-aligned metrics |
| [ ] | DSPy / LangGraph thin adapters | [OQ-0013](OPEN_QUESTIONS.md#oq-0013-dspy--langgraph-adapter-depth), Decision 0002 |
| [ ] | Persistence checkpoint (if needed) | [OQ-0014](OPEN_QUESTIONS.md#oq-0014-persistence--memory-backend) |
| [ ] | License file | [OQ-0011](OPEN_QUESTIONS.md#oq-0011-license) |
| [ ] | CI: pytest on PR | — |
| [ ] | Optional paper env adapters | [OQ-0012](OPEN_QUESTIONS.md#oq-0012-paper-benchmark-adapters), Decision 0004 |

---

## Suggested PR sequence

See also `ARCHITECTURE.md` §7.

1. docs: architecture + ADR + OQ + TODO (this set)  
2. feat: package skeleton + graph core + tests  
3. feat: executor ready-queue + parallel mocks  
4. feat: planner mock compile + history  
5. feat: thought + repair + freeze tests  
6. feat: LiteLLM path + example  
7. chore: packaging extras, CI, license  

---

## Notes for agents

- Prefer resolving or explicitly parking (**OQ**) over inventing silent architecture.  
- Rejected design paths live in **DECISIONS.md** — do not re-propose without new evidence and a superseding ADR.  
- Credit Zhang et al. (2026) on paper-derived modules (`/attribution`).  
- Catalog: [local-llm-dev-tools](https://github.com/themark-net/local-llm-dev-tools) (external analysis; not required to build).
