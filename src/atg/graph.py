"""Stdlib DAG for Atomic Task Graph topology.

Implements concepts from Zhang et al. (2026), Atomic Task Graph, §4
(executable dependency graph). Independent reimplementation — see
docs/ATTRIBUTION.md and docs/citations.bib (zhang2026atg).

Decision 0005: no NetworkX (or equivalent) in core.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from atg.types import NodeStatus, TaskNode


class GraphError(ValueError):
    """Invalid graph mutation or query."""


class TaskGraph:
    """Directed acyclic task graph: nodes plus predecessor→successor edges."""

    def __init__(self) -> None:
        self._nodes: dict[str, TaskNode] = {}
        self._succ: dict[str, set[str]] = defaultdict(set)
        self._pred: dict[str, set[str]] = defaultdict(set)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def node_ids(self) -> list[str]:
        return list(self._nodes.keys())

    def nodes(self) -> list[TaskNode]:
        return [self._nodes[i] for i in self._nodes]

    def get(self, node_id: str) -> TaskNode:
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise GraphError(f"Unknown node {node_id!r}") from exc

    def add_node(self, node: TaskNode) -> TaskNode:
        if node.id in self._nodes:
            raise GraphError(f"Duplicate node id {node.id!r}")
        self._nodes[node.id] = node
        self._succ.setdefault(node.id, set())
        self._pred.setdefault(node.id, set())
        return node

    def add_edge(self, src: str, dst: str) -> None:
        if src not in self._nodes or dst not in self._nodes:
            raise GraphError(f"Edge {src!r} → {dst!r} references unknown node")
        if src == dst:
            raise GraphError(f"Self-loop on {src!r}")
        self._succ[src].add(dst)
        self._pred[dst].add(src)
        if self.has_cycle():
            self._succ[src].discard(dst)
            self._pred[dst].discard(src)
            raise GraphError(f"Edge {src!r} → {dst!r} would create a cycle")

    def remove_edge(self, src: str, dst: str) -> None:
        self._succ[src].discard(dst)
        self._pred[dst].discard(src)

    def successors(self, node_id: str) -> frozenset[str]:
        if node_id not in self._nodes:
            raise GraphError(f"Unknown node {node_id!r}")
        return frozenset(self._succ[node_id])

    def predecessors(self, node_id: str) -> frozenset[str]:
        if node_id not in self._nodes:
            raise GraphError(f"Unknown node {node_id!r}")
        return frozenset(self._pred[node_id])

    def edges(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for src, dests in self._succ.items():
            for dst in sorted(dests):
                out.append((src, dst))
        return out

    def has_cycle(self) -> bool:
        return self._topo() is None

    def is_acyclic(self) -> bool:
        return not self.has_cycle()

    def topological_order(self) -> list[str]:
        order = self._topo()
        if order is None:
            raise GraphError("Graph contains a cycle")
        return order

    def ready_set(self) -> list[str]:
        """Nodes whose predecessors are all ``done`` or ``frozen``.

        Paper §4.2: a node is executable when predecessors have completed.
        Used by the Phase 2 dynamic ready-queue (Decision 0011 / OQ-0007).
        """
        done_like = {NodeStatus.done, NodeStatus.frozen}
        ready: list[str] = []
        for nid, node in self._nodes.items():
            if node.status not in {NodeStatus.pending, NodeStatus.ready}:
                continue
            preds = self._pred[nid]
            if all(self._nodes[p].status in done_like for p in preds):
                ready.append(nid)
        return ready

    def freeze(self, node_id: str) -> TaskNode:
        node = self.get(node_id)
        if node.status not in {NodeStatus.done, NodeStatus.frozen}:
            raise GraphError(
                f"Cannot freeze {node_id!r} in status {node.status.value}"
            )
        node.status = NodeStatus.frozen
        return node

    def mark_status(self, node_id: str, status: NodeStatus) -> TaskNode:
        node = self.get(node_id)
        node.status = status
        return node

    def subgraph(self, node_ids: Iterable[str]) -> TaskGraph:
        keep = set(node_ids)
        unknown = keep - set(self._nodes)
        if unknown:
            raise GraphError(f"Unknown nodes in subgraph: {sorted(unknown)}")
        g = TaskGraph()
        for nid in self._nodes:
            if nid in keep:
                g.add_node(self._nodes[nid].model_copy(deep=True))
        for src, dst in self.edges():
            if src in keep and dst in keep:
                g.add_edge(src, dst)
        return g

    def copy(self) -> TaskGraph:
        return self.subgraph(self._nodes.keys())

    def to_dict(self) -> dict:
        return {
            "nodes": [n.model_dump(mode="json") for n in self.nodes()],
            "edges": [{"src": s, "dst": d} for s, d in self.edges()],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> TaskGraph:
        g = cls()
        for raw in payload.get("nodes", []):
            g.add_node(TaskNode.model_validate(raw))
        for edge in payload.get("edges", []):
            g.add_edge(edge["src"], edge["dst"])
        return g

    def _topo(self) -> list[str] | None:
        indeg = {nid: len(self._pred[nid]) for nid in self._nodes}
        queue = deque(nid for nid, d in indeg.items() if d == 0)
        order: list[str] = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for succ in self._succ[nid]:
                indeg[succ] -= 1
                if indeg[succ] == 0:
                    queue.append(succ)
        if len(order) != len(self._nodes):
            return None
        return order
