"""Parallel runner port. Default is a thread pool (Decision 0010)."""

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


class ThreadRunner:
    """``max_workers=None`` keeps ``ThreadPoolExecutor``'s own default."""

    def __init__(self, max_workers: int | None = None) -> None:
        self.max_workers = max_workers

    def map(self, fn: Callable[[T], R], items: Sequence[T]) -> list[R]:
        batch = list(items)
        if not batch:
            return []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(fn, batch))


class SequentialRunner:
    """Same port, one job at a time. Tests and debugging."""

    def map(self, fn: Callable[[T], R], items: Sequence[T]) -> list[R]:
        return [fn(item) for item in items]
