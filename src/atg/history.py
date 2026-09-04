"""Full immutable graph snapshots for refinement history.

Implements concepts from Zhang et al. (2026), Atomic Task Graph, §4.1 / §4.3
(graph evolution used later for localized repair). See docs/ATTRIBUTION.md.

Decision 0009: full snapshots each compile/repair step (not an event log).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from atg.graph import TaskGraph


class GraphSnapshot(BaseModel):
    """Point-in-time copy of graph topology and node payloads."""

    index: int
    reason: str = "unspecified"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any]


class GraphHistory:
    """Append-only list of immutable snapshots."""

    def __init__(self) -> None:
        self._snapshots: list[GraphSnapshot] = []

    def __len__(self) -> int:
        return len(self._snapshots)

    def snapshots(self) -> list[GraphSnapshot]:
        return list(self._snapshots)

    def latest(self) -> GraphSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def record(self, graph: TaskGraph, reason: str = "unspecified") -> GraphSnapshot:
        snap = GraphSnapshot(
            index=len(self._snapshots),
            reason=reason,
            payload=graph.to_dict(),
        )
        self._snapshots.append(snap)
        return snap

    def restore(self, index: int = -1) -> TaskGraph:
        if not self._snapshots:
            raise IndexError("No snapshots to restore")
        snap = self._snapshots[index]
        return TaskGraph.from_dict(snap.payload)
