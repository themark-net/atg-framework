# Open Questions — atg-framework

**Purpose:** Central index of open questions, TBDs, and parked decisions for multithreaded work.  
**Agents:** Scan this file at the start of multi-step work. Promote architectural answers via `/adr` → `docs/DECISIONS.md`.  
**Backlog:** [`docs/TODO.md`](TODO.md) references these IDs.  
**Architecture:** [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)

**Status:** `open` | `blocked` | `tbd` | `answered` | `promoted-to-adr` | `wont-do`  
**Priority:** P0 (blocks MVP) | P1 (next milestone) | P2 | P3 (someday)

---

## Index

| ID | Priority | Status | Title | Blocks | Related |
|----|----------|--------|-------|--------|---------|
| [OQ-0001](#oq-0001-graph-library-choice) | P0 | promoted-to-adr | Graph library choice | — | Decision 0005 |
| [OQ-0002](#oq-0002-history--evolution-representation) | P0 | promoted-to-adr | History / evolution representation | — | Decision 0009 |
| [OQ-0003](#oq-0003-node--result-data-model) | P0 | promoted-to-adr | Node & result data model | — | Decision 0006 |
| [OQ-0004](#oq-0004-atomic-task--tool-definition) | P0 | promoted-to-adr | Atomic task / tool definition | — | Decision 0007 |
| [OQ-0005](#oq-0005-decomposition--structured-output-strategy) | P1 | open | Decomposition & structured output | Planner quality | Decision 0006 |
| [OQ-0006](#oq-0006-parallel-execution-runtime) | P0 | promoted-to-adr | Parallel execution runtime | — | Decision 0010 |
| [OQ-0007](#oq-0007-ready-queue-vs-static-topo-only) | P1 | open | Ready-queue vs static topo only | Scheduler design | paper §4.2 |
| [OQ-0008](#oq-0008-failure-detection--thought-experiment) | P1 | open | Failure detection & thought experiment | Phase 4 | paper §4.2–4.3 |
| [OQ-0009](#oq-0009-repair-localization-algorithm) | P1 | open | Repair localization algorithm | Phase 4 | paper §4.3 |
| [OQ-0010](#oq-0010-project-packaging--layout) | P0 | promoted-to-adr | Project packaging & layout | — | Decision 0008 |
| [OQ-0011](#oq-0011-license) | P2 | open | License | Distribution | README |
| [OQ-0012](#oq-0012-paper-benchmark-adapters) | P3 | open | Paper benchmark adapters | Parity experiments | Decision 0004 |
| [OQ-0013](#oq-0013-dspy--langgraph-adapter-depth) | P2 | open | DSPy / LangGraph adapter depth | Phase 6 | Decision 0002 |
| [OQ-0014](#oq-0014-persistence--memory-backend) | P2 | open | Persistence / memory backend | Long runs, reuse | ARCH §5 |
| [OQ-0015](#oq-0015-default-example-model-tags) | P2 | open | Default example model tags | Examples docs | Decision 0003, ARCH §4 |

---

## Detail

### OQ-0001: Graph library choice

- **Priority:** P0  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** **Decision 0005** (also Decision 0002)  
- **Related-code:** `atg/graph.py` (planned)  
- **Feature/runbook:** phase-1-skeleton  

**Question:** Implement DAG ops with stdlib-only structures, optional NetworkX internally, or something else?

**Context:** Need topo sort, ancestors/descendants, cycle check, subgraph extract. NetworkX is rich but a dependency. Decision 0002 forbids NetworkX as *public* API identity.

**Options:**

1. **Stdlib-only** dict/list graph — minimal deps, full control  
2. **NetworkX internal** — faster algorithms/viz; hide behind our types  
3. **Hybrid** — stdlib core; NetworkX only in optional `[viz]` extra  

**Recommendation:** (1) for MVP; revisit (3) if viz/algorithms hurt.

**Resolution notes:**

- **2026-07-11:** Accepted option (1). Promoted to **Decision 0005**. Maintainer accepted agent recommendation citing limited graph-library domain knowledge—Decision 0005 records explicit **revisit triggers** (profiling, algorithm needs, viz pressure, expert input) so the choice is not treated as irreversible dogma.

---

### OQ-0002: History / evolution representation

- **Priority:** P0  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** **Decision 0009**  
- **Related-code:** `atg/history.py` (planned)  
- **Feature/runbook:** phase-4-repair  

**Question:** Full graph snapshots each refine step, event log, or both?

**Context:** Paper records intermediate graphs each refinement round for LCA-style localization.

**Options:**

1. Full immutable snapshots (simple, memory-heavier)  
2. Event log (add/replace/remove node) + materialize  
3. Snapshots for compile rounds + events for repair  

**Recommendation:** (1) until graphs are large; add compaction later.

**Resolution notes:**

- **2026-07-11:** Interactive — option **1** full snapshots. Promoted to **Decision 0009**.

---

### OQ-0003: Node & result data model

- **Priority:** P0  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** **Decision 0006**  
- **Related-code:** `atg/types.py` (planned)  
- **Feature/runbook:** phase-1-skeleton  

**Question:** Exact fields for `TaskNode` / outputs / symbolic input refs? Pydantic models vs dataclasses?

**Context:** ARCH §5.2 is a sketch only. Need binding for “output of node A field x → input of B”. Greenfield: no pre-existing type stack; structured LLM output is planned (OQ-0005).

**Options:**

1. Dataclasses + plain dicts (light)  
2. Pydantic v2 models (validation ergonomics)  
3. TypedDict-only JSON shapes  

**Recommendation:** Pydantic if structured LLM output is in play; else dataclasses + validators → resolves to **Pydantic** for this project.

**Resolution notes:**

- **2026-07-11:** Accepted **Pydantic v2** as the public modeling standard. Promoted to **Decision 0006**. Conditional recommendation resolved because planner structured output is on the path. Maintainer accepted without a strong prior stack preference; Decision 0006 lists revisit triggers (zero-dep policy, churn, perf, alternate structured-output stack). Exact field lists may still evolve in implementation PRs without reopening this OQ.

---

### OQ-0004: Atomic task / tool definition

- **Priority:** P0  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** **Decision 0007** (also 0006, 0002)  
- **Related-code:** `atg/tools.py`, `atg/planner.py`, `atg/executor.py` (planned)  
- **Feature/runbook:** phase-1-skeleton  

**Question (umbrella):** What counts as an **atomic** node in *this* framework, how do users **register** tools the planner/executor can use, and how does compilation **know it is done**?

This is the main product-shape question left for Phase 1. The paper is conceptual; we must pick engineering contracts.

---

#### Why this matters

Paper (Def. 2–3, §4.1): a **tool** is an atomic functional unit used only via its I/O interface; **recursive compilation** stops when every node is a single atomic tool-use. If we get “atomic” wrong, either:

- the planner never stops refining, or  
- it stops too early and “atomic” nodes still need hidden multi-step logic, or  
- the executor cannot map nodes to real callables.

---

#### Paper baseline (not optional semantics)

| Idea | Paper meaning | Engineering implication |
|------|---------------|-------------------------|
| Tool \(f: I \to O\) | Opaque unit; not further decomposed | Must be invokable without another ATG plan *inside* the tool (unless we explicitly allow nested ATG later) |
| Node \(v=(i,f,o)\) | One tool call with inputs/outputs | Executor: bind inputs → call \(f\) → store outputs |
| Interface preservation | Subgraph of a parent keeps same external I/O | Non-atomic nodes are **placeholders** for a subgraph with the same interface |
| Termination | All nodes atomic tool-use units | Need a boolean (or enum) “is this node atomic?” |

---

#### Sub-questions to answer (please address A–F; G optional)

Use these as a checklist in your reply. Short answers are fine (“A: 1”, “B: …”).

**A. What makes a node atomic?**

1. **Registry-backed only:** atomic iff `tool_name` is registered in the tool registry.  
2. **Flag on the node:** `atomic: bool` set by planner or user (registry optional for pure data nodes).  
3. **Hybrid:** registered tool ⇒ atomic; planner may also emit `atomic=true` for “literal/result” nodes with no tool.  
4. Other: …

**B. What is a “tool” in the registry?**

1. **Python callable** + name + description + optional JSON Schema / Pydantic model for args (and maybe results).  
2. **OpenAI-style tool spec only** (name, description, parameters JSON Schema); runtime binds name → callable separately.  
3. **Both:** schema for LLM planning, callable for execution, same name.  
4. Other: …

**C. May tools have side effects?** (files, network, env actions)

1. Yes, unrestricted once registered (user responsibility).  
2. Yes, but tools declare `side_effect: bool` / categories for thought-experiment / ordering.  
3. MVP: pure functions only; side-effect tools later.  
4. Other: …

**D. Compile stop / non-atomic nodes**

When the planner emits a subgraph, non-atomic children need a definition.

1. Non-atomic = “abstract subtask” with name + desired I/O, **no** `tool_name` until refined.  
2. Non-atomic = temporary tool name like `plan:` / `think:` that is **not** in the executable registry.  
3. Other: …

Also: **max refine depth** default? (e.g. 4 / 8 / unlimited with safety cap)

**E. Forced-atomic / “do not refine further” escape hatch**

Sometimes a user wants a multi-step helper wrapped as one tool (e.g. `run_sql_pipeline`) that the ATG must **not** explode.

1. **Allow:** `atomic=True` or `refine=False` on registry entry or node—compilation must leave it alone.  
2. **Disallow** for MVP—everything either abstract or a single real tool.  
3. Other: …

**F. Input binding style** (how node B reads node A’s output)

1. Explicit refs: `{"query": {"$ref": "node_a.outputs.text"}}` (or similar).  
2. Name-based auto-wire by matching parameter names to upstream outputs (fragile).  
3. Planner always inlines literal values after upstream completes (executor-time binding only).  
4. Mix: literals + `$ref` for MVP.  

**G. (Optional) Nested ATG**

Can a tool implementation itself run a sub-ATG?

1. Not in MVP.  
2. Allowed as an advanced tool type later.  

---

#### Worked examples (sanity check your answers)

**Example 1 — research-ish toy**

Task: “Get weather for Paris and summarize packing advice.”

Possible graph:

- `n1` tool=`get_weather` args=`{city: "Paris"}` → atomic  
- `n2` tool=`llm_summarize` args=`{text: $ref n1.forecast}` → atomic  
- Edge `n1 → n2`

Questions: Are both registry tools? Is `llm_summarize` a normal tool or special?

**Example 2 — needs decomposition**

Task: “Plan a weekend trip.”

Initial node might be non-atomic `plan_weekend` with outputs `{itinerary: str}`. Compile expands into search + book + summarize subgraph **preserving** `{itinerary}` as the external interface.

Questions: How did we mark `plan_weekend` non-atomic? What stops infinite expand?

**Example 3 — forced atomic**

Tool `legacy_blackbox_agent(prompt) -> str` runs an internal ReAct loop. User registers it with “never refine.”

Questions: Does our model support that without the planner fracturing it into fake steps?

---

#### Option packages (if you prefer picking a bundle)

| Bundle | Summary |
|--------|---------|
| **R1 — Recommended default** | A3 hybrid atomic · B3 schema+callable · C1 user-responsible side effects (declare later) · D1 abstract nodes without tool_name · max depth 6 · E1 refine=False escape · F4 literals+`$ref` · G1 no nested ATG MVP |
| **R2 — Strict pure** | A1 registry-only · B1 callable+schema · C3 pure-only MVP · D1 · E2 no escape · F4 · G1 |
| **R3 — LLM-tools native** | A1 · B2 OpenAI-style specs · separate callable map · C1 · D2 synthetic tool names · E1 · F1 refs only · G1 |

You can say “R1” and then override individual letters.

---

#### Recommendation (agent — not binding until you choose)

**R1** balances paper fidelity (abstract → atomic), practical LLM tool schemas, and a forced-atomic escape hatch for real systems. Side-effect categories (C2) can wait until thought-experiment work (OQ-0008).

**Resolution notes:**

- **2026-07-11:** Interactive Q&A (not doc-only). Maintainer preferred OpenAI-style tool JSON schemas; registry **holds** those schemas **plus** same-name callables. Chose **E1** (`refine=False`) and **F4** (literals + `$ref`). Accepted proposed package as **Decision 0007** (atomicity, abstract nodes, depth 6, side effects allowed, no nested ATG MVP). Domain-knowledge limits noted in ADR revisit triggers.

---

### OQ-0005: Decomposition & structured output strategy

- **Priority:** P1  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Real planner quality  
- **Blocked-by:** OQ-0004 (atomic/tool contracts), Decision 0003  
- **Related-ADR:** Decision 0003; Decision 0006 (Pydantic schemas available)  
- **Related-code:** `atg/planner.py` (planned)  
- **Feature/runbook:** phase-3-planner  

**Question:** How does the LLM emit subgraphs (JSON schema, tool calls, free text+parse)? Recursive depth limits? (Depth may also be set under OQ-0004 D.)

**Options:**

1. JSON schema / `complete_structured`  
2. DSPy signatures (adapter path)  
3. Constrained decoding when available  

**Recommendation:** (1) in core; DSPy optional later.

**Resolution notes:**

- (none yet)

---

### OQ-0006: Parallel execution runtime

- **Priority:** P0  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** **Decision 0010**  
- **Related-code:** `atg/executor.py` (planned)  
- **Feature/runbook:** phase-2-executor  

**Question:** `ThreadPoolExecutor`, `asyncio`, or pluggable?

**Context:** LLM/tool calls are usually I/O bound. Async is nice but complicates sync tool wrappers.

**Options:**

1. Threads first (simple)  
2. Async-first  
3. Protocol with thread default  

**Recommendation:** (3) with thread default for MVP.

**Resolution notes:**

- **2026-07-11:** Interactive — accept recommendation **(3)**. Promoted to **Decision 0010**.

---

### OQ-0007: Ready-queue vs static topo only

- **Priority:** P1  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Scheduler sophistication  
- **Blocked-by:** OQ-0006  
- **Related-ADR:** —  
- **Related-code:** `atg/executor.py`  
- **Feature/runbook:** phase-2-executor  

**Question:** Dynamic ready-queue as nodes complete, or precomputed levels only?

**Context:** Paper: node executable when predecessors done—natural ready-queue. Static levels are simpler but less flexible with repair mid-flight.

**Recommendation:** Dynamic ready-queue.

**Resolution notes:**

- (none yet)

---

### OQ-0008: Failure detection & thought experiment

- **Priority:** P1  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Phase 4 robustness  
- **Blocked-by:** OQ-0005  
- **Related-ADR:** —  
- **Related-code:** `atg/thought.py`, `atg/repair.py`  
- **Feature/runbook:** phase-4-repair  

**Question:** Thought experiment = rules-only, LLM judge, or hybrid? Runtime failure = exceptions only or also validators?

**Recommendation:** MVP hybrid: structural rules always; optional LLM judge behind flag.

**Resolution notes:**

- (none yet)

---

### OQ-0009: Repair localization algorithm

- **Priority:** P1  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Faithful §4.3 behavior  
- **Blocked-by:** OQ-0002  
- **Related-ADR:** —  
- **Related-code:** `atg/repair.py`  
- **Feature/runbook:** phase-4-repair  

**Question:** Exact LCA-over-history algorithm and freeze semantics when multiple failures occur?

**Context:** Paper: lowest common historical ancestor of failed atomic nodes; repair minimal subgraph; freeze rest.

**Recommendation:** Implement explicit `parent_id` lineage on nodes + snapshot index; test with multi-fail fixtures before clever heuristics.

**Resolution notes:**

- (none yet)

---

### OQ-0010: Project packaging & layout

- **Priority:** P0  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** **Decision 0008**  
- **Related-code:** `pyproject.toml`, `src/atg/` (planned)  
- **Feature/runbook:** phase-1-skeleton  

**Question:** `src/atg` vs flat `atg/`? uv vs pip-tools? optional extras matrix?

**Recommendation:** `src/atg` + hatchling/uv; extras: `[llm]`, `[viz]`, `[integrations]`.

**Resolution notes:**

- **2026-07-11:** Interactive: **A1** `src/atg/`, **B1** pyproject + uv, **C1** optional extras. Promoted to **Decision 0008**.

---

### OQ-0011: License

- **Priority:** P2  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Clear redistribution  
- **Blocked-by:** —  
- **Related-ADR:** —  
- **Related-code:** `LICENSE`  
- **Feature/runbook:** packaging  

**Question:** MIT vs Apache-2.0?

**Recommendation:** MIT for max reuse unless patent concerns favor Apache-2.0.

**Resolution notes:**

- (none yet)

---

### OQ-0012: Paper benchmark adapters

- **Priority:** P3  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Scientific parity runs  
- **Blocked-by:** Decision 0004 (deferred by design)  
- **Related-ADR:** Decision 0004  
- **Related-code:** `atg/integrations/benchmarks/` (future)  
- **Feature/runbook:** phase-optional-benchmarks  

**Question:** Which paper envs first, if any? ALFWorld vs lighter synthetic household tasks?

**Recommendation:** Stay deferred until core repair metrics are solid.

**Resolution notes:**

- (none yet)

---

### OQ-0013: DSPy / LangGraph adapter depth

- **Priority:** P2  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Phase 6 polish  
- **Blocked-by:** Decision 0002, working core  
- **Related-ADR:** Decision 0002  
- **Related-code:** `atg/integrations/`  
- **Feature/runbook:** phase-6  

**Question:** Thin wrappers vs bidirectional sync of state?

**Recommendation:** One-way “run ATG inside foreign framework” first.

**Resolution notes:**

- (none yet)

---

### OQ-0014: Persistence / memory backend

- **Priority:** P2  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Multi-session reuse  
- **Blocked-by:** OQ-0002  
- **Related-ADR:** —  
- **Related-code:** future  
- **Feature/runbook:** phase-6  

**Question:** In-memory only for MVP (yes) then JSON files vs SQLite vs vector store for semantic reuse?

**Recommendation:** In-memory MVP; JSON checkpoint next; vectors only if reuse-by-similarity is proven needed.

**Resolution notes:**

- (none yet)

---

### OQ-0015: Default example model tags

- **Priority:** P2  
- **Status:** open  
- **Created:** 2026-07-11  
- **Updated:** 2026-07-11  
- **Blocks:** Copy-paste examples  
- **Blocked-by:** Decision 0003  
- **Related-ADR:** Decision 0003  
- **Related-code:** `examples/`  
- **Feature/runbook:** phase-5  

**Question:** Which Ollama/LiteLLM model string do examples document in 2026?

**Context:** Paper’s Gemma-1.1 / Llama-3 / Mistral-v0.2 are outdated pins—see ARCHITECTURE §4.1.

**Recommendation:** Document `ollama/<current-small-instruct>` as placeholder; read from env `ATG_MODEL`.

**Resolution notes:**

- (none yet)

---

## How to add

1. Next ID = max + 1 (`OQ-NNNN`). Never reuse.  
2. Add index row + detail section (or `docs/open-questions/OQ-NNNN-slug.md` + link).  
3. Reference from TODO item that is blocked.  
4. On answer: append dated **Resolution notes**; set status; if architectural → `/adr` and status `promoted-to-adr`.
