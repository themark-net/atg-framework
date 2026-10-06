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

## Decision 0011: Dynamic ready-queue and node status (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0007  
**Deciders:** Maintainer authorized non-system-impacting Phase 2 decisions in the 2026-10-05 one-shot. The choice follows Zhang et al. (2026) §4.2, which already matched the parked recommendation.

**Context:** Phase 2 must schedule atomic nodes. OQ-0007 asked whether that schedule is a dynamic ready-queue or a static list of topological levels. Paper §4.2 (Dependency-Aware Execution, `zhang2026atg`) says a node becomes executable when its predecessors have finished and its inputs are resolved, and that several such nodes may run at once. The same subsection says execution records each node’s input, output, status, and error. Decision 0010 already separated “what is ready” from “how concurrent work runs.”

**Decision:**

1. **Ready-queue.** A node is ready when its status is `pending` or `ready` and every predecessor status is `done` or `frozen`. The ready set is recomputed as nodes finish. It is not a level partition computed once before the run.
2. **Parallel wave.** Every currently ready node may be submitted together to the `ParallelRunner` (Decision 0010). When metrics exist, one wave counts as one execution step, matching the paper’s parallel-step accounting. The counter itself is Phase 2.
3. **Status vocabulary and transitions.** Recorded fields are input, output, status, and error. The only legal moves are `pending → ready → running → done → frozen` and `running → failed`. `failed` requires an error string. `frozen` is only reached from `done`.
4. **Failure scope.** A `failed` node blocks its descendants (they stay not ready). Other branches stay eligible. Phase 2 must not cancel the whole graph on the first failure.
5. **Repair reset is out of scope.** There is no `failed → pending` transition. Putting a failed region back to pending belongs to repair (OQ-0009), which will need its own decision if it adds transitions.

`TaskGraph.ready_ids`, `mark_ready`, `transition`, and `freeze` are the Phase 1 contract. The thread-pool loop that calls them is still Phase 2.

**Rationale:** The paper’s readiness rule is event-driven: a node *becomes* executable when predecessors finish. Static levels match that only for a run where nothing fails and the graph never changes. Sibling branches must keep running so validated nodes can later be frozen and reused (§4.3). A fixed transition list keeps `done` and `frozen` meaningful for that reuse.

Rejected alternatives:

1. **Static topological levels only** — simple, but a mid-run failure or a repaired graph invalidates the partition, and the paper describes readiness as something that happens when predecessors finish.  
2. **Fail-fast cancellation of every other node** — discards sibling work the repair stage is meant to keep.  
3. **Free-form status strings** — repair cannot trust which nodes are safe to reuse.

**Consequences:**

- Phase 2 executor loop: `mark_ready`, submit those ids to the runner, transition each result to `done` or `failed`, repeat until no ready node remains.  
- Descendants of `failed` nodes are not ready. Independent nodes still are.  
- Do not add a status or a backward transition without superseding this decision.  
- OQ-0007 → `promoted-to-adr`.

**Revisit / supersede when:** in-flight siblings must be cancelled; the async runner needs a different readiness signal; or repair (OQ-0009) needs a transition this list does not have.

**References:** OQ-0007; Decision 0010; Zhang et al. (2026) §4.2 (`zhang2026atg`); `src/atg/graph.py`; `docs/ARCHITECTURE.md` §5.2–5.3.

---

## Decision 0012: Structured decomposition JSON in core (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0005  
**Deciders:** Maintainer authorized non-privileged open-question decisions in the 2026-10-05 one-shot.

**Context:** The planner has to turn one abstract node into a subgraph. Depth is already 6 (Decision 0007). The open choice was JSON schema, DSPy signatures, or constrained decoding.

**Decision:** `complete_structured` returns a Pydantic `Decomposition` (`nodes`, `edges`). The core prompt asks for that object. DSPy is not on the compile path. Constrained decoding is whatever the model port already does (Ollama `format` is the JSON schema).

