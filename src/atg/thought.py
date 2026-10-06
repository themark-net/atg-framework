"""Pre-execution thought experiment.

Zhang et al. (2026), Atomic Task Graph, §4.2. Decision 0013: structural
checks always run. An LLM judge is optional and off unless requested.
The judge is the comparison arm for semantic mistakes the rules cannot
see. Independent reimplementation; see docs/ATTRIBUTION.md
(``zhang2026atg``).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from atg.graph import TaskGraph
from atg.tools import ToolRegistry, is_atomic
from atg.validation import InterfaceError, assert_valid


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    reason: str = ""


class ThoughtReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    errors: list[str] = Field(default_factory=list)
    judge_used: bool = False


def structural_thought(graph: TaskGraph, registry: ToolRegistry) -> ThoughtReport:
    errors: list[str] = []
    try:
        assert_valid(graph)
    except (InterfaceError, Exception) as exc:
        errors.append(str(exc))
    for node_id in graph.node_ids():
        node = graph.get(node_id)
        if not is_atomic(node, registry):
            errors.append(f"{node_id} is not atomic")
        elif node.tool_name and node.tool_name not in registry:
            errors.append(f"{node_id} tool {node.tool_name} is not registered")
    return ThoughtReport(ok=not errors, errors=errors)


def thought_experiment(
    graph: TaskGraph,
    registry: ToolRegistry,
    llm: Any = None,
) -> ThoughtReport:
    """Rules first. ``llm`` adds one judge call when the rules pass."""

    report = structural_thought(graph, registry)
    if llm is None or not report.ok:
        return report
    verdict = llm.complete_structured(_judge_messages(graph, registry), JudgeVerdict)
    report.judge_used = True
    if not verdict.ok:
        report.errors.append(verdict.reason or "judge rejected the plan")
        report.ok = False
    return report


def _judge_messages(graph: TaskGraph, registry: ToolRegistry) -> list[dict]:
    nodes = [graph.get(node_id).model_dump(mode="json") for node_id in graph.topological_order()]
    return [
        {
            "role": "system",
            "content": (
                "You are a plan judge. Reply with JSON {ok, reason}. "
                "ok is false only when the tool choice or the data flow cannot "
                "produce the declared outputs. Do not reject a plan only because "
                "it is short."
            ),
        },
        {
            "role": "user",
            "content": str({"nodes": nodes, "tools": registry.names()}),
        },
    ]
