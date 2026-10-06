"""Stdlib task DAG: topology, ready-set, freeze, and status transitions.

Graph storage is stdlib dicts (Decision 0005). Readiness and the status
vocabulary follow Zhang et al. (2026), Atomic Task Graph, §4.2
(Dependency-Aware Execution) and Decision 0011. Independent
reimplementation; see docs/ATTRIBUTION.md (``zhang2026atg``).
"""

from atg.types import NodeStatus, TaskNode

_ALLOWED: dict[NodeStatus, frozenset[NodeStatus]] = {
    NodeStatus.pending: frozenset({NodeStatus.ready}),
    NodeStatus.ready: frozenset({NodeStatus.running}),
    NodeStatus.running: frozenset({NodeStatus.done, NodeStatus.failed}),
    NodeStatus.done: frozenset({NodeStatus.frozen}),
    NodeStatus.failed: frozenset(),
    NodeStatus.frozen: frozenset(),
}

_FINISHED = frozenset({NodeStatus.done, NodeStatus.frozen})


class GraphError(Exception):
    """Illegal graph edit or status transition."""


class CycleError(GraphError):
    """The DAG would contain a cycle. ``nodes`` are the unvisited ids."""

    def __init__(self, nodes: list[str]) -> None:
        self.nodes = list(nodes)
        listed = ", ".join(self.nodes) if self.nodes else "(unknown)"
        super().__init__(f"cycle involving: {listed}")