**Rationale:** One schema keeps the mock tests and the live model on the same object. The interface check rejects a decomposition that drops a parent `$ref` or a declared sink output, so a fluent but wrong graph does not run.

Rejected alternatives:

1. **DSPy signatures in core** — Decision 0002 keeps DSPy as an adapter.  
2. **Free text plus a best-effort parser** — fails closed less often and is harder to test.  
3. **Tool-call messages as the only compile format** — plausible if schema JSON fails on every local instruct model. That is the revisit trigger, not the default.

**Consequences:**

- `compile_task` snapshots once per depth step.  
- A live failure of `examples/toy_parallel.py --live` on every fallback model reopens the format, not the depth cap.  
- OQ-0005 → `promoted-to-adr`.

**Revisit / supersede when:** the toy live script fails schema validation for `llama3.1:8b`, `qwen2.5:14b`, and `gemma4:latest`, and a tool-call encoding of the same task succeeds.

**References:** OQ-0005; Decisions 0003, 0006, 0007; Zhang et al. (2026) §4.1 (`zhang2026atg`); `src/atg/planner.py`.

---

## Decision 0013: Structural thought experiment, optional judge (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0008  
**Deciders:** Same one-shot authorization as Decision 0012.

**Context:** Paper §4.2 runs a cheap check before environment cost. It lists what to look for (tools, dependencies, interfaces) and does not say a second model must judge the plan.

**Decision:** `structural_thought` always runs: closed-graph validation plus atomicity. `thought_experiment(..., llm)` adds one `JudgeVerdict` call only when the rules already passed. `run_task` passes the LLM only when `judge=True` or `ATG_JUDGE=1`. Tool exceptions stay execution failures.

**Rationale:** Rules are deterministic and cover the failures the paper names as structural. A judge can reject a plan the rules accept. The unit test records that split: rules ok, scripted judge not ok. Paying for a judge on every run is optional.

Rejected alternatives:

1. **Rules only, no judge hook** — cannot compare when a semantic miss shows up.  
2. **Judge on every run** — spends a model call before the deterministic check has failed.  
3. **A second validation framework for tool return values** — overlaps `declared_outputs` and the tool’s own exception.

**Consequences:**

- Default runs do not call the judge.  
- `Metrics.judge_disagreements` is 1 when the judge rejects a rule-clean plan.  
- OQ-0008 → `promoted-to-adr`.

**Revisit / supersede when:** a live task passes structural checks and then fails for a reason other than a tool exception. Re-run that task with `ATG_JUDGE=1` and compare `judge_disagreements` before changing the default.

**References:** OQ-0008; paper §4.2; `src/atg/thought.py`; `tests/test_runtime.py`.

---

## Decision 0014: LCA repair region and a narrow reset (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0009  
**Deciders:** Same one-shot authorization as Decision 0012.

**Context:** Paper §4.3 localizes failed atomic nodes to their lowest common historical ancestor, repairs that region, and freezes the rest. Decision 0011 forbade `failed → pending` until repair had its own decision.

**Decision:**

1. Lineage is `parent_id`, then the same id in older snapshots.  
2. The LCA is the common ancestor closest to the failed nodes. No common ancestor means each failed node is its own seed.  
3. The region is the live nodes under that ancestor plus every downstream node.  
4. `done` nodes outside the region are frozen. Frozen nodes are not replaced and `reset_for_repair` refuses them.  
5. The region is removed and replaced by a new `Decomposition` of the region’s external interface.  
6. `reset_for_repair` may move `done`, `failed`, or `ready` back to `pending` and clear output and error. `transition` still does not allow that move.

**Rationale:** Parent links are already on `TaskNode`. The freeze test is the measurement: a successful sibling’s tool runs once, the failed tool runs again, the sibling status is `frozen`.

Rejected alternatives:

1. **Repair only the failed node and ignore `parent_id`** — misses a bad decomposition that produced several failing siblings. The code already falls back to that when there is no shared ancestor.  
2. **Re-run the whole graph** — throws away frozen work. The paper’s point is not to.  
3. **Allow `failed → pending` on `transition`** — any caller could un-freeze a failure. The reset stays on one method.

