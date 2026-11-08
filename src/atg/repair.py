"""Minimal subgraph repair from refinement lineage.

Zhang et al. (2026), Atomic Task Graph, §4.3. The failed nodes' lowest
common historical ancestor bounds the repair (Decision 0014). Nodes
outside that region that already succeeded are frozen and are not
reset. Independent reimplementation; see docs/ATTRIBUTION.md
(``zhang2026atg``).
"""

from typing import Any

from atg.graph import GraphError, TaskGraph
from atg.history import GraphHistory
from atg.metrics import Metrics
from atg.planner import DEFAULT_COMPILE_ATTEMPTS, CompileError, propose_subgraph
from atg.tools import ToolRegistry
from atg.types import NodeStatus, TaskNode, parse_ref


class RepairError(Exception):
    """Repair could not produce a graph that preserves the broken region."""

    def __init__(self, message: str, *, compile_retries: int = 0) -> None:
        super().__init__(message)
        self.compile_retries = compile_retries


def lineage(node_id: str, graph: TaskGraph, history: GraphHistory) -> list[str]:
    """``node_id`` then each ``parent_id``, newest snapshot filling gaps."""

    chain: list[str] = []
    current: str | None = node_id
    seen: set[str] = set()
    while current and current not in seen:
        chain.append(current)
        seen.add(current)
        current = _parent(current, graph, history)
    return chain


def lowest_common_ancestor(
    failed: list[str],
    graph: TaskGraph,
    history: GraphHistory,
) -> str | None:
    if not failed:
        return None
    chains = [lineage(node_id, graph, history) for node_id in failed]
    common = set(chains[0])
    for chain in chains[1:]:
        common &= set(chain)
    if not common:
        return None
    return min(common, key=lambda name: max(chain.index(name) for chain in chains))


def repair_region(failed: list[str], graph: TaskGraph, history: GraphHistory) -> set[str]:
    anchor = lowest_common_ancestor(failed, graph, history)
    if anchor is None:
        seeds = set(failed)
    else:
        seeds = {
            node_id
            for node_id in graph.node_ids()
            if anchor in lineage(node_id, graph, history)
        }
        if not seeds:
            seeds = set(failed)
    region = set(seeds)
    changed = True
    while changed:
        changed = False
        for node_id in graph.node_ids():
            if node_id in region:
                continue
            if any(pred in region for pred in graph.predecessors(node_id)):
                region.add(node_id)
                changed = True
    return region


def repair_graph(
    graph: TaskGraph,
    history: GraphHistory,
    failed: list[str],
    registry: ToolRegistry,
    llm: Any,
    *,
    metrics: Metrics | None = None,
    max_compile_attempts: int = DEFAULT_COMPILE_ATTEMPTS,
) -> TaskGraph:
    """Copy, freeze successes outside the region, replace the region, snapshot."""

    if not failed:
        raise RepairError("no failed nodes")
    working = graph.copy()
    region = repair_region(failed, working, history)
    for node_id in list(working.node_ids()):
        if node_id in region:
            continue
        if working.get(node_id).status == NodeStatus.done:
            working.freeze(node_id)
    interface = _region_interface(working, region, failed, history)
    incoming, outgoing = _boundary(working, region)
    failures = [
        f"{node_id}: {working.get(node_id).error}"
        for node_id in failed
        if node_id in working and working.get(node_id).error
    ]
    for node_id in list(region):
        if node_id in working:
            working.remove_node(node_id)
    note = _repair_note(history, interface, failures)
    try:
        subgraph = propose_subgraph(
            interface,
            registry,
            llm,
            note=note,
            repair=True,
            metrics=metrics,
            max_attempts=max_compile_attempts,
        )
    except CompileError as exc:
        raise RepairError(str(exc), compile_retries=exc.compile_retries) from exc
    _insert(working, subgraph, incoming, outgoing)
    history.append(working, "repair")
    return working