class TaskGraph:
    """Directed acyclic task graph. Edges point from producer to consumer."""

    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}
        self._succ: dict[str, list[str]] = {}
        self._pred: dict[str, list[str]] = {}

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node_ids(self) -> list[str]:
        return list(self._nodes)

    def get(self, node_id: str) -> TaskNode:
        try:
            return self._nodes[node_id]
        except KeyError:
            raise GraphError(f"unknown node {node_id}") from None

    def add_node(self, node: TaskNode) -> TaskNode:
        if node.id in self._nodes:
            raise GraphError(f"duplicate node {node.id}")
        owned = node.model_copy(deep=True)
        self._nodes[node.id] = owned
        self._succ[node.id] = []
        self._pred[node.id] = []
        return owned

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._nodes or dst not in self._nodes:
            raise GraphError(f"missing endpoint for edge {src} -> {dst}")
        if src == dst:
            raise CycleError([src])
        if dst in self._succ[src]:
            raise GraphError(f"duplicate edge {src} -> {dst}")
        self._succ[src].append(dst)
        self._pred[dst].append(src)
        try:
            self.topological_order()
        except CycleError:
            self._succ[src].pop()
            self._pred[dst].pop()
            raise

    def predecessors(self, node_id: str) -> tuple[str, ...]:
        self._require(node_id)
        return tuple(self._pred[node_id])

    def successors(self, node_id: str) -> tuple[str, ...]:
        self._require(node_id)
        return tuple(self._succ[node_id])

    def edges(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (src, dst) for src, dsts in self._succ.items() for dst in dsts
        )

    def ancestors(self, node_id: str) -> set[str]:
        self._require(node_id)
        seen: set[str] = set()
        stack = list(self._pred[node_id])
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self._pred[current])
        return seen

    def topological_order(self) -> list[str]:
        """Kahn order. Frontiers are sorted by id so the result is stable."""

        indegree = {node_id: len(self._pred[node_id]) for node_id in self._nodes}
        ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
        ordered: list[str] = []
        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for succ in self._succ[current]:
                indegree[succ] -= 1
                if indegree[succ] == 0:
                    ready.append(succ)
            ready.sort()
        if len(ordered) != len(self._nodes):
            left = sorted(set(self._nodes) - set(ordered))
            raise CycleError(left)
        return ordered

    def ready_ids(self) -> list[str]:
        """Pending or ready nodes whose predecessors are done or frozen.

        Order follows ``topological_order``. Decision 0011.
        """

        found: list[str] = []
        for node_id in self.topological_order():
            node = self._nodes[node_id]
            if node.status not in (NodeStatus.pending, NodeStatus.ready):
                continue
            preds_done = all(
                self._nodes[pred].status in _FINISHED for pred in self._pred[node_id]
            )
            if preds_done:
                found.append(node_id)
        return found

    def mark_ready(self) -> list[str]:
        """Move qualifying ``pending`` nodes to ``ready``. Return the ready set."""

        ids = self.ready_ids()
        for node_id in ids:
            if self._nodes[node_id].status == NodeStatus.pending:
                self.transition(node_id, NodeStatus.ready)
        return ids

    def transition(
        self,
        node_id: str,
        status: NodeStatus,
        *,
        error: str | None = None,
        outputs: dict | None = None,
    ) -> TaskNode:
        node = self.get(node_id)
        if status not in _ALLOWED[node.status]:
            raise GraphError(f"{node_id}: {node.status.value} -> {status.value} is not allowed")
        if status == NodeStatus.failed and not error:
            raise GraphError("failed transition requires error")
        updates: dict = {"status": status}
        if error is not None:
            updates["error"] = error
        if outputs is not None:
            updates["outputs"] = outputs
        updated = node.model_copy(update=updates)
        self._nodes[node_id] = updated
        return updated

    def freeze(self, node_id: str) -> TaskNode:
        """Mark a ``done`` node ``frozen`` so dependents can reuse it."""

        return self.transition(node_id, NodeStatus.frozen)

    def subgraph(self, node_ids: set[str]) -> "TaskGraph":
        """Induced subgraph. Copies nodes. Does not invent transitive edges."""

        missing = node_ids - self._nodes.keys()
        if missing:
            listed = ", ".join(sorted(missing))
            raise GraphError(f"unknown node {listed}")
        extracted = TaskGraph()
        for node_id in sorted(node_ids):
            extracted.add_node(self._nodes[node_id])
        for src, dst in self.edges():
            if src in node_ids and dst in node_ids:
                extracted.add_edge(src, dst)
        return extracted

    def copy(self) -> "TaskGraph":
        return self.subgraph(set(self._nodes))

    def remove_node(self, node_id: str) -> None:
        self._require(node_id)
        for pred in list(self._pred[node_id]):
            self._succ[pred].remove(node_id)
        for succ in list(self._succ[node_id]):
            self._pred[succ].remove(node_id)
        del self._nodes[node_id]
        del self._succ[node_id]
        del self._pred[node_id]

    def replace_node(self, node_id: str, subgraph: "TaskGraph") -> None:
        """Swap ``node_id`` for an induced replacement. Boundary edges reattach.

        Incoming edges attach to every in-subgraph source. Outgoing edges
        leave from every in-subgraph sink. Decision 0007 interface swap.
        """

        self._require(node_id)
        if len(subgraph) == 0:
            raise GraphError("replacement subgraph is empty")
        overlap = set(subgraph.node_ids()) & (set(self._nodes) - {node_id})
        if overlap:
            raise GraphError(f"replacement ids already exist: {sorted(overlap)}")
        preds = self.predecessors(node_id)
        succs = self.successors(node_id)
        sources = [nid for nid in subgraph.node_ids() if not subgraph.predecessors(nid)]
        sinks = [nid for nid in subgraph.node_ids() if not subgraph.successors(nid)]
        self.remove_node(node_id)
        for nid in subgraph.node_ids():
            self.add_node(subgraph.get(nid))
        for src, dst in subgraph.edges():
            self.add_edge(src, dst)
        for pred in preds:
            for source in sources:
                self.add_edge(pred, source)
        for sink in sinks:
            for succ in succs:
                self.add_edge(sink, succ)

    def reset_for_repair(self, node_id: str) -> TaskNode:
        """Return a non-frozen node to ``pending`` and clear output and error.

        ``transition`` does not allow this move (Decision 0011). Repair is the
        only caller (Decision 0014). Frozen nodes stay frozen.
        """

        node = self.get(node_id)
        if node.status == NodeStatus.frozen:
            raise GraphError("frozen nodes cannot be reset")
        if node.status == NodeStatus.running:
            raise GraphError("running nodes cannot be reset")
        if node.status == NodeStatus.pending:
            return node
        updated = node.model_copy(
            update={"status": NodeStatus.pending, "outputs": None, "error": None}
        )
        self._nodes[node_id] = updated
        return updated

    def _require(self, node_id: str) -> None:
        if node_id not in self._nodes:
            raise GraphError(f"unknown node {node_id}")
