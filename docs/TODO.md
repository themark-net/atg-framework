# TODO — Master Backlog (atg-framework)

**Purpose:** Ordered next steps and phase gates.  
**Not for:** Long-form design (→ [`ARCHITECTURE.md`](ARCHITECTURE.md)), binding choices (→ [`DECISIONS.md`](DECISIONS.md)), parked questions (→ [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md)).

**Status legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked (see OQ)

---

## Current focus

1. MVP loop is in `src/atg/`. On 2026-10-06, `uv run pytest -q -m "not integration"` → 40 passed, 1 deselected.  
2. Offline demo: `uv run python examples/toy_parallel.py`. How to use the library, by skill level, is [`NEXT.md`](NEXT.md) and [`USING.md`](USING.md).  
3. Live 14B remeasure is done. Decision 0023 sets `DEFAULT_MODEL` to `qwen2.5:14b`. Decision 0017 records the 2026-10-05 failures and is superseded.  
4. The software license is MIT (Decision 0019). The 2026-10-05 gap check is Decision 0020. Decisions 0021–0024 cover the OpenAI client, toy PoC metrics, the 14B default, and short `$ref` compile errors.  
5. **OQ-0016** is open: whether a second failure of the same repair region should widen to the parent. Decision 0014 does not widen. The 2026-10-06 live runs did not show that double failure. The Cursor branch’s `escalate_after` was not merged.  
6. **OQ-0017** is open: the next live comparison among Ollama, the home vLLM environment, and Lemonade. Decision 0023 stays the default until a new measurement and a decision.  
7. pfy-mentat #279 is merged at catalog stage I2. Publishing on X is still [`ops/x-publishing-handoff.md`](ops/x-publishing-handoff.md). Do not post from this backlog.

**Recently closed:** OQ-0011→0019. Earlier: OQ-0005→0012, OQ-0008→0013, OQ-0009→0014, OQ-0013→0016, OQ-0014→0015, OQ-0015→0017. OQ-0012 → wont-do (Decision 0018). OQ-0007→0011.

---

## Session checkpoint — resume here (2026-10-06)

**State:** `main` holds Decisions 0021–0024. Default model is `qwen2.5:14b`. Offline PoC and `docs/poc/RESULTS.md` are in tree. pfy-mentat #279 is merged at I2. OQ-0016 and OQ-0017 stay open. Do not post on X.

### Next session

1. Review and merge only through Tester and Reviewer.
2. Leave `qwen3-coder-next` unloaded until MemAvailable covers 48.19 GiB + 25 GiB.
3. If a live repair of the same region fails twice, write that on OQ-0016 and stop for a decision.

## Session checkpoint — resume here (2026-10-05)

**State:** Phases 1–6 are in tree. Decisions **0012–0020** are accepted. `uv run pytest -m "not integration"` is green. OQ-0016 (repair escalation) is the remaining open question.

### Done this session

| Area | Outcome |
|------|---------|
| Runtime | Planner, executor, structural thought, localized repair, JSON history, one-way adapters |
| Decisions | 0012–0020. License is MIT |
| Live | Three local tags failed (Decision 0017 measurement). Parent-id edges are dropped. A 14B retry was cancelled while `gpt-oss:120b` was loading |
| Docs | [`USING.md`](USING.md) (skill levels and nimo-class use), [`NEXT.md`](NEXT.md), pfy and X handoffs under `docs/ops/` |

### Next session

Follow [`NEXT.md`](NEXT.md).

1. When `ollama ps` is empty, run `uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only`.  
2. If that exits 0 with parallel ≥ 2 and sink value 25, supersede Decision 0017 and set `DEFAULT_MODEL` to `qwen2.5:14b`.  
3. Do not load a model for the Decision 0017 remeasure while another bench holds Ollama.  
4. pfy-mentat and X publishing wait for a session that is asked to do them. Procedures: `docs/ops/pfy-mentat-handoff.md`, `docs/ops/x-publishing-handoff.md`.