def _repair_note(history: GraphHistory, interface: TaskNode, failures: list[str]) -> str:
    """Task sentence plus the parent ``$ref`` strings the replacement must copy.

    The sentence is the caller's original task, from the first snapshot.
    It is not a field from Zhang et al. The ``$ref`` strings are not rewritten.
    """

    parts = ["This is a repair. Preserve the external interface."]
    sentence = _original_task(history)
    if sentence:
        parts.append("The original task is: " + sentence)
    refs = _interface_refs(interface)
    if refs:
        producers: list[str] = []
        for ref in refs:
            producer = ref.split(".outputs.", 1)[0]
            if producer not in producers:
                producers.append(producer)
        parts.append(
            "Copy these $ref strings onto child inputs, unchanged: "
            + ", ".join(refs)
            + ". Do not create a child whose id is one of these producers: "
            + ", ".join(producers)
            + ". A parent $ref does not get an edge."
        )
    parts.append("Never emit an edge whose src and dst are the same id.")
    if failures:
        parts.append("Previous failures: " + "; ".join(failures))
    return " ".join(parts)


def _original_task(history: GraphHistory) -> str | None:
    if len(history) == 0:
        return None
    first = history[0]
    if first.reason != "initial" or len(first.nodes) != 1:
        return None
    name = first.nodes[0].name.strip()
    return name or None


def _interface_refs(node: TaskNode) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for value in node.inputs.values():
        parsed = parse_ref(value)
        if parsed is None:
            continue
        text = f"{parsed.node_id}.outputs.{parsed.field}"
        if text not in seen:
            seen.add(text)
            found.append(text)
    return found


def _parent(node_id: str, graph: TaskGraph, history: GraphHistory) -> str | None:
    if node_id in graph:
        return graph.get(node_id).parent_id
    for index in range(len(history) - 1, -1, -1):
        for node in history[index].nodes:
            if node.id == node_id:
                return node.parent_id
    return None


def _region_interface(
    graph: TaskGraph,
    region: set[str],
    failed: list[str],
    history: GraphHistory,
) -> TaskNode:
    anchor = lowest_common_ancestor(failed, graph, history) or failed[0]
    inputs: dict = {}
    declared: list[str] = []
    for node_id in sorted(region):
        node = graph.get(node_id)
        for key, value in node.inputs.items():
            ref = parse_ref(value)
            if ref is not None and ref.node_id in region:
                continue
            inputs.setdefault(key, value)
        if any(succ in region for succ in graph.successors(node_id)):
            continue
        for name in node.declared_outputs:
            if name not in declared:
                declared.append(name)
    return TaskNode(
        id=anchor,
        name=anchor,
        inputs=inputs,
        declared_outputs=declared,
        refine=True,
    )


def _boundary(graph: TaskGraph, region: set[str]) -> tuple[list[str], list[str]]:
    incoming: list[str] = []
    outgoing: list[str] = []
    for node_id in region:
        for pred in graph.predecessors(node_id):
            if pred not in region and pred not in incoming:
                incoming.append(pred)
        for succ in graph.successors(node_id):
            if succ not in region and succ not in outgoing:
                outgoing.append(succ)
    return incoming, outgoing


def _insert(
    graph: TaskGraph,
    subgraph: TaskGraph,
    incoming: list[str],
    outgoing: list[str],
) -> None:
    for node_id in subgraph.node_ids():
        graph.add_node(subgraph.get(node_id))
    for src, dst in subgraph.edges():
        graph.add_edge(src, dst)
    sources = [node_id for node_id in subgraph.node_ids() if not subgraph.predecessors(node_id)]
    sinks = [node_id for node_id in subgraph.node_ids() if not subgraph.successors(node_id)]
    try:
        for pred in incoming:
            for source in sources:
                graph.add_edge(pred, source)
        for sink in sinks:
            for succ in outgoing:
                graph.add_edge(sink, succ)
    except GraphError as exc:
        raise RepairError(str(exc)) from exc
