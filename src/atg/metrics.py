"""Run counters aligned with Zhang et al. (2026) step accounting.

A parallel wave counts as one step (paper Table 2; Decision 0011).
This is an independent reimplementation. See docs/ATTRIBUTION.md
(``zhang2026atg``).
"""

from pydantic import BaseModel, ConfigDict, Field


class Metrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    waves: int = 0
    tool_calls: int = 0
    max_parallel: int = 0
    failures: int = 0
    repairs: int = 0
    nodes_frozen_reused: int = 0
    judge_disagreements: int = 0
    notes: list[str] = Field(default_factory=list)