**Consequences:**

- `run_task` repairs at most twice, then returns.  
- OQ-0009 → `promoted-to-adr`.

**Revisit / supersede when:** a test that should keep a node frozen shows it inside the region, or the no-common-ancestor union re-executes most of a large graph. Switch that case to “failed node plus descendants” by superseding this decision.

**References:** OQ-0009; Decisions 0009, 0011; paper §4.3; `src/atg/repair.py`.

---

## Decision 0015: JSON checkpoint beside in-memory history (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0014  
**Deciders:** Same one-shot authorization as Decision 0012.

**Context:** Decision 0009 stores full snapshots in a list. OQ-0014 asked what happens after the process exits.

**Decision:** Runtime history stays in memory. `save_history` / `load_history` persist that list as one JSON file. No SQLite and no vector index.

**Rationale:** Snapshots are already Pydantic models. One file round-trips in a unit test. A database adds an operational dependency before a size problem exists.

Rejected alternatives:

1. **SQLite now** — useful once a file is too large to load whole. Not before.  
2. **Vector store for semantic reuse** — no task in this repo asks for similarity search.  
3. **No checkpoint** — a process crash drops the history the repair algorithm needs.

**Consequences:**

- Callers choose the path. The library does not auto-write.  
- OQ-0014 → `promoted-to-adr`.

**Revisit / supersede when:** a checkpoint is too large to load, or a caller has a real similarity-reuse task.

**References:** OQ-0014; Decision 0009; `src/atg/persist.py`.

---

## Decision 0016: One-way DSPy and LangGraph callables (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0013  
**Deciders:** Same one-shot authorization as Decision 0012.

**Context:** Decision 0002 keeps those frameworks out of core. OQ-0013 asked how deep an adapter should be.

**Decision:** `as_langgraph_node` and `as_dspy_forward` are plain callables. They run `run_task` and return a dict. They do not import LangGraph or DSPy and they do not sync checkpoints.

**Rationale:** A callable can be placed in either framework without a dependency in this package. Bidirectional sync is a second product.

Rejected alternatives:

1. **Import LangGraph and DSPy in core** — Decision 0002.  
2. **Bidirectional state sync now** — no caller needs to pause mid-repair.  
3. **No adapter module** — the integration point stays tribal knowledge.

**Consequences:**

- Optional extra `[integrations]` is unnecessary until those libraries are imported from here.  
- OQ-0013 → `promoted-to-adr`.

**Revisit / supersede when:** a caller must pause inside an ATG run and resume from the other framework’s checkpointer.

**References:** OQ-0013; Decision 0002; `src/atg/integrations/`.

---

## Decision 0017: Default local model tag (2026-10-05)

**Status:** Superseded by 0023  
**Promotes:** OQ-0015  
**Deciders:** Same one-shot authorization as Decision 0012. The machine already had Ollama tags installed. No cloud model was called.

**Context:** Examples need a concrete tag. The paper’s Gemma-1.1 / Llama-3 / Mistral-v0.2 pins are outdated (ARCHITECTURE §4). Several local tags exist, including coder models and a cloud tag.

**Decision:** `ATG_MODEL` overrides. The default string is `llama3.1:8b`. If a live compile fails schema or interface checks, try `qwen2.5:14b`, then `gemma4:latest` (the local 8B tag). Do not default to coder-only tags, to tags above about 15B, or to `deepseek-v4-flash:cloud`.

**Rationale:** `llama3.1:8b` is an installed instruct model in the paper’s 7B–8B class. Coder tags are a different job. Larger tags contend with other local eval work. The cloud tag leaves the machine.

Rejected alternatives:

1. **`qwen3.6:35b` or `qwen3-coder:30b` as the default** — stronger, heavier, and not the paper’s size claim.  
2. **A coder model as the default planner** — wrong specialty unless the instruct tags fail the toy and a coder tag passes it.  
3. **Hard-code the tag with no env override** — Decision 0003.

