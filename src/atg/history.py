"""Full-graph snapshots for refinement and repair history.

Zhang et al. (2026), Atomic Task Graph, §4.1, record each intermediate
graph so later repair can trace how a node was refined. Decision 0009
stores an immutable full snapshot per step, not an event log. Independent
reimplementation; see docs/ATTRIBUTION.md (``zhang2026atg``).
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from atg.graph import TaskGraph
from atg.types import TaskNode


class GraphSnapshot(BaseModel):
    """One immutable copy of a task graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = Field(ge=1)
    reason: str = Field(min_length=1)
    created_at: str
    nodes: tuple[TaskNode, ...]
    edges: tuple[tuple[str, str], ...]

    def to_graph(self) -> TaskGraph:
        graph = TaskGraph()
        for node in self.nodes:
            graph.add_node(node)
        for src, dst in self.edges:
            graph.add_edge(src, dst)
        return graph


class GraphHistory:
    """Ordered list of full snapshots. Append-only."""

    def __init__(self) -> None:
        self._items: list[GraphSnapshot] = []

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> GraphSnapshot:
        return self._items[index]

    def append(self, graph: TaskGraph, reason: str) -> GraphSnapshot:
        if not reason.strip():
            raise ValueError("snapshot reason must be non-empty")
        snapshot = GraphSnapshot(
            version=len(self._items) + 1,
            reason=reason,
            created_at=datetime.now(timezone.utc).isoformat(),
            nodes=tuple(
                graph.get(node_id).model_copy(deep=True)
                for node_id in graph.topological_order()
            ),
            edges=graph.edges(),
        )
        self._items.append(snapshot)
        return snapshot

    def dump(self) -> list[dict]:
        return [item.model_dump(mode="json") for item in self._items]

    @classmethod
    def load(cls, payload: list[dict]) -> "GraphHistory":
        history = cls()
        for item in payload:
            history._items.append(GraphSnapshot.model_validate(item))
        return history
