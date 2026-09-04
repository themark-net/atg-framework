"""Run-level counters for execute / later repair (ARCH §5.6)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunMetrics(BaseModel):
    total_steps: int = 0
    wall_time_s: float = 0.0
    max_parallel: int = 0
    waves: int = 0
    repairs: int = 0
    nodes_frozen_reused: int = 0
    nodes_failed: int = 0
    events: list[str] = Field(default_factory=list)

    def emit(self, event: str) -> None:
        self.events.append(event)