**Consequences:**

- `examples/toy_parallel.py --live` applies the fallback order and prints the tag that worked.  
- OQ-0015 → `promoted-to-adr`.  
- Measurement (2026-10-05, `examples/toy_parallel.py --live`, timeout 180s, GPU idle at the start of that run): `llama3.1:8b` raised `TimeoutError`. `qwen2.5:14b` returned a decomposition whose edge named the parent id (`add2 -> job`), which `add_edge` rejected. `gemma4:latest` returned JSON whose sinks omitted declared output `value`. No tag exited 0, so the swap trigger below did not fire and the default string stays `llama3.1:8b`.  
- Comparison landed in the same session, not yet remeasured live: the compiler drops an edge whose endpoint is not a child id, and the system prompt tells the model to copy parent declared outputs onto every sink and to keep the parent id out of the edge list. `tests/test_runtime.py::test_edges_that_name_the_parent_are_ignored` covers the edge drop. A follow-up `--live --model qwen2.5:14b --only` was started and then stopped because a separate bench was loading `gpt-oss:120b` on the same Ollama server. That request was cancelled so it would not evict the other model.

**Revisit / supersede when:** `ollama ps` shows no runner (the other local bench has released the GPU). Then run `uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only`. If that exits 0 with `max_parallel >= 2` and sink value 25, supersede this decision and set `DEFAULT_MODEL` to `qwen2.5:14b`. A llama3.1:8b comparison after that uses a timeout above 180s. Do not repeat the identical 180s call. Do not load `qwen3.6:35b`, a coder-only tag, or `deepseek-v4-flash:cloud` for this check. Also re-run when the installed small instruct set changes.

- Measurement (2026-10-06): that command exited 0. stdout: `model=qwen2.5:14b ok=True repairs=0 waves=2 parallel=2 outputs={'add_results': {'value': 25}}`. Superseded by Decision 0023.

**References:** OQ-0015; Decision 0003; `src/atg/llm.py`; `examples/toy_parallel.py`.

---

## Decision 0018: Paper benchmarks stay deferred (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0012 (closed as wont-do for this milestone)  
**Deciders:** Same one-shot authorization as Decision 0012. This confirms Decision 0004. It does not supersede it.

**Context:** OQ-0012 asked which paper environment to port. Decision 0004 already deferred ALFWorld, WebShop, and ScienceWorld.

**Decision:** Do not add benchmark adapters. Synthetic tools, mock compiles, parallel execution, and localized repair are the measurement. Metrics that exist now: `waves`, `max_parallel`, `repairs`, `nodes_frozen_reused`.

**Rationale:** Those environments are heavy and drift. The library claims are testable without them.

Rejected alternatives:

1. **Port ALFWorld first** — large harness, not required for the control loop.  
2. **A toy household clone inside this repo** — still a second product.  
3. **Treat deferral as temporary silence** — the OQ would look open. It is closed until a named environment is requested.

**Consequences:**

- No `atg/integrations/benchmarks/` package.  
- OQ-0012 → `wont-do`.

**Revisit / supersede when:** a maintainer names one paper environment to port. Open a new OQ for that environment rather than reopening a blanket “benchmarks” item.

**References:** OQ-0012; Decision 0004; `docs/ARCHITECTURE.md` §3.2.

---

## Decision 0019: MIT license (2026-10-05)

**Status:** Accepted  
**Promotes:** OQ-0011  
**Deciders:** Maintainer, in chat (“ok MIT”).

**Context:** OQ-0011 asked MIT versus Apache-2.0. The software license is separate from the arXiv license on Zhang et al. (2026). That paper license does not cover this code.

**Decision:** The software is MIT. The copyright line is `Copyright (c) 2026 themark-net`, the same line already published on `origin/main`. The text is `LICENSE`. `pyproject.toml` and `CITATION.cff` say `MIT`. Citing the paper stays a requirement of `docs/ATTRIBUTION.md`. The license does not replace that citation.

