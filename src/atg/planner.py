"""Interface-preserving recursive graph compilation.

Implements concepts from Zhang et al. (2026), Atomic Task Graph, §4.1
(coarse task → recursive refinement of non-atomic nodes into subgraphs that
preserve the parent's external I/O interface, recording every intermediate
graph). See docs/ATTRIBUTION.md and docs/citations.bib (zhang2026atg). This is
an independent reimplementation, not official code.

Engineering contracts: Decision 0007 (atomicity, ``refine=False``, ``$ref``
inputs, depth cap 6), Decision 0009 (snapshot after each refine step),
Decision 0012 (structured JSON decomposition via ``LLMClient``).

Decomposition mini-language (what the LLM returns, see ``Decomposition``):

* child ``inputs`` values are literals, ``{"$ref": "<sibling_id>.outputs.<field>"}``
  for a sibling in the same decomposition, or ``{"$parent": "<input_name>"}``
  to inherit the parent's input binding (this is how the input interface is
  preserved);
* ``output_bindings`` maps **every** parent output field to
  ``"<sibling_id>.outputs.<field>"`` (this is how the output interface is
  preserved). Downstream consumers of the parent are rewired automatically.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from atg.graph import GraphError, TaskGraph
from atg.history import GraphHistory
from atg.llm import LLMClient, Messages
from atg.tools import ToolRegistry, parse_input_value
from atg.types import InputRef, TaskNode, TaskSpec

PARENT_KEY = "$parent"


class PlanError(ValueError):
    """Decomposition violated an interface, atomicity, or depth invariant."""


class PlannedNode(BaseModel):
    """One child node proposed by the planner LLM."""

    id: str = Field(description="Short unique id within this decomposition")
    name: str = Field(default="", description="Human-readable subtask name")
    tool_name: str | None = Field(
        default=None,
        description="Registered tool name for an atomic node; null for an abstract subtask",
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description='Literals, {"$ref": "sibling.outputs.field"}, or {"$parent": "input_name"}',
    )
    output_keys: list[str] = Field(
        default_factory=list,
        description="Output field names this node exposes (required for abstract nodes)",
    )
    refine: bool = Field(default=True, description="False forbids further refinement")


class Decomposition(BaseModel):
    """Structured planner output: a subgraph replacing one non-atomic node."""

    nodes: list[PlannedNode]
    edges: list[list[str]] = Field(
        default_factory=list,
        description="Optional ordering-only dependencies as [src_id, dst_id]",
    )
    output_bindings: dict[str, str] = Field(
        default_factory=dict,
        description='Parent output field -> "sibling.outputs.field"; must cover every parent output',
    )
    rationale: str = ""


class ExpansionRecord(BaseModel):
    """Lineage + interface bookkeeping for every node the planner ever created.

    Kept even after a node is replaced by its refinement so repair can walk
    history (paper §4.3) and re-abstract a region with its original interface.
    ``inputs`` and ``bindings`` are kept *current*: whenever a node is
    refined, refs pointing at it are rewritten everywhere, including here.
    """

    node_id: str
    name: str
    tool_name: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_keys: list[str] = Field(default_factory=list)
    depth: int = 0
    parent_id: str | None = None
    bindings: dict[str, str] = Field(default_factory=dict)


class CompiledPlan:
    """Mutable compile/execute/repair state: graph + history + lineage."""

    def __init__(self, spec: TaskSpec, root_id: str = "root") -> None:
        self.spec = spec
        self.root_id = root_id
        self.graph = TaskGraph()
        self.history = GraphHistory()
        self.records: dict[str, ExpansionRecord] = {}
        self.output_bindings: dict[str, str] = {}
        self.repair_log: list[dict[str, Any]] = []

    # ----- lineage -----------------------------------------------------

    def lineage(self, node_id: str) -> list[str]:
        """``[node_id, parent, grandparent, ..., root]`` using expansion records."""
        chain: list[str] = []
        current: str | None = node_id
        seen: set[str] = set()
        while current is not None and current not in seen:
            seen.add(current)
            chain.append(current)
            rec = self.records.get(current)
            current = rec.parent_id if rec else None
        return chain

    def region(self, ancestor_id: str) -> set[str]:
        """Current graph nodes derived from ``ancestor_id`` (inclusive)."""
        return {nid for nid in self.graph.node_ids() if ancestor_id in self.lineage(nid)}

    # ----- atomicity ---------------------------------------------------

    def non_atomic_ids(self, registry: ToolRegistry) -> list[str]:
        names = registry.names()
        return [
            nid
            for nid in self.graph.topological_order()
            if not self.graph.get(nid).is_atomic(names)
        ]

    def is_atomic(self, registry: ToolRegistry) -> bool:
        return not self.non_atomic_ids(registry)

    # ----- outputs -----------------------------------------------------

    def task_outputs(self, strict: bool = False) -> dict[str, Any]:
        """Resolve the task's external outputs against executed node outputs."""
        upstream = {n.id: n.outputs for n in self.graph.nodes() if n.outputs is not None}
        result: dict[str, Any] = {}
        for field, ref in self.output_bindings.items():
            node_id, out_field = InputRef(ref=ref).parse()
            outputs = upstream.get(node_id)
            if outputs is None or out_field not in outputs:
                if strict:
                    raise PlanError(f"Task output {field!r} unresolved ({ref})")
                result[field] = None
            else:
                result[field] = outputs[out_field]
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": self.spec.model_dump(mode="json"),
            "root_id": self.root_id,
            "graph": self.graph.to_dict(),
            "output_bindings": dict(self.output_bindings),
            "records": {k: v.model_dump(mode="json") for k, v in self.records.items()},
            "history": [s.model_dump(mode="json") for s in self.history.snapshots()],
            "repair_log": list(self.repair_log),
        }


