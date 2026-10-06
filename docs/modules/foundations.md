# Module: atg foundations

**Architecture layer:** Core graph, history, tools, and validation (`docs/ARCHITECTURE.md` §5.1–5.5)  
**Code:** `src/atg/` (`types.py`, `graph.py`, `history.py`, `tools.py`, `validation.py`)  
**Related ADR / Decisions:** 0005, 0006, 0007, 0008, 0009, 0011

Paper concepts in this package come from Zhang et al. (2026), `zhang2026atg`: Definition 2 (tool), Definition 3 (node), §4.1 (interface preservation and refinement history), §4.2 (readiness and node state). This is an independent reimplementation. Policy: `docs/ATTRIBUTION.md`.

## Operator

### What it does

You build a directed acyclic task graph, register Python tools with an OpenAI-style schema, record full snapshots of the graph, and check that `$ref` inputs point at ancestor outputs. The package does not call an LLM and does not run tools for you. The Phase 2 executor will call `mark_ready` and `transition`.

### How to run

From the repository root:

```bash
uv sync --extra dev
uv run pytest
uv run python -c "import atg; print(atg.__version__)"
```

`uv run pytest` is the Phase 1 gate. It needs no API key, no Ollama process, and no network at test time. The first `uv sync` downloads Pydantic and pytest from PyPI into `.venv/`.

### Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| `CycleError` on `add_edge` | The new edge closes a cycle, including a self-loop | The edge is not stored. Remove the dependency or split the node. |
| `GraphError` on `transition` | Status move is not in the Decision 0011 list, or `failed` has no error string | Follow `pending → ready → running → done → frozen`, or `running → failed` with `error=`. |
| `GraphError` on `freeze` | Node is not `done` | Finish the node, then freeze it. |
| `InterfaceError` | `$ref` target is missing, is not an ancestor, or the field is undeclared / not produced. Or a replacement subgraph drops a parent input or sink output. | Point `$ref` at `node_id.outputs.field` along an edge, and cover `declared_outputs` on sink nodes. |
| `ToolError` | Duplicate `register` or unknown name | Tool names are unique. |
| `ValidationError` on `TaskNode` | Bad id or a malformed `$ref` object | Ids match `^[A-Za-z_][A-Za-z0-9_-]*$`. A ref is exactly `{"$ref": "node_id.outputs.field"}`. |
| `ModuleNotFoundError: atg` | Package not installed into the environment | `uv sync --extra dev` from the repo root, then `uv run`. |

## Configuration / variables

Phase 1 reads no environment variables and has no config file.

| Name | Where | Purpose |
|------|-------|---------|
| Node id / field pattern | `src/atg/types.py` | Ids and `$ref` fields. Dots are rejected so `node_id.outputs.field` stays unambiguous. |
| `TaskNode.refine` | default `True` | `False` forces the node atomic (Decision 0007). |
| `ToolSchema.refine` | default `True` | Stored on the tool. A registered tool is atomic either way; `False` records the forced-atomic flag. |
| `ToolSchema.parameters` | default `{"type": "object", "properties": {}}` | JSON Schema exported by `as_openai_tools`. |
| Snapshot list | `GraphHistory` instance, in memory | Full copy per `append` (Decision 0009). Nothing is written to disk. |
| `[dev]` extra | `pyproject.toml` | pytest. `[llm]`, `[viz]`, and `[integrations]` are reserved by Decision 0008 and are not defined until those dependencies exist. |

## Agent

### Entry points

- `TaskNode`, `NodeStatus`, `parse_ref`, `Ref` — node payload and `$ref` parsing
- `TaskGraph.add_node`, `add_edge`, `topological_order`, `ancestors`, `subgraph`, `copy`
- `TaskGraph.ready_ids`, `mark_ready`, `transition`, `freeze` — Decision 0011 contract. No runner yet.
- `GraphHistory.append`, `GraphSnapshot.to_graph`
- `ToolRegistry.register`, `get`, `as_openai_tools`; `is_atomic`
- `assert_valid`, `assert_refs`, `assert_interface_preserved`

### Data shapes

- Node input literal: any JSON-like value without a `$ref` key.
- Node input ref: `{"$ref": "src.outputs.city"}` and nothing else in that object.
- OpenAI export: `{"type": "function", "function": {"name", "description", "parameters"}}`. The callable is not exported.
- Snapshot: `version`, `reason`, `created_at` (UTC ISO), `nodes` in topological order, `edges` as `(src, dst)` producer → consumer.
- Edge direction: producer → consumer. `a → b` means `a` is a predecessor of `b`.

### Callers / callees

Nothing outside `src/atg/` calls this package yet. Inside the package:

- `graph` uses `types` only.
- `history` copies a `TaskGraph` into a frozen `GraphSnapshot`.
- `validation` reads `TaskGraph` and `parse_ref`. It does not import the registry.
- `tools.is_atomic` reads a `TaskNode` and, when passed, a `ToolRegistry`.
- `__init__.py` re-exports the public names.

### Invariants

- Core does not import NetworkX, LangGraph, or DSPy (Decisions 0002, 0005).
- `TaskNode` is frozen. Status changes replace the graph’s stored copy via `transition` (Decisions 0006, 0011).
- `add_edge` that would cycle leaves the graph unchanged.
- `ready_ids` lists `pending` or `ready` nodes whose predecessors are all `done` or `frozen`, in topological order (Decision 0011, paper §4.2).
- `failed` blocks descendants. Siblings can still become ready. There is no transition back to `pending` (OQ-0009).
- `GraphHistory.append` deep-copies nodes. Later edits to the live graph do not change an earlier snapshot (Decision 0009).
- `subgraph` is induced: an edge is kept only when both ends are in the set. Transitive shortcuts are not invented.
- `is_atomic` is true when `node.refine` is false or `tool_name` is in the registry (Decision 0007).
- `assert_interface_preserved` requires every parent `$ref` to be consumed by the subgraph, rejects external refs the parent does not have, and requires sink `declared_outputs` to cover the parent’s declared outputs (paper §4.1). Literal values are not compared.
- `topological_order` is Kahn with id-sorted frontiers, so the order is stable.

### Extension points

- Phase 2 adds an executor that calls `mark_ready` and `transition`. It should take a runner object so tests can avoid threads (Decision 0010). It must not grow a second status enum.
- Phase 3 planner calls `is_atomic` and `assert_interface_preserved`, then `GraphHistory.append` once per refine step.
- Phase 4 repair may need `failed → pending` or a new status. That requires a superseding ADR, not a quiet edit to `_ALLOWED`.
- Optional extras `[llm]`, `[viz]`, `[integrations]` stay out of the core import path.

### Do not

- Do not import NetworkX (or LangGraph, DSPy) from `src/atg`.
- Do not mutate a `TaskNode` field in place, and do not append to `inputs` after construction. `add_node` stores a deep copy; change status only through `transition`.
- Do not treat a `GraphSnapshot` as a live view of the graph. Rebuild with `to_graph()` if you need to edit.
- Do not reset `failed` nodes to `pending` in the executor.
- Do not claim this package proposes ATG. Credit Zhang et al. (2026).
- Do not add a dependency for a problem the stdlib graph already covers.