**Rationale:** The library is small, its direct dependencies are MIT, and the maintainer holds no patent for Apache-2.0’s grant to cover. MIT is the shorter grant for reuse.

Rejected alternatives:

1. **Apache-2.0** — the patent grant covers patents the contributors themselves hold. It does not cover a claim by someone else on the paper’s method, and it adds a change-notice practice this repo does not need.  
2. **Leave the license unset** — blocks a clear redistribution statement.  
3. **A copyleft license** — the OQ asked for broad reuse. Copyleft was not requested.

**Consequences:**

- `LICENSE` is the software grant.  
- OQ-0011 → `promoted-to-adr`.  
- Dependencies keep their own licenses.  
- Paper credit stays in `CITATION.cff`, `docs/citations.bib`, and `docs/ATTRIBUTION.md`.

**Revisit / supersede when:** a contributor requires an explicit patent grant from this project, or the maintainer chooses copyleft.

**References:** OQ-0011; `LICENSE`; `docs/ATTRIBUTION.md`.

---

## Decision 0020: Third-party gap check against public ATG readings (2026-10-05)

**Status:** Accepted  
**Deciders:** Maintainer one-shot. Neither source is authoritative over the paper or over Decisions 0002–0019.

**Context:** There is no author SDK, package, or experiment repository for Zhang et al. (2026), arXiv:2607.01942. Two public readings exist. RegardV/ATG-looping (MIT, 2026-07-13) is a Claude Code skill plus a stdlib coding-agent ledger (`algl.py`). The fork hufeide/ATG-looping is two commits ahead (`fei`). Those commits harden the same ledger — relative write paths, a stricter artifact check — and append a build log. They do not add a paper mechanism. SnackOnAI (Mohinish S, 2026-07-15) publishes illustrative snippets reconstructed from §4.1–§4.3. Those snippets were checked against `https://arxiv.org/html/2607.01942v1`. Neither source is official code. Their code was not copied into this repository.

**Decision:** Adopt three behaviors this tree did not have. Record the rest as skipped.

Adopted:

1. A thought-experiment failure that names a live node is repaired before `execute`, then checked again. Paper §4.3 applies repair to thought-experiment failures and to runtime failures. `max_repairs` counts both (Decision 0014).  
2. `save_history` writes a temporary file and replaces the checkpoint. A failed write leaves the previous file.  
3. A node still `running` when `execute` starts becomes `failed` with error `interrupted before completion`. That is the legal `running → failed` move (Decision 0011). The tool is not called.

Skipped:

1. **Derived completion from an artifact hash and a gate command** (`algl.py`). Decision 0011 stores status. A node is done when its tool return is recorded, not when a file hash matches.  
2. **Write-collision serialization, preflight shell gates, consequential scoring, and a sticky per-scope attempt budget.** Those belong to the coding-agent ledger. Decision 0007 tools have no write set. The Love Equation regulator is a different RegardV project and was not read as ATG.  
3. **Refusing tasks of one to four steps.** The skill states that as usage advice. The paper does not, and a library gate would reject a legal graph.  
4. **A constraint or budget check in the thought experiment.** The skill lists it. Paper §4.2 lists tool selection, missing steps, dependencies, interfaces, and implausible paths. It does not list a budget.  
5. **An unscoped judge reason selects no repair region.** Repairing the whole graph would be the global replan Decision 0014 rejected. A reason that names a live node id still repairs.  
6. **SnackOnAI status name `succeeded`.** Decision 0011 says `done`.  
7. **String `input_spec` / `output_spec`.** Decision 0007 uses literals and `$ref`.  
8. **Refinement history as a list of ids.** Decision 0009 stores full snapshots. A `refinement_depth` integer is not in the paper. The snapshot sequence is the history.  
9. **A judge call on every thought experiment.** Decision 0013 runs structural rules first. The judge stays opt-in.  
10. **Repair only the failed node and one downstream hop, and the undefined `is_descendant` helper.** The snippet is not runnable. Decision 0014 already bounds the region by the lowest common historical ancestor plus the downstream cone.  
11. **ALFWorld, WebShop, and ScienceWorld walkthroughs.** Decision 0004. The blog’s benchmark numbers were not re-measured here.

