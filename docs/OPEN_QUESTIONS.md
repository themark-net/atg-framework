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
| [OQ-0005](#oq-0005-decomposition--structured-output-strategy) | P1 | promoted-to-adr | Decomposition & structured output | — | Decision 0012 |
| [OQ-0006](#oq-0006-parallel-execution-runtime) | P0 | promoted-to-adr | Parallel execution runtime | — | Decision 0010 |
| [OQ-0007](#oq-0007-ready-queue-vs-static-topo-only) | P1 | promoted-to-adr | Ready-queue vs static topo only | — | Decision 0011 |
| [OQ-0008](#oq-0008-failure-detection--thought-experiment) | P1 | promoted-to-adr | Failure detection & thought experiment | — | Decision 0013 |
| [OQ-0009](#oq-0009-repair-localization-algorithm) | P1 | promoted-to-adr | Repair localization algorithm | — | Decision 0014 |
| [OQ-0010](#oq-0010-project-packaging--layout) | P0 | promoted-to-adr | Project packaging & layout | — | Decision 0008 |
| [OQ-0011](#oq-0011-license) | P2 | promoted-to-adr | License | — | Decision 0019 |
| [OQ-0012](#oq-0012-paper-benchmark-adapters) | P3 | wont-do | Paper benchmark adapters | — | Decision 0018 |
| [OQ-0013](#oq-0013-dspy--langgraph-adapter-depth) | P2 | promoted-to-adr | DSPy / LangGraph adapter depth | — | Decision 0016 |
| [OQ-0014](#oq-0014-persistence--memory-backend) | P2 | promoted-to-adr | Persistence / memory backend | — | Decision 0015 |
| [OQ-0015](#oq-0015-default-example-model-tags) | P2 | promoted-to-adr | Default example model tags | — | Decision 0017 |
| [OQ-0016](#oq-0016-repair-escalation-policy) | P2 | open | Repair escalation policy | Repeated failures | Decision 0014 |
| [OQ-0017](#oq-0017-which-local-server-runs-the-next-live-comparison) | P2 | open | Which local server runs the next live comparison | Live runtime comparison | Decision 0021 |

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
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** OQ-0004 (resolved), Decision 0003  
- **Related-ADR:** **Decision 0012**  
- **Related-code:** `src/atg/planner.py`, `src/atg/llm.py`  
- **Feature/runbook:** phase-3-planner  

**Question:** How does the LLM emit subgraphs (JSON schema, tool calls, free text+parse)? Recursive depth limits? (Depth may also be set under OQ-0004 D.)

**Options:**

1. JSON schema / `complete_structured`  
2. DSPy signatures (adapter path)  
3. Constrained decoding when available  

**Recommendation:** (1) in core; DSPy optional later.

**Resolution notes:**

- **2026-10-05:** Promoted to **Decision 0012**. Core asks for a Pydantic `Decomposition` via `complete_structured`. Depth cap stays 6 (Decision 0007). Revisit if the live toy script fails schema validation on every installed instruct model and a tool-call format succeeds on the same prompt. DSPy stays an adapter, not the compiler.

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
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** OQ-0006 (resolved by Decision 0010)  
- **Related-ADR:** **Decision 0011**  
- **Related-code:** `src/atg/graph.py` (`ready_ids`, `transition`)  
- **Feature/runbook:** phase-2-executor  

**Question:** Dynamic ready-queue as nodes complete, or precomputed levels only?

**Context:** Paper: node executable when predecessors done—natural ready-queue. Static levels are simpler but less flexible with repair mid-flight.

**Recommendation:** Dynamic ready-queue.

**Resolution notes:**

- **2026-10-05:** Promoted to **Decision 0011**. Dynamic ready-queue; status chain `pending → ready → running → done → frozen`, plus `running → failed`; a failure blocks descendants and leaves siblings eligible. The executor loop is still Phase 2. Paper §4.2 was specific enough. Thought-experiment policy (OQ-0008) and repair reset (OQ-0009) were not decided.

---

### OQ-0008: Failure detection & thought experiment

- **Priority:** P1  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** OQ-0005 (resolved)  
- **Related-ADR:** **Decision 0013**  
- **Related-code:** `src/atg/thought.py`  
- **Feature/runbook:** phase-4-repair  

**Question:** Thought experiment = rules-only, LLM judge, or hybrid? Runtime failure = exceptions only or also validators?

**Recommendation:** MVP hybrid: structural rules always; optional LLM judge behind flag.

**Resolution notes:**

- **2026-10-05:** Promoted to **Decision 0013**. Structural checks always run. `ATG_JUDGE=1` adds one judge call after the rules pass. Unit comparison: a structurally valid plan stays ok with the judge off, and the same plan is rejected when a scripted judge returns `ok=false`. Revisit when a live run passes the rules and then fails for a reason other than a tool exception: turn the judge on for that task and compare `judge_disagreements`. Runtime tool failures stay exceptions (Decision 0011), not a second validator framework.

---

### OQ-0009: Repair localization algorithm

- **Priority:** P1  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** OQ-0002 (resolved)  
- **Related-ADR:** **Decision 0014**  
- **Related-code:** `src/atg/repair.py`  
- **Feature/runbook:** phase-4-repair  

**Question:** Exact LCA-over-history algorithm and freeze semantics when multiple failures occur?

**Context:** Paper: lowest common historical ancestor of failed atomic nodes; repair minimal subgraph; freeze rest.

**Recommendation:** Implement explicit `parent_id` lineage on nodes + snapshot index; test with multi-fail fixtures before clever heuristics.

**Resolution notes:**

- **2026-10-05:** Promoted to **Decision 0014**. Lineage walks `parent_id`, then older snapshots. The lowest common ancestor is the common id closest to the failed nodes. The repair region is every live node under that ancestor, plus downstream nodes. Successes outside the region are frozen. `transition` still refuses `failed → pending`; `reset_for_repair` is the only reset and it refuses frozen nodes. Revisit if a fixture shows the LCA region re-executes a node the test required to stay frozen, or if two failures share no ancestor and the union of their cones is too large: the alternative is “repair only the failed node plus its descendants,” which is already what a missing ancestor does.

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
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** **Decision 0019**  
- **Related-code:** `LICENSE`  
- **Feature/runbook:** packaging  

**Question:** MIT vs Apache-2.0?

**Recommendation:** MIT for max reuse unless patent concerns favor Apache-2.0.

**Resolution notes:**

- **2026-10-05:** Left open until the maintainer chose.  
- **2026-10-05:** Maintainer chose MIT. Promoted to **Decision 0019**. `LICENSE` is the grant. Paper citation stays in `docs/ATTRIBUTION.md` and is separate from this software license.

---

### OQ-0012: Paper benchmark adapters

- **Priority:** P3  
- **Status:** wont-do  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** —  
- **Blocked-by:** Decision 0004 (deferred by design)  
- **Related-ADR:** Decision 0004, **Decision 0018**  
- **Related-code:** none (no benchmark package)  
- **Feature/runbook:** phase-optional-benchmarks  

**Question:** Which paper envs first, if any? ALFWorld vs lighter synthetic household tasks?

**Recommendation:** Stay deferred until core repair metrics are solid.

**Resolution notes:**

- **2026-10-05:** **Decision 0018**. Still deferred. Repair metrics now exist on synthetic tasks (`waves`, `repairs`, `nodes_frozen_reused`). Revisit only when someone names one paper environment to port. Do not start ALFWorld, WebShop, or ScienceWorld before that.

---

### OQ-0013: DSPy / LangGraph adapter depth

- **Priority:** P2  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** Decision 0002, **Decision 0016**  
- **Related-code:** `src/atg/integrations/`  
- **Feature/runbook:** phase-6  

**Question:** Thin wrappers vs bidirectional sync of state?

**Recommendation:** One-way “run ATG inside foreign framework” first.

**Resolution notes:**

- **2026-10-05:** Promoted to **Decision 0016**. `as_langgraph_node` and `as_dspy_forward` return plain callables. They do not import either framework. Revisit bidirectional checkpoint sync only if a caller must pause inside an ATG run and resume from the other framework’s saver.

---

### OQ-0014: Persistence / memory backend

- **Priority:** P2  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** OQ-0002 (resolved)  
- **Related-ADR:** **Decision 0015**  
- **Related-code:** `src/atg/persist.py`  
- **Feature/runbook:** phase-6  

**Question:** In-memory only for MVP (yes) then JSON files vs SQLite vs vector store for semantic reuse?

**Recommendation:** In-memory MVP; JSON checkpoint next; vectors only if reuse-by-similarity is proven needed.

**Resolution notes:**

- **2026-10-05:** Promoted to **Decision 0015**. Runtime history stays in memory. `save_history` / `load_history` write one JSON list of snapshots. Revisit SQLite when a checkpoint file is too large to load whole. Revisit a vector store only after a concrete similarity-reuse task exists.

---

### OQ-0015: Default example model tags

- **Priority:** P2  
- **Status:** promoted-to-adr  
- **Created:** 2026-07-11  
- **Updated:** 2026-10-05  
- **Blocks:** — (resolved)  
- **Blocked-by:** —  
- **Related-ADR:** Decision 0003, **Decision 0017**  
- **Related-code:** `examples/toy_parallel.py`, `src/atg/llm.py`  
- **Feature/runbook:** phase-5  

**Question:** Which Ollama/LiteLLM model string do examples document in 2026?

**Context:** Paper’s Gemma-1.1 / Llama-3 / Mistral-v0.2 are outdated pins—see ARCHITECTURE §4.1.

**Recommendation:** Document `ollama/<current-small-instruct>` as placeholder; read from env `ATG_MODEL`.

**Resolution notes:**

- **2026-10-05:** Promoted to **Decision 0017**. Default tag `llama3.1:8b` via `ATG_MODEL`. Fallback order if that tag cannot emit a valid `Decomposition`: `qwen2.5:14b`, then `gemma4:latest`. Coder-only tags and `deepseek-v4-flash:cloud` are not defaults.  
- **2026-10-05 measurement:** `--live` exited 1 for all three tags (`llama3.1:8b` timeout at 180s, `qwen2.5:14b` parent-id edge, `gemma4:latest` missing sink output `value`). The default was not swapped. Parent-id edges are now dropped in the compiler. Re-run `examples/toy_parallel.py --live --model qwen2.5:14b --only` when `ollama ps` is empty. Details and the supersede rule are on Decision 0017.

---

### OQ-0016: Repair escalation policy

- **Priority:** P2  
- **Status:** open  
- **Created:** 2026-09-20  
- **Updated:** 2026-10-05  
- **Blocks:** —  
- **Blocked-by:** —  
- **Related-ADR:** Decision 0014  
- **Related-code:** `src/atg/repair.py`, `src/atg/run.py`  
- **Feature/runbook:** phase-4  

**Question:** When the same region fails again, should repair widen to the parent, or retry that region until `max_repairs`?

**Context:** Brought across from `origin/cursor/first-pass-atg-loop-b0e3`, where it was left open. That branch retried a region once, then widened to the parent (`escalate_after=1`, `max_repairs=3`). Paper §4.3 names the lowest common historical ancestor and does not say what a second failure of that region does. Decision 0014 retries the same region and stops at `max_repairs` (default 2). It does not widen.

**Options:**

1. Keep Decision 0014: same region, then stop.  
2. Widen one parent level after the region has failed once, and cap the total repairs.  
3. Count failures per tool name.  
4. Ask the model to choose the region.

**Recommendation:** Keep (1) until a live run shows the same region failing twice for a reason a wider parent would fix.

**Resolution notes:**

- **2026-10-05:** Recorded from `cursor/first-pass-atg-loop-b0e3` (`1982c58`). Not implemented. That branch’s `$parent` input convention was not copied. Decision 0012 already fixes literals and `$ref`.
- **2026-10-07:** The branch was not merged. `main` keeps `run_task`. `escalate_after` stays out until a live double failure says otherwise.

---

### OQ-0017: Which local server runs the next live comparison

- **Priority:** P2
- **Status:** open
- **Created:** 2026-10-06
- **Updated:** 2026-10-07
- **Blocks:** a measured choice of live server after the Ollama default
- **Blocked-by:** a quiet host and one scored run
- **Related-ADR:** Decision 0021, Decision 0023
- **Related-code:** `src/atg/llm.py` (`OllamaClient`, `OpenAICompatClient`), `examples/toy_parallel.py`
- **Feature/runbook:** `docs/NEXT.md`, `docs/USING.md` Level 3

**Question:** The default live path is Ollama `qwen2.5:14b`. For the next comparison, should a run go through Lemonade, through the vLLM environment under the home directory, or stay on Ollama?

**Context:** Decision 0023 already accepted the 14B Ollama toy (sink value 25, width 2). Decision 0021 added `OpenAICompatClient`, so Lemonade and vLLM are reached with `ATG_BASE_URL` and `--client openai`. They do not need a new client, and they do not need `ATG_OLLAMA_HOST`.

On 2026-10-06 Lemonade 2026.40.0 was listening on `127.0.0.1:13305` with no model loaded. The NPU is present (`1022:17f0`, `/dev/accel`). `flm:npu` was not installed, so that server was not using the NPU. A GGUF through Lemonade’s llama.cpp backend uses the same iGPU class as Ollama.

On 2026-10-07 `/home/mark/vllm-rocm/.venv` imports `vllm` 0.29.1.dev0 (ROCm 10.1 userspace inside that venv, Python 3.14). This repository has not sent a toy through that server. vLLM uses the 8060S, not the NPU.

**Options:**

1. Keep the Decision 0023 default on Ollama. Compare another server later, one model at a time.
2. Serve one 7B–14B checkpoint with the home vLLM venv and run `examples/toy_parallel.py --live --client openai --only`. Judge schema success and sink value.
3. Point the same command at Lemonade’s OpenAI API after a model is loaded there. The NPU comparison is a separate run that needs `flm:npu` and an FLM model.

**Recommendation:** Keep (1) as the default. The next measurement is one quiet-host toy through `OpenAICompatClient`, either vLLM or Lemonade, not both at once. Do not change `DEFAULT_MODEL` from that run unless it exits 0 with sink value 25 and width at least 2, and a decision says to swap.

**Resolution notes:**

- **2026-10-06:** Parked while another bench held the GPU. Notes lived only in a stash on `29bca8a`.
- **2026-10-07:** Restored onto `main`. The 14B Ollama toy has since passed, and the OpenAI client exists. vLLM imports in the home venv and is still unscored.

---

## How to add

1. Next ID = max + 1 (`OQ-NNNN`). Never reuse.  
2. Add index row + detail section (or `docs/open-questions/OQ-NNNN-slug.md` + link).  
3. Reference from TODO item that is blocked.  
4. On answer: append dated **Resolution notes**; set status; if architectural → `/adr` and status `promoted-to-adr`.
