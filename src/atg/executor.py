"""Dependency-aware ready-queue execution.

Implements concepts from Zhang et al. (2026), Atomic Task Graph, §4.2
(Dependency-Aware Execution). See docs/ATTRIBUTION.md and docs/citations.bib
(zhang2026atg). This is an independent reimplementation, not official code.

Decision 0011: dynamic ready-queue. Decision 0010: pluggable runner.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from atg.graph import GraphError, TaskGraph
from atg.metrics import RunMetrics
from atg.runner import ParallelRunner, ThreadPoolRunner
from atg.tools import ToolRegistry, resolve_inputs
from atg.types import NodeStatus
from atg.validation import validate_graph


class ExecutionError(RuntimeError):
    """One or more nodes failed during a run."""

    def __init__(self, message: str, result: ExecutionResult) -> None:
        super().__init__(message)
        self.result = result


class ExecutionResult:
    def __init__(self, graph: TaskGraph, metrics: RunMetrics) -> None:
        self.graph = graph
        self.metrics = metrics

    @property
    def ok(self) -> bool:
        return self.metrics.nodes_failed == 0 and all(
            n.status in {NodeStatus.done, NodeStatus.frozen}
            for n in self.graph.nodes()
        )

    def outputs(self) -> dict[str, dict[str, Any] | None]:
        return {n.id: n.outputs for n in self.graph.nodes()}


def _normalize_output(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    return {"result": raw}


class GraphExecutor:
    """Run atomic tools on a DAG using a dynamic ready-queue."""

    def __init__(
        self,
        registry: ToolRegistry,
        runner: ParallelRunner | None = None,
        stop_on_failure: bool = True,
    ) -> None:
        self.registry = registry
        self.runner = runner or ThreadPoolRunner()
        self.stop_on_failure = stop_on_failure

    def run(self, graph: TaskGraph) -> ExecutionResult:
        validate_graph(graph)
        metrics = RunMetrics()
        metrics.nodes_frozen_reused = sum(
            1 for n in graph.nodes() if n.status is NodeStatus.frozen
        )
        started = perf_counter()
        failed_ids: list[str] = []

        while True:
            ready = graph.ready_set()
            if not ready:
                break
            metrics.waves += 1
            metrics.max_parallel = max(metrics.max_parallel, len(ready))
            metrics.emit(f"wave:{','.join(ready)}")

            for nid in ready:
                graph.mark_status(nid, NodeStatus.running)
                metrics.emit(f"node_started:{nid}")

            jobs = [self._job(graph, nid) for nid in ready]
            outcomes = self.runner.map(jobs)

            wave_failed = False
            for nid, outcome in zip(ready, outcomes, strict=True):
                metrics.total_steps += 1
                if outcome["ok"]:
                    graph.get(nid).outputs = outcome["outputs"]
                    graph.mark_status(nid, NodeStatus.done)
                    metrics.emit(f"node_finished:{nid}")
                else:
                    graph.mark_status(nid, NodeStatus.failed)
                    metrics.nodes_failed += 1
                    failed_ids.append(nid)
                    metrics.emit(f"node_failed:{nid}")
                    wave_failed = True

            if wave_failed and self.stop_on_failure:
                break

        metrics.wall_time_s = perf_counter() - started
        result = ExecutionResult(graph, metrics)
        pending = [
            n.id
            for n in graph.nodes()
            if n.status in {NodeStatus.pending, NodeStatus.ready, NodeStatus.running}
        ]
        if failed_ids:
            raise ExecutionError(
                f"Failed nodes: {failed_ids}; leftover pending: {pending}",
                result,
            )
        if pending:
            raise ExecutionError(
                f"Deadlock or missing tools; leftover pending: {pending}",
                result,
            )
        return result

    def _job(self, graph: TaskGraph, node_id: str) -> Any:
        node = graph.get(node_id)

        def run() -> dict[str, Any]:
            try:
                if not node.tool_name:
                    raise GraphError(f"Node {node_id!r} has no tool_name")
                upstream = {
                    n.id: n.outputs or {}
                    for n in graph.nodes()
                    if n.outputs is not None
                }
                kwargs = resolve_inputs(node.inputs, upstream)
                raw = self.registry.run(node.tool_name, **kwargs)
                return {"ok": True, "outputs": _normalize_output(raw)}
            except Exception as exc:
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

        return run