**Rationale:** The three adopted behaviors are in the paper or in the checkpoint/status decisions already accepted. The skipped ones either contradict those decisions or belong to a coding-agent loop the paper does not describe.

Rejected alternatives:

1. **Vendor either source** — both say they are not the paper’s code. Vendoring would also pull the Love Equation bridge.  
2. **Replace stored status with hash-derived done** — reopens Decision 0011.  
3. **Treat the blog snippets as the method where they disagree with the HTML paper** — the HTML text wins.

**Consequences:**

- `run_task` may spend part of `max_repairs` before the first `execute`.  
- `tests/test_runtime.py` covers the three adopted behaviors.  
- No files from either repository were added.

**Revisit / supersede when:** a judge schema grows a node-id field, or a tool schema grows a declared write set. Either change needs its own decision.

**References:** Zhang et al. (2026) §§4.1–4.3 (`zhang2026atg`); Decisions 0004, 0007, 0009, 0011, 0013, 0014, 0015; https://github.com/RegardV/ATG-looping; https://www.snackonai.com/p/atomic-task-graph-a-7b-model-that-beats-gpt-4-react-on-alfworld-and-webshop-has-nothing-to-do-with-t; `docs/ATTRIBUTION.md`.

---

## Decision 0021: OpenAI-compatible local client (2026-10-06)

**Status:** Accepted

**Context:** `OllamaClient` posts to Ollama `/api/chat`. That route cannot talk to llama-server, Lemonade, or vLLM. Those servers speak OpenAI `/v1/chat/completions`. OQ-0017 still asks which of those servers should run the live toy. This decision does not pick one.

**Decision:** Add a stdlib `OpenAICompatClient` (`urllib`, `json`, `os`, pydantic). `model` is the argument, else `ATG_MODEL`, else `DEFAULT_MODEL` (`llama3.1:8b`). `base_url` is the argument, else `ATG_BASE_URL`, else `http://127.0.0.1:8000`, with any trailing slash removed. `api_key` is the argument, else `ATG_API_KEY`. When the key is set, send `Authorization: Bearer <key>`. When it is unset, send no auth header. `POST {base_url}/v1/chat/completions` with `model`, `messages`, `temperature` 0, and `stream` false. `complete_structured` first sends `response_format` `{"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()}}` and parses `choices[0].message.content` with `_parse_model`. If that validation fails, send one follow-up that appends a user message: the previous content was not valid JSON for the schema, return only JSON. The follow-up does not send `response_format`. If the follow-up is still invalid, raise `LLMError`. HTTP errors, URL errors, and socket timeouts raise `LLMError`. `urlopen` honors `timeout_s`. `examples/toy_parallel.py` takes `--client {ollama,openai}` and defaults to `ollama`. With `--live` and `openai`, it constructs `OpenAICompatClient(model, timeout_s=180)`.

**Rationale:** llama-server, Lemonade, and vLLM already share one chat-completions shape. A stdlib client reaches them without a new dependency and without sending Ollama's `/api/chat` body to a foreign port. One schema retry covers a prose reply. A second invalid reply, or a transport failure, is `LLMError` so compile does not loop or hang.

Rejected alternatives:

1. **Requiring the litellm extra** — Decision 0003 keeps LiteLLM optional. The local path and the core tests must not import it.  
2. **Pointing `ATG_OLLAMA_HOST` at a foreign port** — that client posts `/api/chat` with an Ollama `format` field, not `/v1/chat/completions`.

**Consequences:**

- `--client openai` is opt-in. The default live path stays `OllamaClient`.  
- Do not change `DEFAULT_MODEL`. It stays `llama3.1:8b` (Decision 0017).  
- OQ-0017 stays open. This client does not choose the live-toy server.

**References:** OQ-0017; Decision 0003; Decision 0017; `src/atg/llm.py`; `examples/toy_parallel.py`.

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

