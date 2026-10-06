"""Compile, check, execute, and repair once per failed wave.

Orchestrates Zhang et al. (2026) §§4.1–4.3. A thought-experiment error
that names a live node is repaired before execution (paper §4.3). An
error that names no node is not repaired. The judge stays off unless
``judge=True`` or ``ATG_JUDGE=1`` (Decision 0013). ``max_repairs`` counts
pre-execution and runtime repairs together (Decision 0014). Independent
reimplementation; see docs/ATTRIBUTION.md (``zhang2026atg``).
"""

import os
from typing import Any

from pydantic import BaseModel, ConfigDict

from atg.executor import execute
from atg.graph import TaskGraph
from atg.history import GraphHistory
from atg.metrics import Metrics
from atg.planner import compile_task
from atg.repair import repair_graph
from atg.thought import ThoughtReport, thought_experiment
from atg.tools import ToolRegistry
from atg.types import NodeStatus, TaskNode


class RunResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    graph: TaskGraph
    history: GraphHistory
    metrics: Metrics
    thought: ThoughtReport


def implicated_ids(errors: list[str], graph: TaskGraph) -> list[str]:
    """Node ids named at the start of a thought-experiment error."""

    known = set(graph.node_ids())
    found: list[str] = []
    for error in errors:
        token = error.split(" ", 1)[0].split(".", 1)[0]
        if token in known and token not in found:
            found.append(token)
    return found


def run_task(
    root: TaskNode,
    registry: ToolRegistry,
    llm: Any,
    *,
    runner: Any = None,
    max_depth: int = 6,
    max_repairs: int = 2,
    judge: bool | None = None,
) -> RunResult:
    if judge is None:
        judge = os.environ.get("ATG_JUDGE") == "1"
    graph, history = compile_task(root, registry, llm, max_depth=max_depth)
    judge_llm = llm if judge else None
    report = thought_experiment(graph, registry, judge_llm)
    metrics = Metrics()
    remaining = max_repairs
    while not report.ok and remaining:
        targets = implicated_ids(report.errors, graph)
        if not targets:
            break
        graph = repair_graph(graph, history, targets, registry, llm)
        remaining -= 1
        metrics.repairs += 1
        report = thought_experiment(graph, registry, judge_llm)
    if report.judge_used and not report.ok:
        metrics.judge_disagreements = 1
    if not report.ok:
        metrics.notes.extend(report.errors)
        return RunResult(graph=graph, history=history, metrics=metrics, thought=report)
    execute(graph, registry, runner=runner, metrics=metrics)
    for _ in range(remaining):
        failed = [
            node_id
            for node_id in graph.node_ids()
            if graph.get(node_id).status == NodeStatus.failed
        ]
        if not failed:
            break
        graph = repair_graph(graph, history, failed, registry, llm)
        metrics.repairs += 1
        execute(graph, registry, runner=runner, metrics=metrics)
    return RunResult(graph=graph, history=history, metrics=metrics, thought=report)
