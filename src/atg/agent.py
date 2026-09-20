"""End-to-end ATG control loop: compile → thought experiment → execute → repair.

Wires the three stages described by Zhang et al. (2026), Atomic Task Graph
(§4.1 compilation, §4.2 dependency-aware execution with a pre-execution
thought experiment, §4.3 minimal subgraph repair) into one driver. See
docs/ATTRIBUTION.md and docs/citations.bib (zhang2026atg). Independent
reimplementation, not official code.

Core stays framework-agnostic (Decision 0002): no LangGraph/DSPy here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from atg.executor import ExecutionError, ExecutionResult, GraphExecutor
from atg.llm import LLMClient
from atg.metrics import RunMetrics
from atg.planner import CompiledPlan, Planner
from atg.repair import Repairer, RepairError, RepairEvent
from atg.runner import ParallelRunner
from atg.thought import ThoughtExperiment, ThoughtReport
from atg.tools import ToolRegistry
from atg.types import TaskSpec


class AgentResult(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    ok: bool = False
    outputs: dict[str, Any] = Field(default_factory=dict)
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    repairs: list[RepairEvent] = Field(default_factory=list)
    thought_reports: list[ThoughtReport] = Field(default_factory=list)
    executions: list[ExecutionResult] = Field(default_factory=list)
    plan: CompiledPlan | None = None
    error: str | None = None


class ATGAgent:
    """Run a ``TaskSpec`` against registered tools with an LLM planner."""

    def __init__(
        self,
        registry: ToolRegistry,
        llm: LLMClient,
        *,
        runner: ParallelRunner | None = None,
        max_depth: int = 6,
        max_repairs: int = 3,
        thought_experiment: bool = True,
        judge: LLMClient | None = None,
        escalate_after: int = 1,
    ) -> None:
        self.registry = registry
        self.planner = Planner(registry, llm, max_depth=max_depth)
        self.repairer = Repairer(self.planner, escalate_after=escalate_after)
        self.executor = GraphExecutor(registry, runner=runner, stop_on_failure=True)
        self.thought = (
            ThoughtExperiment(registry, judge=judge) if thought_experiment else None
        )
        self.max_repairs = max_repairs

    def run(self, spec: TaskSpec) -> AgentResult:
        result = AgentResult()
        plan = self.planner.compile(spec)
        result.plan = plan
        metrics = result.metrics

        while True:
            if self.thought is not None:
                report = self.thought.check(plan)
                result.thought_reports.append(report)
                if not report.ok:
                    metrics.emit(f"thought_reject:{','.join(report.node_ids())}")
                    flagged = [
                        plan.root_id if n == "*" else n for n in report.node_ids()
                    ]
                    if not self._try_repair(
                        plan, flagged, report.messages_by_node(), result
                    ):
                        return self._finish(
                            result,
                            plan,
                            f"Thought experiment rejected plan: {report.issues}",
                        )
                    continue

            try:
                execution = self.executor.run(plan.graph)
            except ExecutionError as exc:
                execution = exc.result
                result.executions.append(execution)
                self._merge(metrics, execution, len(result.executions))
                failed = execution.failed_ids()
                if not failed:
                    return self._finish(result, plan, str(exc))
                if not self._try_repair(plan, failed, None, result):
                    return self._finish(result, plan, str(exc))
                continue

            result.executions.append(execution)
            self._merge(metrics, execution, len(result.executions))
            result.ok = True
            result.outputs = plan.task_outputs()
            return result

    # ----- helpers -----------------------------------------------------

    def _try_repair(
        self,
        plan: CompiledPlan,
        failed_ids: list[str],
        errors: dict[str, str] | None,
        result: AgentResult,
    ) -> bool:
        if len(result.repairs) >= self.max_repairs:
            return False
        result.metrics.emit(f"repair_started:{','.join(failed_ids)}")
        try:
            event = self.repairer.repair(plan, failed_ids, errors=errors)
        except RepairError as exc:
            result.metrics.emit(f"repair_failed:{exc}")
            return False
        result.repairs.append(event)
        result.metrics.repairs += 1
        result.metrics.emit(f"repair_done:{event.lca}")
        return True

    @staticmethod
    def _merge(
        total: RunMetrics, run: RunMetrics | ExecutionResult, index: int
    ) -> None:
        m = run.metrics if isinstance(run, ExecutionResult) else run
        total.total_steps += m.total_steps
        total.wall_time_s += m.wall_time_s
        total.max_parallel = max(total.max_parallel, m.max_parallel)
        total.waves += m.waves
        total.nodes_frozen_reused += m.nodes_frozen_reused
        total.nodes_failed += m.nodes_failed
        total.events.extend(f"run{index}:{e}" for e in m.events)

    @staticmethod
    def _finish(result: AgentResult, plan: CompiledPlan, error: str) -> AgentResult:
        result.ok = False
        result.error = error
        result.outputs = plan.task_outputs()
        return result
