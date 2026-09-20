"""Pre-execution thought experiment.

Implements concepts from Zhang et al. (2026), Atomic Task Graph, §4.2
(a cheap internal check of the compiled plan before paying environment cost).
See docs/ATTRIBUTION.md and docs/citations.bib (zhang2026atg). Independent
reimplementation, not official code.

First pass follows the OQ-0008 recommendation — hybrid: structural rules
always run; an optional LLM judge can be enabled by passing ``judge``.
Rejected nodes are handed to the repairer exactly like runtime failures.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from atg.graph import TaskGraph
from atg.llm import LLMClient
from atg.planner import CompiledPlan, refs_in
from atg.tools import ToolRegistry
from atg.types import NodeStatus
from atg.validation import ValidationError, validate_graph


class ThoughtIssue(BaseModel):
    node_id: str
    code: str
    message: str


class ThoughtReport(BaseModel):
    issues: list[ThoughtIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def node_ids(self) -> list[str]:
        seen: list[str] = []
        for issue in self.issues:
            if issue.node_id not in seen:
                seen.append(issue.node_id)
        return seen

    def messages_by_node(self) -> dict[str, str]:
        out: dict[str, list[str]] = {}
        for issue in self.issues:
            out.setdefault(issue.node_id, []).append(f"{issue.code}: {issue.message}")
        return {k: "; ".join(v) for k, v in out.items()}


class JudgeVerdict(BaseModel):
    """Structured answer expected from the optional LLM judge."""

    ok: bool = True
    issues: list[ThoughtIssue] = Field(default_factory=list)


class ThoughtExperiment:
    """Rules-based plan validation, with an optional LLM judge."""

    def __init__(self, registry: ToolRegistry, judge: LLMClient | None = None) -> None:
        self.registry = registry
        self.judge = judge

    def check(self, plan: CompiledPlan) -> ThoughtReport:
        report = ThoughtReport(issues=self.structural_issues(plan.graph))
        if report.ok and self.judge is not None:
            report.issues.extend(self.judge_issues(plan))
        return report

    def structural_issues(self, graph: TaskGraph) -> list[ThoughtIssue]:
        issues: list[ThoughtIssue] = []
        try:
            validate_graph(graph)
        except ValidationError as exc:
            issues.append(
                ThoughtIssue(node_id="*", code="invalid_graph", message=str(exc))
            )
            return issues

        names = self.registry.names()
        for node in graph.nodes():
            if node.status in {NodeStatus.done, NodeStatus.frozen}:
                continue
            if not node.is_atomic(names) or node.tool_name is None:
                issues.append(
                    ThoughtIssue(
                        node_id=node.id,
                        code="non_atomic",
                        message=f"node {node.id!r} is not bound to a registered tool",
                    )
                )
                continue
            spec = self.registry.get(node.tool_name)
            missing = [p for p in spec.required_params() if p not in node.inputs]
            if missing:
                issues.append(
                    ThoughtIssue(
                        node_id=node.id,
                        code="missing_params",
                        message=f"tool {spec.name!r} requires {missing}",
                    )
                )
            allowed = spec.param_names()
            if (
                allowed is not None
                and spec.parameters.get("additionalProperties") is not True
            ):
                unknown = [k for k in node.inputs if k not in allowed]
                if unknown:
                    issues.append(
                        ThoughtIssue(
                            node_id=node.id,
                            code="unknown_params",
                            message=f"tool {spec.name!r} does not accept {unknown}",
                        )
                    )
            for src_id, field in refs_in(node.inputs):
                src = graph.get(src_id)
                declared = _declared_outputs(src, self.registry)
                if declared is not None and field not in declared:
                    issues.append(
                        ThoughtIssue(
                            node_id=node.id,
                            code="unknown_output_field",
                            message=(
                                f"$ref {src_id}.outputs.{field} but {src_id!r} exposes {declared}"
                            ),
                        )
                    )
        return issues

    def judge_issues(self, plan: CompiledPlan) -> list[ThoughtIssue]:
        assert self.judge is not None
        request = {
            "task": plan.spec.description,
            "task_outputs": plan.spec.outputs,
            "graph": plan.graph.to_dict(),
            "tools": self.registry.openai_tools(),
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "Mentally simulate this tool DAG before it runs. Report only "
                    "concrete problems (wrong tool for a subtask, missing dependency, "
                    "inputs that cannot produce the required outputs). Reference node ids."
                ),
            },
            {"role": "user", "content": json.dumps(request, default=str)},
        ]
        verdict = self.judge.complete_structured(
            messages, JudgeVerdict, context={"reason": "thought_judge"}
        )
        if verdict.ok and not verdict.issues:
            return []
        return [
            issue
            for issue in verdict.issues
            if issue.node_id in plan.graph
            and plan.graph.get(issue.node_id).status
            not in {NodeStatus.done, NodeStatus.frozen}
        ]


def _declared_outputs(src: Any, registry: ToolRegistry) -> list[str] | None:
    if src.outputs is not None:
        return list(src.outputs)
    if src.output_keys:
        return list(src.output_keys)
    if src.tool_name and src.tool_name in registry:
        return registry.get(src.tool_name).output_keys()
    return None