---

## Decision 0022: Toy PoC metrics for localized repair (2026-10-06)

**Status:** Accepted

**Context:** Decision 0014 freezes a successful sibling and repairs the failed region. That behavior had a unit test and no suite-level comparison against a whole-graph replan or a sequential replay. Paper benchmark scores stay deferred (Decision 0018).

**Decision:** The offline suite defines success, llm_calls, tool_calls, nodes_frozen_reused, repairs, wall_time_s. Localized repair is the product path. Global replan and sequential replay are measurement arms only. These numbers are toy-scale. They are not the paper's ALFWorld / WebShop / ScienceWorld scores.

**Rationale:** A scripted mock can show that repairing the failed region costs fewer structured planner calls than replacing the whole graph, and that sequential replay re-executes tools localized repair kept frozen. The comparison stays in the example so `repair_graph` does not grow a second policy.

Rejected alternatives:

1. **Changing Decision 0014 so the default repair becomes whole-graph** — that throws away the frozen-sibling result the paper's repair is for.
2. **Treating the suite as a paper reproduction** — the tasks are synthetic. They do not measure ALFWorld, WebShop, or ScienceWorld.

**Consequences:**

- `examples/poc_suite.py` writes `docs/poc/offline-report.json` and `docs/poc/offline-report.md`. `tests/test_poc_suite.py` checks the offline inequalities.
- Localized `repairs` counts `repair_graph` calls. Global `repairs` counts one whole-graph recompile. Sequential `repairs` stays 0 because a replay is not a repair.
- `max_parallel` on an arm is the widest wave, not a sum. The sequential arm stays at 1.
- Decision 0014 stays the product path.

**Revisit / supersede when:** a maintainer names one paper environment to port. That is a new decision, not a change to these toy numbers.

**References:** Decisions 0004, 0014, 0018; Zhang et al. (2026) §4.3 (`zhang2026atg`); `examples/poc_suite.py`; `docs/ATTRIBUTION.md`.

---

## Decision 0023: Default local model tag `qwen2.5:14b` (2026-10-06)

**Status:** Accepted  
**Supersedes:** Decision 0017

**Context:** Decision 0017 said to set `DEFAULT_MODEL` to `qwen2.5:14b` only if `examples/toy_parallel.py --live --model qwen2.5:14b --only` exited 0 with `max_parallel >= 2` and sink value 25.

**Decision:** `DEFAULT_MODEL` is `qwen2.5:14b`. `ATG_MODEL` still overrides it. The automatic fallback is `gemma4:latest` only. `llama3.1:8b` stays selectable through `ATG_MODEL` and is not an automatic fallback. Coder-only tags, tags much above about 15B, and `deepseek-v4-flash:cloud` stay off the default path. A later sweep may load a larger tag without changing this default.

**Rationale:** On 2026-10-06 the host was quiet (`ollama ps` empty, MemAvailable about 69 GiB). The command exited 0 and printed `model=qwen2.5:14b ok=True repairs=0 waves=2 parallel=2 outputs={'add_results': {'value': 25}}`. The model named the sink `add_results`. The declared output `value` is 25, two waves ran, and the widest wave was 2. That is the swap rule in Decision 0017.

Rejected alternatives:

1. **Leave the default at `llama3.1:8b`** — the written swap rule fired.  
2. **Also fall back to `llama3.1:8b` automatically** — that tag timed out at 180 seconds on 2026-10-05. A later comparison needs a longer timeout and is not the default path.  
3. **Make `qwen3.6:35b` the default because a bench scored it higher** — Decision 0017 kept tags above about 15B off the default. The 35B tag is a separate measurement.

**Consequences:**

- `tests/test_package.py` expects `qwen2.5:14b`.  
- Decision 0017 remains the record of the 2026-10-05 failures. Its status is Superseded by 0023.  
- The model was unloaded with `keep_alive: 0` after the run.

**References:** Decision 0017; `src/atg/llm.py`; `examples/toy_parallel.py`.

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