class Planner:
    """Recursive compiler: refine non-atomic nodes until every node is atomic."""

    def __init__(self, registry: ToolRegistry, llm: LLMClient, max_depth: int = 6) -> None:
        self.registry = registry
        self.llm = llm
        self.max_depth = max_depth

    # ----- public API --------------------------------------------------

    def compile(self, spec: TaskSpec, *, root_id: str = "root") -> CompiledPlan:
        """Create the coarse root graph and refine until atomic."""
        plan = self.initial_plan(spec, root_id=root_id)
        self.refine_until_atomic(plan)
        return plan

    def initial_plan(self, spec: TaskSpec, *, root_id: str = "root") -> CompiledPlan:
        """Coarse graph: one abstract node carrying the task's I/O interface."""
        plan = CompiledPlan(spec, root_id=root_id)
        output_keys = list(spec.outputs) or ["result"]
        root = TaskNode(
            id=root_id,
            name=spec.description,
            inputs=dict(spec.inputs),
            output_keys=output_keys,
            metadata={"depth": 0},
        )
        plan.graph.add_node(root)
        plan.records[root_id] = ExpansionRecord(
            node_id=root_id,
            name=root.name,
            inputs=dict(root.inputs),
            output_keys=output_keys,
            depth=0,
        )
        plan.output_bindings = {f: f"{root_id}.outputs.{f}" for f in output_keys}
        plan.history.record(plan.graph, reason="initial")
        return plan

    def refine_until_atomic(
        self,
        plan: CompiledPlan,
        *,
        only_under: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> int:
        """Refine every non-atomic node (optionally only descendants of one ancestor)."""
        refinements = 0
        while True:
            pending = [
                nid
                for nid in plan.non_atomic_ids(self.registry)
                if only_under is None or only_under in plan.lineage(nid)
            ]
            if not pending:
                return refinements
            for nid in pending:
                self.refine_node(plan, nid, context=context)
                refinements += 1

    def refine_node(
        self,
        plan: CompiledPlan,
        node_id: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Ask the LLM for a decomposition of one node and splice it in."""
        node = plan.graph.get(node_id)
        if node.depth + 1 > self.max_depth:
            raise PlanError(
                f"Node {node_id!r} at depth {node.depth} cannot be refined: "
                f"max_depth={self.max_depth} reached without reaching atomic tools "
                f"(lineage {plan.lineage(node_id)})"
            )
        llm_context = {
            "node_id": node_id,
            "depth": node.depth,
            "reason": "refine",
            **(context or {}),
        }
        decomposition = self.llm.complete_structured(
            self.build_messages(plan, node, llm_context),
            Decomposition,
            context=llm_context,
        )
        return self.splice(
            plan, node_id, decomposition, reason=f"{llm_context['reason']}:{node_id}"
        )

    # ----- splice (pure graph surgery; no LLM) -------------------------

    def splice(
        self,
        plan: CompiledPlan,
        parent_id: str,
        decomposition: Decomposition,
        *,
        reason: str | None = None,
    ) -> list[str]:
        """Replace ``parent_id`` with the decomposition, preserving its interface."""
        graph = plan.graph
        parent = graph.get(parent_id)
        names = self.registry.names()
        if parent.is_atomic(names):
            raise PlanError(f"Node {parent_id!r} is atomic and must not be refined")
        if not decomposition.nodes:
            raise PlanError(f"Empty decomposition for {parent_id!r}")
        depth = parent.depth + 1
        if depth > self.max_depth:
            raise PlanError(f"Refining {parent_id!r} exceeds max_depth={self.max_depth}")

        local_ids = [n.id for n in decomposition.nodes]
        if len(set(local_ids)) != len(local_ids):
            raise PlanError(f"Duplicate child ids in decomposition of {parent_id!r}")
        existing = set(graph.node_ids())
        id_map: dict[str, str] = {}
        for local in local_ids:
            global_id = local if local not in existing else f"{parent_id}/{local}"
            if global_id in existing or global_id in id_map.values():
                raise PlanError(f"Child id {local!r} clashes with existing node")
            id_map[local] = global_id

        children: list[TaskNode] = []
        for planned in decomposition.nodes:
            if planned.tool_name is not None and planned.tool_name not in names:
                raise PlanError(
                    f"Child {planned.id!r} of {parent_id!r} uses unknown tool "
                    f"{planned.tool_name!r}"
                )
            inputs = {
                key: _resolve_child_input(value, parent, id_map, parent_id)
                for key, value in planned.inputs.items()
            }
            refine = planned.refine
            output_keys = list(planned.output_keys)
            if planned.tool_name is not None:
                spec = self.registry.get(planned.tool_name)
                refine = refine and spec.refine
                if not output_keys:
                    output_keys = spec.output_keys() or []
            elif not output_keys:
                raise PlanError(
                    f"Abstract child {planned.id!r} of {parent_id!r} must declare output_keys"
                )
            children.append(
                TaskNode(
                    id=id_map[planned.id],
                    name=planned.name or planned.id,
                    tool_name=planned.tool_name,
                    inputs=inputs,
                    output_keys=output_keys,
                    parent_id=parent_id,
                    refine=refine,
                    metadata={"depth": depth},
                )
            )
        by_id = {c.id: c for c in children}

        expected = set(parent.output_keys)
        provided = set(decomposition.output_bindings)
        if expected != provided:
            raise PlanError(
                f"Interface not preserved for {parent_id!r}: expected outputs "
                f"{sorted(expected)}, bindings cover {sorted(provided)}"
            )
        bindings: dict[str, str] = {}
        for field, ref in decomposition.output_bindings.items():
            local, out_field = _parse_ref_string(ref, f"output binding {field!r}")
            if local not in id_map:
                raise PlanError(f"Output binding {field!r} targets non-child {local!r}")
            child = by_id[id_map[local]]
            if child.output_keys and out_field not in child.output_keys:
                raise PlanError(
                    f"Output binding {field!r} -> {ref!r}: child {child.id!r} does not "
                    f"expose {out_field!r} (has {child.output_keys})"
                )
            bindings[field] = f"{child.id}.outputs.{out_field}"

        # Mutate a copy so a cycle / bad edge leaves the plan untouched.
        work = graph.copy()
        ext_preds = set(work.predecessors(parent_id))
        ext_succs = set(work.successors(parent_id))
        work.remove_node(parent_id)
        for child in children:
            work.add_node(child)
        try:
            for child in children:
                for src_id, _field in refs_in(child.inputs):
                    if src_id in work:
                        work.add_edge(src_id, child.id)
            for edge in decomposition.edges:
                if len(edge) != 2 or edge[0] not in id_map or edge[1] not in id_map:
                    raise PlanError(f"Bad ordering edge {edge!r} in decomposition of {parent_id!r}")
                work.add_edge(id_map[edge[0]], id_map[edge[1]])
        except GraphError as exc:
            raise PlanError(f"Decomposition of {parent_id!r} is not a DAG: {exc}") from exc

        child_ids = {c.id for c in children}
        entry = [c.id for c in children if not (work.predecessors(c.id) & child_ids)]
        exit_ = [c.id for c in children if not (work.successors(c.id) & child_ids)]
        for pred in ext_preds:
            for cid in entry:
                work.add_edge(pred, cid)
        for succ in ext_succs:
            for cid in exit_:
                work.add_edge(cid, succ)

        # Rewire everything that consumed the parent's outputs.
        mapping = {(parent_id, field): ref for field, ref in bindings.items()}
        for node in work.nodes():
            node.inputs = rewrite_refs(node.inputs, mapping)
        for rec in plan.records.values():
            rec.inputs = rewrite_refs(rec.inputs, mapping)
            rec.bindings = {
                f: rewrite_ref_string(r, mapping) for f, r in rec.bindings.items()
            }
        plan.output_bindings = {
            f: rewrite_ref_string(r, mapping) for f, r in plan.output_bindings.items()
        }

        plan.graph = work
        parent_rec = plan.records.get(parent_id)
        if parent_rec is None:
            parent_rec = ExpansionRecord(
                node_id=parent_id,
                name=parent.name,
                inputs=dict(parent.inputs),
                output_keys=list(parent.output_keys),
                depth=parent.depth,
                parent_id=parent.parent_id,
            )
            plan.records[parent_id] = parent_rec
        parent_rec.bindings = bindings
        for child in children:
            plan.records[child.id] = ExpansionRecord(
                node_id=child.id,
                name=child.name,
                tool_name=child.tool_name,
                inputs=dict(child.inputs),
                output_keys=list(child.output_keys),
                depth=depth,
                parent_id=parent_id,
            )
        plan.history.record(plan.graph, reason=reason or f"refine:{parent_id}")
        return [c.id for c in children]

    # ----- prompt ------------------------------------------------------

    def build_messages(
        self, plan: CompiledPlan, node: TaskNode, context: dict[str, Any]
    ) -> Messages:
        tools = []
        for spec in (self.registry.get(n) for n in sorted(self.registry.names())):
            entry: dict[str, Any] = spec.openai_schema()["function"]
            if spec.returns:
                entry["returns"] = spec.returns
            if not spec.refine:
                entry["refine"] = False
            tools.append(entry)
        request = {
            "task": plan.spec.description,
            "task_outputs": plan.spec.outputs,
            "node_to_refine": {
                "id": node.id,
                "name": node.name,
                "inputs": node.inputs,
                "output_keys": node.output_keys,
                "depth": node.depth,
                "max_depth": self.max_depth,
            },
            "existing_node_ids": plan.graph.node_ids(),
            "tools": tools,
        }
        failure = context.get("failure")
        if failure:
            request["previous_failure"] = failure
        system = (
            "You compile one subtask of an Atomic Task Graph into a small DAG of "
            "child nodes. Rules: (1) an atomic child sets tool_name to a listed tool "
            "and passes its parameters as inputs; (2) an abstract child sets tool_name "
            "to null and declares output_keys so it can be refined later; (3) input "
            'values are literals, {"$parent": "<input>"} to reuse an input of the node '
            'being refined, or {"$ref": "<child_id>.outputs.<field>"} for a sibling '
            "output; (4) output_bindings must map EVERY output key of the node being "
            "refined to a child output; (5) keep independent children independent so "
            "they can run in parallel; (6) never use tools marked refine=false as "
            "anything but a single atomic node."
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(request, indent=2, default=str)},
        ]


# ----- helpers -----------------------------------------------------------


def _parse_ref_string(ref: str, what: str) -> tuple[str, str]:
    try:
        return InputRef(ref=ref).parse()
    except ValueError as exc:
        raise PlanError(f"{what}: {exc}") from exc


def _resolve_child_input(
    value: Any, parent: TaskNode, id_map: dict[str, str], parent_id: str
) -> Any:
    if isinstance(value, dict):
        if PARENT_KEY in value:
            name = value[PARENT_KEY]
            if name not in parent.inputs:
                raise PlanError(
                    f"Child of {parent_id!r} inherits unknown parent input {name!r} "
                    f"(parent has {sorted(parent.inputs)})"
                )
            return parent.inputs[name]
        if "$ref" in value:
            local, field = _parse_ref_string(str(value["$ref"]), f"child input of {parent_id!r}")
            if local not in id_map:
                raise PlanError(
                    f"Child of {parent_id!r} references {local!r}, which is not a sibling "
                    f"in this decomposition (use {PARENT_KEY} for inherited inputs)"
                )
            return {"$ref": f"{id_map[local]}.outputs.{field}"}
        return {k: _resolve_child_input(v, parent, id_map, parent_id) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_child_input(v, parent, id_map, parent_id) for v in value]
    return value


def refs_in(value: Any) -> list[tuple[str, str]]:
    """All ``(node_id, field)`` refs nested anywhere inside an inputs value."""
    found: list[tuple[str, str]] = []
    parsed = parse_input_value(value)
    if isinstance(parsed, InputRef):
        found.append(parsed.parse())
    elif isinstance(value, dict):
        for v in value.values():
            found.extend(refs_in(v))
    elif isinstance(value, list):
        for v in value:
            found.extend(refs_in(v))
    return found


def rewrite_ref_string(ref: str, mapping: dict[tuple[str, str], str]) -> str:
    try:
        key = InputRef(ref=ref).parse()
    except ValueError:
        return ref
    return mapping.get(key, ref)


def rewrite_refs(value: Any, mapping: dict[tuple[str, str], str]) -> Any:
    parsed = parse_input_value(value)
    if isinstance(parsed, InputRef):
        return {"$ref": rewrite_ref_string(parsed.ref, mapping)}
    if isinstance(value, dict):
        return {k: rewrite_refs(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [rewrite_refs(v, mapping) for v in value]
    return value