---

## Historical checkpoint — design only (2026-07-11)

Superseded by the checkpoint above. Decisions listed here still bind. **Do not treat “no application code” as current.**

**State at that date:** Design/docs phase complete for MVP P0 decisions. Application code had not been created yet.

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

The July resume list (start Phase 1, discuss OQ-0007) is done. Follow the 2026-10-05 checkpoint.

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
| [x] | `pyproject.toml` + `src/atg` package skeleton | Decision 0008 |
| [x] | `atg.types` + `atg.graph` (DAG ops, freeze marks) | ARCH §5.1–5.2 |
| [x] | `atg.history` full snapshot list | **Decision 0009** |
| [x] | `atg.validation` acyclicity + basic interface checks | ARCH §5.5 |
| [x] | Unit tests for graph/history/validation | ARCH §3.3 |
| [x] | Package `__init__` attribution blurb | `ATTRIBUTION.md` |

---

## Phase 2 — Executor

**Gate:** Independent mock tools run concurrently; dependent tools respect order.

| Done | Item | Refs |
|------|------|------|
| [x] | Choose parallel runtime default | **Decision 0010** (was OQ-0006): pluggable, threads default |
| [x] | Ready-queue executor loop (semantics decided; `ready_ids` exists) | **Decision 0011**, paper §4.2 |
| [x] | Node state transitions + metrics hooks | ARCH §5.6, `atg.metrics` |
| [x] | Tests: parallel width ≥ 2; order constraints | Decision 0004 |

---

## Phase 3 — Planner

**Gate:** Multi-level compile from mock structured LLM; interface preservation held.

| Done | Item | Refs |
|------|------|------|
| [x] | `LLMClient` protocol + mock | Decision 0003, `atg.llm` |
| [x] | Recursive compile loop + history snapshots | paper §4.1, Decision 0009 |
| [x] | Structured decomposition path | **Decision 0012** |
| [x] | Fixture-based planner tests (no network) | ARCH §5.5 |

---

## Phase 4 — Thought experiment & repair

**Gate:** Injected failure repairs subgraph; frozen successful nodes not re-executed.

| Done | Item | Refs |
|------|------|------|
| [x] | Structural thought/pre-check | **Decision 0013** |
| [x] | Failure localization + minimal repair | **Decision 0014**, paper §4.3 |
| [x] | Freeze validated regions | Decision 0004 metrics story |
| [x] | Failure-injection tests | ARCH §3.3 |

---

## Phase 5 — Real LLM path & examples

**Gate:** Documented example runs with Ollama/LiteLLM via env model.

| Done | Item | Refs |
|------|------|------|
| [x] | LiteLLM-backed `LLMClient` (optional extra `[llm]`) plus stdlib `OllamaClient` | Decision 0003, 0017 |
| [x] | Example: multi-step toy task with ≥1 parallel branch | `examples/toy_parallel.py` |
| [x] | Example model via `ATG_MODEL` | **Decision 0017** |
| [x] | Optional `@pytest.mark.integration` | skipped unless `ATG_RUN_INTEGRATION=1` |
| [ ] | Live toy exits 0 on one local instruct tag | Decision 0017 measurement. Re-run when `ollama ps` is empty |

---

## Phase 6 — Integrations & polish

**Gate:** Optional extras; CI; clear contrib docs.

| Done | Item | Refs |
|------|------|------|
| [x] | Metrics export (steps, repairs, frozen reuse) | `atg.metrics.Metrics` |
| [x] | DSPy / LangGraph thin adapters | **Decision 0016** |
| [x] | Persistence checkpoint (JSON) | **Decision 0015** |
| [x] | License file | **Decision 0019** — MIT |
| [x] | CI: pytest on PR | `.github/workflows/pytest.yml` |
| [x] | Paper env adapters stayed deferred | **Decision 0018** |

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
