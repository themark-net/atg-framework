"""Interface-preserving recursive compilation.

Zhang et al. (2026), Atomic Task Graph, §4.1. The model emits a
``Decomposition`` JSON object (Decision 0012). Depth cap is 6
(Decision 0007). Independent reimplementation; see
docs/ATTRIBUTION.md (``zhang2026atg``).
"""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from atg.graph import GraphError, TaskGraph
from atg.history import GraphHistory
from atg.tools import ToolRegistry, is_atomic
from atg.types import TaskNode
from atg.validation import InterfaceError, assert_interface_preserved

_SYSTEM = (
    "Compile this one task node into a small DAG of tool calls. "
    "Return only JSON matching the schema. "
    "Use tool_name values from the tool list. "
    "A node with a tool_name must set refine to false. "
    "Input values are literals or {\"$ref\": \"node_id.outputs.field\"}. "
    "Every $ref on the parent must appear on some child. "
    "Do not invent external $refs the parent does not have. "
    "Sink declared_outputs must include every parent declared output. "
    "Copy those output names onto every sink. "
    "Edges connect child ids only. Do not use the parent id as a node or an edge endpoint. "
    "Independent steps must be sibling nodes, not a chain."
)


class CompileError(Exception):
    """Compilation stopped without an all-atomic graph."""


class ChildNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    tool_name: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    declared_outputs: list[str] = Field(default_factory=list)
    refine: bool = True


class EdgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str
    dst: str


class Decomposition(BaseModel):
    """One refinement of a single parent node."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[ChildNode]
    edges: list[EdgeSpec] = Field(default_factory=list)


def compile_task(
    root: TaskNode,
    registry: ToolRegistry,
    llm: Any,
    *,
    max_depth: int = 6,
) -> tuple[TaskGraph, GraphHistory]:
    graph = TaskGraph()
    graph.add_node(root)
    history = GraphHistory()
    history.append(graph, "initial")
    for step in range(max_depth):
        pending = [
            node_id
            for node_id in graph.topological_order()
            if not is_atomic(graph.get(node_id), registry)
        ]
        if not pending:
            return graph, history
        for node_id in pending:
            if node_id not in graph or is_atomic(graph.get(node_id), registry):
                continue
            parent = graph.get(node_id)
            spec = llm.complete_structured(_messages(parent, registry), Decomposition)
            subgraph = _decomposition_graph(spec, parent)
            try:
                assert_interface_preserved(parent, subgraph)
                graph.replace_node(node_id, subgraph)
            except (InterfaceError, GraphError) as exc:
                raise CompileError(f"{exc}; decomposition={spec.model_dump()}") from exc
        history.append(graph, f"refine-{step + 1}")
    left = [
        node_id
        for node_id in graph.node_ids()
        if not is_atomic(graph.get(node_id), registry)
    ]
    if left:
        raise CompileError(f"depth cap {max_depth} with non-atomic nodes: {left}")
    return graph, history


def _messages(
    node: TaskNode,
    registry: ToolRegistry,
    *,
    note: str | None = None,
) -> list[dict]:
    payload: dict = {
        "node": {
            "id": node.id,
            "name": node.name,
            "inputs": node.inputs,
            "declared_outputs": node.declared_outputs,
        },
        "tools": registry.as_openai_tools(),
    }
    if note:
        payload["note"] = note
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": json.dumps(payload)},
    ]


def _decomposition_graph(spec: Decomposition, parent: TaskNode) -> TaskGraph:
    graph = TaskGraph()
    for child in spec.nodes:
        try:
            node = TaskNode(
                id=child.id,
                name=child.name,
                tool_name=child.tool_name,
                inputs=dict(child.inputs),
                declared_outputs=list(child.declared_outputs),
                refine=child.refine,
                parent_id=parent.id,
            )
        except ValidationError as exc:
            raise CompileError(
                f"decomposition node {child.id!r} is not a valid task node: {exc}"
            ) from exc
        graph.add_node(node)
    known = {child.id for child in spec.nodes}
    for edge in spec.edges:
        if edge.src not in known or edge.dst not in known:
            continue
        graph.add_edge(edge.src, edge.dst)
    return graph
