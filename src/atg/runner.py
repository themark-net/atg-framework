"""Pluggable parallel runner (Decision 0010).

Default is threads. Scheduler (ready-queue) is independent of how jobs run.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol, TypeVar

T = TypeVar("T")


class ParallelRunner(Protocol):
    """Submit callables and wait for all results, preserving input order."""

    def map(self, jobs: Sequence[Callable[[], T]]) -> list[T]: ...


class SequentialRunner:
    """Deterministic one-at-a-time runner for tests."""

    def map(self, jobs: Sequence[Callable[[], T]]) -> list[T]:
        return [job() for job in jobs]


class ThreadPoolRunner:
    """Default MVP runner for sync tools and I/O-bound work."""

    def __init__(self, max_workers: int | None = None) -> None:
        self.max_workers = max_workers

    def map(self, jobs: Sequence[Callable[[], T]]) -> list[T]:
        if not jobs:
            return []
        if len(jobs) == 1:
            return [jobs[0]()]
        workers = self.max_workers or len(jobs)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(job) for job in jobs]
            return [f.result() for f in futures]
