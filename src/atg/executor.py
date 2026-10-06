"""Dependency-aware execution.

Zhang et al. (2026), Atomic Task Graph, §4.2. The ready set is Decision
0011. The runner is Decision 0010. Tool calls happen off the graph lock:
status changes are applied on the calling thread after the wave returns.
Independent reimplementation; see docs/ATTRIBUTION.md (``zhang2026atg``).
"""

from collections.abc import Callable
from typing import Any

from atg.graph import TaskGraph
from atg.metrics import Metrics
from atg.runner import ThreadRunner
from atg.tools import ToolRegistry
from atg.types import NodeStatus, parse_ref


def execute(
    graph: TaskGraph,
    registry: ToolRegistry,
    *,
    runner: Any = None,
    metrics: Metrics | None = None,
) -> Metrics:
    metrics = metrics or Metrics()
    runner = runner or ThreadRunner()
    for node_id in list(graph.node_ids()):
        if graph.get(node_id).status != NodeStatus.running:
            continue
        graph.transition(node_id, NodeStatus.failed, error="interrupted before completion")
        metrics.failures += 1
    while True:
        ready = [node_id for node_id in graph.mark_ready() if graph.get(node_id).status == NodeStatus.ready]
        if not ready:
            return metrics
        metrics.waves += 1
        metrics.max_parallel = max(metrics.max_parallel, len(ready))
        prepared: list[tuple[str, Callable[..., Any], dict[str, Any], list[str]]] = []
        for node_id in ready:
            node = graph.get(node_id)
            for pred in graph.predecessors(node_id):
                if graph.get(pred).status == NodeStatus.frozen:
                    metrics.nodes_frozen_reused += 1
            if not node.tool_name or node.tool_name not in registry:
                _fail(graph, metrics, node_id, "no callable for node")
                continue
            try:
                kwargs = resolve_inputs(graph, node_id)
            except Exception as exc:
                _fail(graph, metrics, node_id, str(exc))
                continue
            graph.transition(node_id, NodeStatus.running)
            prepared.append(
                (node_id, registry.get(node.tool_name).fn, kwargs, list(node.declared_outputs))
            )
        if not prepared:
            continue
        results = runner.map(lambda item: _invoke(item[1], item[2]), prepared)
        for (node_id, _fn, _kwargs, declared), (value, err) in zip(prepared, results):
            if err:
                graph.transition(node_id, NodeStatus.failed, error=err)
                metrics.failures += 1
                continue
            graph.transition(node_id, NodeStatus.done, outputs=normalize_output(value, declared))
            metrics.tool_calls += 1


def resolve_inputs(graph: TaskGraph, node_id: str) -> dict[str, Any]:
    node = graph.get(node_id)
    resolved: dict[str, Any] = {}
    for key, value in node.inputs.items():
        ref = parse_ref(value)
        if ref is None:
            resolved[key] = value
            continue
        outputs = graph.get(ref.node_id).outputs
        if outputs is None or ref.field not in outputs:
            raise KeyError(f"{node_id}.{key} missing {ref.node_id}.outputs.{ref.field}")
        resolved[key] = outputs[ref.field]
    return resolved


def normalize_output(value: Any, declared: list[str]) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if len(declared) == 1:
        return {declared[0]: value}
    return {"result": value}


def _invoke(fn: Callable[..., Any], kwargs: dict[str, Any]) -> tuple[Any, str | None]:
    try:
        return fn(**kwargs), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _fail(graph: TaskGraph, metrics: Metrics, node_id: str, message: str) -> None:
    graph.transition(node_id, NodeStatus.running)
    graph.transition(node_id, NodeStatus.failed, error=message)
    metrics.failures += 1
