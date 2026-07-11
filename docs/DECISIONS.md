# Architecture Decision Resource (ADR) Log — atg-framework

**Purpose:** Durable record of architecture choices: what we chose, why, what we rejected, and what that forbids or requires later.  
**Process:** Prefer the project ADR skill (`/adr`). Do not re-litigate Accepted decisions without a superseding entry.  
**Index:** [`docs/adr/README.md`](adr/README.md)  
**Related:** [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) · [`docs/OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) · [`docs/TODO.md`](TODO.md)

**Status values:** `Proposed` | `Accepted` | `Rejected` | `Superseded by NNNN`

---

## Decision 0001: Documentation system layout (2026-07-11)

**Status:** Accepted

**Context:** Greenfield public repo. Need a way for humans and agents to share goals, park questions, and record pivots without losing rejected alternatives. User requested: master design doc, ADR log with rejected paths, central TODO, and open questions that can live near code/docs context.

**Decision:**

| Artifact | Path | Role |
|----------|------|------|
| Master design / architecture | `docs/ARCHITECTURE.md` | Goals, paper map, outdated-tech notes, target design, phases |
| ADR log (single file) | `docs/DECISIONS.md` | Binding decisions + rejected alternatives |
| ADR index | `docs/adr/README.md` | Table of decision IDs |
| Open questions | `docs/OPEN_QUESTIONS.md` | Central OQ index + detail; optional `docs/open-questions/OQ-*.md` later |
| Master backlog | `docs/TODO.md` | Next steps only; references OQ/ADR IDs |
| Attribution | `docs/ATTRIBUTION.md` | Paper credit rules |

Contextual open questions may also be noted in module docs or code with `OQ-NNNN` IDs that **must** appear in the central log.

**Rationale:** Matches proven layout in sibling projects (e.g. gom-jobbar). Single-file ADR is enough until decision count is large. Separating TODO from OQ prevents the backlog from becoming an unstructured parking lot.

Rejected alternatives:

1. **TODO-only tracking** — loses rejected alternatives and decision rationale; agents re-propose dead ends.  
2. **Multi-file ADR only from day one** — extra ceremony for a skeleton repo.  
3. **Design doc without OQ log** — multithreaded agent work loses parked questions.

**Consequences:**

- Agents must read ARCHITECTURE + OPEN_QUESTIONS before multi-step implementation.  
- Architectural answers promote OQ → ADR (status `promoted-to-adr`).  
- Do not create a second parallel decision store.

**References:** `docs/ARCHITECTURE.md` §8–10; open-questions + adr skills.

---

## Decision 0002: Custom ATG core; frameworks as adapters (2026-07-11)

**Status:** Accepted

**Context:** Need an execution substrate that supports refinement history, interface-preserving compile, ready-queue parallel execution, and minimal subgraph repair. LangGraph and DSPy are attractive ecosystems but encode different graph/prompt abstractions.

**Decision:** Implement a **small custom core** (`atg.graph`, planner, executor, repair, history) that mirrors ATG semantics. Integrate **LangGraph** and **DSPy** only as optional adapters under `atg.integrations` / extras.

**Rationale:** Paper’s graph is an **executable dependency + evolution** substrate, not only a search tree or prompt pipeline. Keeping core independent maximizes testability and fidelity to Zhang et al. (2026).

Rejected alternatives:

1. **LangGraph-first core** — faster demo; risk of warping refinement history and freeze/repair into StateGraph patterns that don’t fit LCA repair.  
2. **DSPy-first core** — excellent for signatures; weak as general tool-DAG runtime.  
3. **NetworkX-as-public-API** — fine as internal helper later; coupling public types to NetworkX is unnecessary (resolved by Decision 0005: no NetworkX in core).

**Consequences:**

- Core packages must not import LangGraph/DSPy.  
- Adapters may translate ATG ↔ foreign graphs.  
- Graph storage/algorithms: Decision 0005 (stdlib-only core).

**References:** `docs/ARCHITECTURE.md` §5–6; Decision 0005; paper §4.

---

## Decision 0003: Model-agnostic LLM port; no paper model pins in core (2026-07-11)

**Status:** Accepted

**Context:** Paper evaluates Mistral-7B-Instruct-v0.2, Gemma-1.1-7B-it, Llama-3-8B-Instruct, plus GPT-3.5/4. Those IDs age quickly and must not become library constants.

**Decision:** Define an `LLMClient` protocol; default implementation via **LiteLLM** (Ollama/OpenAI-compatible/etc.). Example configs may recommend modern model tags; **core never requires** a specific checkpoint. Paper model names live only in docs §4 (modernization) and optional benchmark notes.

**Rationale:** Recreate **control benefits**, not 2024–early-era checkpoints. Local-first users already have heterogeneous Ollama tags.

Rejected alternatives:

1. **Hard-code paper model IDs** — bitrot; fails on user machines.  
2. **Vendor SDK only (OpenAI/Anthropic/…)** — poor local UX.  
3. **No LLM abstraction (call litellm everywhere)** — harder to mock in unit tests.

**Consequences:**

- Tests use mock `LLMClient`.  
- Integration tests optional with env model name.  
- Update ARCHITECTURE §4 when recommending new example defaults.

**References:** `docs/ARCHITECTURE.md` §4.1, §5.4; OQ-0008.

---

## Decision 0004: MVP scope — synthetic tools and mocks; paper benchmarks deferred (2026-07-11)

**Status:** Accepted

**Context:** Paper proves ATG on ALFWorld, WebShop, ScienceWorld. Those envs are heavy and orthogonal to shipping a usable control library.

**Decision:** MVP success = synthetic multi-tool DAGs + mock/real LLM path + tests for parallel execution and localized repair. Full paper benchmark harnesses are **Phase 3+ / optional**, not MVP gates.

**Rationale:** Fastest path to verifying the three ATG benefits under pytest; avoids env rot blocking core design.

Rejected alternatives:

1. **Benchmark-first** — months of harness before graph freeze/repair is solid.  
2. **No real LLM until benchmarks** — misses local-LLM integration goal; allow optional e2e without making it the gate.

**Consequences:**

- TODO Phase 1–2 never blocked on ALFWorld installs.  
- Metrics should still **align conceptually** with paper (success, steps, repair savings).  
- OQ-0012 tracks optional benchmark work.

**References:** `docs/ARCHITECTURE.md` §3.2–3.3, §7; OQ-0012.

---

## Decision 0005: Stdlib-only graph core (no NetworkX in core) (2026-07-11)

**Status:** Accepted  
**Promotes:** OQ-0001  
**Deciders:** Maintainer accepted agent recommendation (limited graph-library domain knowledge at decision time—see revisit triggers).

**Context:** Phase 1 needs DAG operations: topological order, cycle detection, predecessors/successors, ready-set, subgraph extract, freeze marks. Options were stdlib-only structures, NetworkX as internal engine, or hybrid with optional `[viz]`. Decision 0002 already forbids NetworkX as the *public* API identity. OQ-0001 recommended stdlib-only for MVP.

**Decision:** Implement `TaskGraph` and related algorithms with **stdlib-only** data structures (e.g. `dict` adjacency, explicit edge lists, BFS/DFS/Kahn topo). **Do not** add NetworkX (or equivalent graph frameworks) as a core runtime dependency. Optional visualization may later live behind an extra that *exports* our graph—never the reverse (our types wrapping NetworkX as source of truth).

**Rationale:**

- MVP graphs are small (tens to low hundreds of nodes); classic topo/cycle algorithms are trivial in pure Python.
- Zero heavy graph dependency keeps install light and testing simple (Decision 0002 spirit).
- Full ownership of freeze/history-friendly mutations without fighting an external graph object model.
- **Domain-knowledge caveat (explicit):** The maintainer accepted this recommendation **without deep comparative experience** of NetworkX vs custom DAGs in production agent systems. That is a valid reason to **revisit**, not a permanent religious ban. The choice optimizes for simplicity and testability under current evidence, not proven superiority at large scale.

Rejected alternatives:

1. **NetworkX internal as source of truth** — richer algorithms/viz out of the box; cost: dependency, version surface, impedance with freeze/snapshot/clone semantics, harder minimal public types.  
2. **Hybrid now (stdlib + NetworkX `[viz]` coupled early)** — premature; export adapters can be added when a real viz need appears without coupling core.  
3. **Delay choosing** — blocks Phase 1 code; no benefit once MVP graph size is known-small.

**Consequences:**

- Required: pure-Python `atg.graph` (+ tests for topo, cycles, ready-set, subgraph).  
- Forbidden in core: `import networkx` (or similar) as graph store.  
- Allowed later: optional extra that *renders* or *analyzes* an exported snapshot; must not redefine node identity.  
- OQ-0001 → `promoted-to-adr`.

**Revisit / supersede when (any one is enough):**

1. Domain expert or production profiling shows custom graph ops are a real bottleneck or correctness liability.  
2. We need algorithms we do not want to maintain (e.g. complex flow/cut, advanced layout) **inside** core rather than export-and-analyze.  
3. A visualization or notebook workflow becomes first-class and repeatedly reimplements NetworkX conversion.  
4. Graph sizes routinely exceed what simple Python structures handle comfortably in tests or demos.

On revisit: open a new OQ or superseding ADR; do not silently add NetworkX.

**References:** OQ-0001; Decision 0002; `docs/ARCHITECTURE.md` §5.1; planned `atg/graph.py`.

---

## Decision 0006: Pydantic v2 for public node/result models (2026-07-11)

**Status:** Accepted  
**Promotes:** OQ-0003  
**Deciders:** Maintainer accepted agent recommendation (limited preference between dataclass vs Pydantic stacks at decision time—see revisit triggers).

**Context:** Need stable types for `TaskNode`, graph payloads, input/output bindings (“output of A.field → input of B”), status enums, and soon structured LLM decomposition (OQ-0005). Greenfield repo has **no** pre-existing type stack. OQ-0003 options: dataclasses+dicts, Pydantic v2, TypedDict-only. Conditional recommendation was “Pydantic if structured LLM output is in play; else dataclasses.” Structured output **is** on the critical path for the planner (Phase 3), so the conditional resolves to **Pydantic**.

**Decision:**

1. Public core models (`TaskNode`, graph serializable views, status enums as appropriate, tool I/O payload shapes used at boundaries) use **Pydantic v2** (`BaseModel` / constrained types).  
2. Graph **topology** remains owned by Decision 0005 structures; Pydantic models describe **node payloads and serializable graph DTOs**, not a third-party graph library.  
3. Prefer one representation: avoid parallel “dataclass TaskNode + Pydantic TaskNodeSchema” unless a measured need appears.  
4. Exact field list may still evolve in implementation PRs, but **Pydantic is the modeling standard**—field changes are code reviews, not a new OQ, unless the standard itself is overturned.

**Rationale:**

- Planner needs JSON-schema-friendly structured output; Pydantic generates schemas and validates round-trips.  
- Single stack reduces dual-mapping bugs between runtime objects and LLM JSON.  
- Validation ergonomics for status transitions and required fields beat ad-hoc validators on plain dicts.  
- **Domain-knowledge caveat:** Maintainer did not bring a strong prior (“we always use dataclasses in libs”). Choice follows agent recommendation + planned LLM boundary needs. Revisit is appropriate if dependency policy or runtime constraints change.

Rejected alternatives:

1. **Stdlib dataclasses + plain dicts only** — lightest deps; cost: hand-rolled validation and a second schema layer when structured LLM output lands (duplicate types).  
2. **TypedDict-only** — poor runtime validation; weak for evolving node status/invariants.  
3. **Split now (dataclass graph + Pydantic only at LLM edge)** — valid purity play; rejected for MVP to avoid two node shapes and copy bugs; can be revisited if core must be zero-dep.

**Consequences:**

- Core may depend on `pydantic>=2`.  
- `atg.types` (or equivalent) is the home for models; graph algorithms stay dependency-light per Decision 0005 (Pydantic is allowed for node values).  
- Tests should include model validation cases, not only graph algorithms.  
- OQ-0003 → `promoted-to-adr`. OQ-0002 unblocked on “types exist” axis (history still open). OQ-0004 still open but no longer blocked on “dataclass vs Pydantic.”

**Revisit / supersede when:**

1. Policy requires **zero** non-stdlib core deps (embed/vendoring constraints).  
2. Pydantic major churn or binary size becomes a real problem for target users.  
3. Profiling shows model validation cost material on large graphs.  
4. We adopt a different structured-output stack that wants its own types exclusively (then document split boundary in a superseding ADR).

**References:** OQ-0003; OQ-0005; Decision 0003 (LLM port); `docs/ARCHITECTURE.md` §5.2.

---

## Decision 0007: Tools, atomicity, and compile stop (OpenAI-style + callable) (2026-07-11)

**Status:** Accepted  
**Promotes:** OQ-0004  
**Deciders:** Maintainer, via interactive Q&A. Preferred standardized **OpenAI-style tool JSON schemas**; accepted agent package for remaining pieces given limited domain knowledge. Explicitly chose **E1** (`refine=False`) and **F4** (literals + `$ref`).

**Context:** Need engineering contracts for: what a tool is, when recursive compilation stops, how non-atomic nodes look, how outputs flow between nodes, and whether multi-step black boxes can be forced atomic. Paper defines tools as atomic I/O units and compilation as refining until every node is atomic, but does not specify registry APIs. Maintainer asked how “OpenAI-style schemas” diverge from a “separate registry,” and what “side effects” means.

**Decision:**

| Topic | Choice |
|-------|--------|
| **Tool definition** | **OpenAI-style JSON schema surface** (`name`, `description`, `parameters` JSON Schema) **plus** a **same-name Python callable** used at execution. Schema is for planning/LLM; callable is for running. Not schemas-only. |
| **Registry** | One registry entry per tool binds schema metadata + callable (+ optional flags). Names are unique. |
| **Atomic node** | A node is atomic (compile must not refine it further) if: (1) its `tool_name` is registered as executable, **or** (2) `refine=False` / forced-atomic is set on the node or tool. |
| **Non-atomic node** | Abstract subtask: human/LLM-facing name + desired external I/O interface, **no** executable registry tool (or not yet bound). Planner replaces it with a subgraph that **preserves** that interface (paper §4.1). |
| **Max refine depth** | Default **6**; overridable per run/config. Hitting the cap is an error or forced stop with diagnostics (implementation detail in planner PR). |
| **Forced atomic (E1)** | Tools or nodes may set **`refine=False`** so compilation never explodes a black-box multi-step helper. |
| **Input binding (F4)** | Node inputs may be **literals** or **`$ref`** (or equivalent) to upstream `node_id.outputs.field`. |
| **Side effects** | **Allowed** if the user registered the tool. MVP does not require purity. Optional `side_effect` (or category) annotation may be added later for thought-experiment / scheduling—not required to register. “Side effect” = the tool changes or depends on the outside world (HTTP, disk, DB, browser, robot…) rather than being a pure function of its args. |
| **Nested ATG** | **Not in MVP** (a tool should not be required to spawn a full inner ATG; may revisit later). |

**Rationale:**

- **Why OpenAI-style schemas:** Widely known format for tool calling; good for LLM planners and future interoperability. Matches maintainer preference for standardized shapes.  
- **Why still a callable (not schema-only):** A JSON schema describes *shape*; it cannot execute. At runtime the executor must invoke Python (or a bound client). Binding **same name → callable** is the usual pattern behind every “OpenAI tools” demo.  
- **Why not “registry instead of OpenAI”:** False opposition. The registry **stores** OpenAI-style specs **and** callables. Divergence in practice:  
  - *Schemas only* → can plan, cannot run.  
  - *Callables only* → can run, weaker LLM tool lists.  
  - *Both (this decision)* → plan + run.  
- **Abstract non-atomic nodes** match paper recursive compilation.  
- **`refine=False`** covers real systems (legacy agents, fat tools).  
- **Literals + `$ref`** is explicit and testable (F4).  
- **Domain-knowledge caveat:** Several sub-options were accepted as a package after explanation because the maintainer lacked comparative production experience. Revisit triggers below are intentional.

Rejected alternatives:

1. **Schemas-only tools until later** — blocks real executor; deferred wiring creates two migration steps.  
2. **Callable-only / non-OpenAI registry** — fine technically; rejected for weaker alignment with common LLM tool formats.  
3. **R2 pure-only MVP** — unnecessary friction for agent demos (weather, HTTP, etc.).  
4. **No `refine=False`** — forces dishonest “atomic” decompositions of black boxes.  
5. **Name-based auto-wire only** — fragile; harder to test than `$ref`.  
6. **Nested ATG in MVP** — scope creep before single-level compile/execute/repair works.

**Consequences:**

- Implement `ToolRegistry` (name → schema + callable + flags) and document OpenAI-shaped export for prompts.  
- Planner stop condition uses atomic rules above + depth cap.  
- Executor resolves `$ref` after upstream `done`/`frozen`.  
- OQ-0004 → `promoted-to-adr`. OQ-0005 can assume tool list = OpenAI-style from registry.  
- Tests: register mock tools with parameters schema; abstract node refine; `refine=False` not expanded; `$ref` binding.

**Revisit / supersede when:**

1. We need MCP / other tool protocol as primary instead of OpenAI-shaped JSON.  
2. Depth 6 is systematically too low/high in real tasks.  
3. Side-effect categories become necessary for safe parallel scheduling (pair with OQ-0008).  
4. Nested ATG becomes a real product requirement.  
5. Domain experience shows abstract-node representation should use synthetic `plan:` tool names instead.

**References:** OQ-0004; Decisions 0002, 0006; paper Def. 2–3, §4.1; `docs/ARCHITECTURE.md` §5; interactive session 2026-07-11.

---

## Decision 0008: Packaging — src layout, uv, optional extras (2026-07-11)

**Status:** Accepted  
**Promotes:** OQ-0010  
**Deciders:** Maintainer via interactive Q&A: **A1** `src/atg/`, **B1** `pyproject.toml` + uv, **C1** optional extras.

**Context:** Phase 1 needs an installable package layout and dependency workflow before code lands. Options: src vs flat layout; uv vs pip-only vs Poetry; extras vs single fat install.

**Decision:**

| Topic | Choice |
|-------|--------|
| **Layout** | **`src/atg/`** (src layout). Tests under `tests/`; examples under `examples/`. |
| **Build / install** | **`pyproject.toml`** as source of truth; **uv** for lock/sync/dev workflow (`uv sync`, `uv run pytest`). pip-compatible (`pip install -e .`) remains possible via standard packaging metadata. |
| **Extras** | **Yes** — optional groups so core stays small. Initial intent (names may refine in implementation): `[llm]` (e.g. LiteLLM), `[viz]` (export/render helpers if any), `[integrations]` (DSPy/LangGraph adapters), `[dev]` (pytest, ruff, etc.). Core includes what MVP graph/types/tools need (e.g. pydantic per Decision 0006). |

**Rationale:**

- **src layout** avoids accidental import of an uninstalled tree and matches common modern library practice.  
- **uv + pyproject** is fast and standardizing in 2026-era Python tooling; still interoperable with pip.  
- **Extras** keep a minimal core for users who only need graph/execute mocks without full LLM stack.

Rejected alternatives:

1. **Flat `atg/` at repo root** — simpler paths; easier to shadow installs during messy PYTHONPATH use.  
2. **pip-only, no uv** — valid minimalism; slower/less ergonomic lock story for this maintainer preference.  
3. **Poetry** — fine ecosystem; unnecessary second tool given uv choice.  
4. **Single fat install for MVP** — simpler first PR; pays cost later when local-only users pull integration deps.

**Consequences:**

- First code PR should add `pyproject.toml`, `src/atg/`, and document `uv sync` in README.  
- CI should use uv or equivalent install from pyproject.  
- OQ-0010 → `promoted-to-adr`. Phase 1 packaging row unblocked.

**Revisit / supersede when:**

1. Contributors cannot use uv and need first-class poetry/conda docs.  
2. Extra boundaries prove wrong (merge/split groups).  
3. Build backend choice (hatchling vs setuptools) needs a dedicated ADR if non-default.

**References:** OQ-0010; Decisions 0002, 0003, 0006; `docs/TODO.md` Phase 1; interactive session 2026-07-11.

---

## Decision 0009: Graph history as full snapshots (2026-07-11)

**Status:** Accepted  
**Promotes:** OQ-0002  
**Deciders:** Maintainer via interactive Q&A — option **1** full snapshots each step (recommended).

**Context:** Paper records intermediate graphs during recursive compilation so failures can be localized via refinement history (LCA-style repair). Engineering choice: full copies vs event log vs hybrid.

**Decision:** After each meaningful compile refine step and each repair that changes the graph, append an **immutable full snapshot** of the `TaskGraph` (plus metadata: version, reason, timestamp). History is an ordered list of snapshots. Event-sourced history is **out of scope** for MVP.

**Rationale:** Snapshots are easy to test, debug, and serialize; MVP graphs are small (Decision 0005 context). Event logs optimize memory at the cost of complexity we do not need yet.

Rejected alternatives:

1. **Event log only** — leaner; harder correctness and debugging.  
2. **Hybrid snapshots + events** — premature optimization.  
3. **No history until repair phase** — blocks faithful §4.3 design and early tests of lineage/`parent_id`.

**Consequences:**

- Implement `GraphHistory` / `GraphSnapshot` with deep-copy or Pydantic-model_copy semantics.  
- Repair (OQ-0009) will walk snapshot lineage + node `parent_id`.  
- Monitor memory only if graphs grow large → revisit.  
- OQ-0002 → `promoted-to-adr`.

**Revisit / supersede when:** snapshot memory/CPU becomes material; or we need audit compression for long-running agents.

**References:** OQ-0002; OQ-0009; paper §4.1, §4.3; Decisions 0005–0006; interactive session 2026-07-11.

---

## Decision 0010: Pluggable parallel runner; threads default (2026-07-11)

**Status:** Accepted  
**Promotes:** OQ-0006  
**Deciders:** Maintainer via interactive Q&A — accept recommendation **(3)** pluggable + thread default.

**Context:** Independent DAG nodes should run concurrently (paper §4.2). Choices: threads only, asyncio-first, or pluggable with a default.

**Decision:**

1. Define a small **`ParallelRunner` / executor-port** interface (submit callables or node jobs; wait for completion; respect cancellation later if needed).  
2. **Default implementation:** `concurrent.futures.ThreadPoolExecutor` (sync tools + I/O-bound LLM/HTTP).  
3. **Asyncio backend** may be added later behind the same interface without rewriting graph scheduling logic.  
4. Core ready-queue scheduler (see OQ-0007) is independent of the runner: it decides *what* is ready; the runner decides *how* concurrent ready work runs.

**Rationale:** Threads are the lowest-friction MVP for mixed sync tools. A port avoids painting into a corner if the project goes async-heavy.

Rejected alternatives:

1. **Threads only, no interface** — fastest first PR; harder to swap later.  
2. **Async-first core** — forces async wrappers on every sync tool early.  
3. **Process pool default** — overkill for LLM I/O; worse pickling story for tools.

**Consequences:**

- Executor module depends on runner protocol; tests can inject a sequential or fake runner.  
- Document that default thread runner requires tools to be safe under concurrent calls if they share state.  
- OQ-0006 → `promoted-to-adr`. Phase 2 unblocked on runtime choice.

**Revisit / supersede when:** most tools are async-native; or thread safety issues dominate; or a process-pool isolation need appears.

**References:** OQ-0006; OQ-0007; paper §4.2; interactive session 2026-07-11.

---

## How to add a decision

1. Assign next ID (`NNNN` = max + 1, never reuse).  
2. Append a full section using the template below (include **rejected alternatives**).  
3. Add a row to `docs/adr/README.md`.  
4. If it changes layering, update `docs/ARCHITECTURE.md` in the same change.  
5. If it answers an OQ, set that OQ to `promoted-to-adr` and link both ways.

```markdown
## Decision NNNN: Short Title (YYYY-MM-DD)

**Status:** Proposed | Accepted | Rejected | Superseded by NNNN

**Context:** …

**Decision:** …

**Rationale:** …
Rejected alternatives:
1. …
2. …

**Consequences:** …

**References:** OQ-…, paths, architecture sections
```
