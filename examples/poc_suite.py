"""Toy PoC: localized repair versus whole-graph replan and sequential replay.

Offline (default) scripts ``MockLLM`` and writes ``docs/poc/offline-report.json``
and ``docs/poc/offline-report.md``. ``--live`` calls local Ollama and is not
part of the unit tests.

The product path is localized repair (Decision 0014). The other two arms are
measurement only. Numbers are toy-scale, not the paper's ALFWorld, WebShop,
or ScienceWorld scores. The suite measures Zhang et al. (2026), §4.3.
Independent reimplementation; see docs/ATTRIBUTION.md (``zhang2026atg``).

    uv run python examples/poc_suite.py
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from atg.executor import execute, normalize_output, resolve_inputs
from atg.graph import TaskGraph
from atg.llm import DEFAULT_MODEL, FALLBACK_MODELS, MockLLM, OllamaClient, OpenAICompatClient
from atg.metrics import Metrics
from atg.planner import ChildNode, Decomposition, EdgeSpec, compile_task
from atg.run import run_task
from atg.thought import thought_experiment
from atg.tools import ToolRegistry
from atg.types import NodeStatus, TaskNode

_ROOT = Path(__file__).resolve().parents[1]
OFFLINE_JSON = _ROOT / "docs" / "poc" / "offline-report.json"
OFFLINE_MD = _ROOT / "docs" / "poc" / "offline-report.md"
_ARMS = ("localized", "global_replan", "sequential")
_NOTE = (
    "Toy-scale synthetic metrics for localized repair "
    "(Zhang et al. 2026, arXiv:2607.01942, §4.3). "
    "Not ALFWorld, WebShop, or ScienceWorld scores."
)


@dataclass(frozen=True)
class TaskSpec:
    id: str
    name: str
    expected: int
    failed_once: bool
    plan: Decomposition
    repair: Decomposition | None = None
    replan_mid: Decomposition | None = None
    replan_final: Decomposition | None = None


def _parameters(*names: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {name: {"type": "integer"} for name in names},
        "required": list(names),
    }


def make_registry(flake: bool) -> ToolRegistry:
    """Fresh tools. A failing task's flaky callable raises on its first call."""

    registry = ToolRegistry()

    def add(a: int, b: int) -> dict:
        return {"value": a + b}

    def mul(a: int, b: int) -> dict:
        return {"value": a * b}

    def join(left: int, right: int) -> dict:
        return {"value": left + right}

    registry.register(
        add,
        name="add",
        description="Add integers a and b. Returns value.",
        parameters=_parameters("a", "b"),
    )
    registry.register(
        mul,
        name="mul",
        description="Multiply integers a and b. Returns value.",
        parameters=_parameters("a", "b"),
    )
    registry.register(
        join,
        name="join",
        description="Add integers left and right. Returns value.",
        parameters=_parameters("left", "right"),
    )
    if not flake:
        return registry
    seen = {"add": 0, "mul": 0}

    def flaky_add(a: int, b: int) -> dict:
        seen["add"] += 1
        if seen["add"] == 1:
            raise RuntimeError("boom")
        return {"value": a + b}

    def flaky_mul(a: int, b: int) -> dict:
        seen["mul"] += 1
        if seen["mul"] == 1:
            raise RuntimeError("boom")
        return {"value": a * b}

    registry.register(
        flaky_add,
        name="flaky_add",
        description="Add integers a and b. Returns value.",
        parameters=_parameters("a", "b"),
    )
    registry.register(
        flaky_mul,
        name="flaky_mul",
        description="Multiply integers a and b. Returns value.",
        parameters=_parameters("a", "b"),
    )
    return registry


def _ref(node_id: str) -> dict[str, str]:
    return {"$ref": f"{node_id}.outputs.value"}


def _plan(items: list[tuple[str, str, dict]], edges: list[tuple[str, str]]) -> Decomposition:
    return Decomposition(
        nodes=[
            ChildNode(
                id=node_id,
                name=node_id,
                tool_name=tool,
                inputs=inputs,
                declared_outputs=["value"],
                refine=False,
            )
            for node_id, tool, inputs in items
        ],
        edges=[EdgeSpec(src=src, dst=dst) for src, dst in edges],
    )


def _open_stage() -> Decomposition:
    """Non-atomic replan. Compilation must call the model once more."""

    return Decomposition(
        nodes=[
            ChildNode(
                id="stage",
                name="stage",
                declared_outputs=["value"],
                refine=True,
            )
        ]
    )


def _catalog() -> list[TaskSpec]:
    tasks = [
        TaskSpec(
            id="add_pair",
            name="Add 2 and 3.",
            expected=5,
            failed_once=False,
            plan=_plan([("total", "add", {"a": 2, "b": 3})], []),
        ),
        TaskSpec(
            id="mul_pair",
            name="Multiply 6 and 7.",
            expected=42,
            failed_once=False,
            plan=_plan([("total", "mul", {"a": 6, "b": 7})], []),
        ),
        TaskSpec(
            id="scale_sum",
            name="Add 2 and 3, then multiply by 4.",
            expected=20,
            failed_once=False,
            plan=_plan(
                [
                    ("a_sum", "add", {"a": 2, "b": 3}),
                    ("total", "mul", {"a": _ref("a_sum"), "b": 4}),
                ],
                [("a_sum", "total")],
            ),
        ),
        TaskSpec(
            id="parallel_sums",
            name="Add 1+2 and 3+4 in parallel, then add those sums.",
            expected=10,
            failed_once=False,
            plan=_plan(
                [
                    ("a_left", "add", {"a": 1, "b": 2}),
                    ("b_right", "add", {"a": 3, "b": 4}),
                    ("total", "join", {"left": _ref("a_left"), "right": _ref("b_right")}),
                ],
                [("a_left", "total"), ("b_right", "total")],
            ),
        ),
        TaskSpec(
            id="parallel_prod",
            name="Multiply 3*5 and 2*7 in parallel, then add the products.",
            expected=29,
            failed_once=False,
            plan=_plan(
                [
                    ("a_left", "mul", {"a": 3, "b": 5}),
                    ("b_right", "mul", {"a": 2, "b": 7}),
                    ("total", "join", {"left": _ref("a_left"), "right": _ref("b_right")}),
                ],
                [("a_left", "total"), ("b_right", "total")],
            ),
        ),
        TaskSpec(
            id="diamond",
            name="Add 2+2, then multiply by 3 and add 2 in parallel, then add those.",
            expected=18,
            failed_once=False,
            plan=_plan(
                [
                    ("a_root", "add", {"a": 2, "b": 2}),
                    ("b_mul", "mul", {"a": _ref("a_root"), "b": 3}),
                    ("c_add", "add", {"a": _ref("a_root"), "b": 2}),
                    ("total", "join", {"left": _ref("b_mul"), "right": _ref("c_add")}),
                ],
                [
                    ("a_root", "b_mul"),
                    ("a_root", "c_add"),
                    ("b_mul", "total"),
                    ("c_add", "total"),
                ],
            ),
        ),
        TaskSpec(
            id="three_wide",
            name="Add 1+1, 2+2, and 3+3 in parallel, then fold the three sums.",
            expected=12,
            failed_once=False,
            plan=_plan(
                [
                    ("a_left", "add", {"a": 1, "b": 1}),
                    ("b_mid", "add", {"a": 2, "b": 2}),
                    ("c_right", "add", {"a": 3, "b": 3}),
                    ("p_sum", "join", {"left": _ref("a_left"), "right": _ref("b_mid")}),
                    ("total", "join", {"left": _ref("p_sum"), "right": _ref("c_right")}),
                ],
                [
                    ("a_left", "p_sum"),
                    ("b_mid", "p_sum"),
                    ("p_sum", "total"),
                    ("c_right", "total"),
                ],
            ),
        ),
        TaskSpec(
            id="nested_chain",
            name="Add 3+3, multiply by 2, then multiply by 3.",
            expected=36,
            failed_once=False,
            plan=_plan(
                [
                    ("a_sum", "add", {"a": 3, "b": 3}),
                    ("b_scale", "mul", {"a": _ref("a_sum"), "b": 2}),
                    ("total", "mul", {"a": _ref("b_scale"), "b": 3}),
                ],
                [("a_sum", "b_scale"), ("b_scale", "total")],
            ),
        ),
    ]
    tasks.extend(_failing_tasks())
    return tasks


def _failing_tasks() -> list[TaskSpec]:
    """Four plans whose first flaky call raises. The repair reuses a frozen sibling."""

    parallel = _plan(
        [
            ("a_left", "add", {"a": 2, "b": 3}),
            ("z_right", "flaky_mul", {"a": 4, "b": 5}),
            ("total", "join", {"left": _ref("a_left"), "right": _ref("z_right")}),
        ],
        [("a_left", "total"), ("z_right", "total")],
    )
    parallel_repair = _plan(
        [
            ("z_fix", "flaky_mul", {"a": 4, "b": 5}),
            ("total", "join", {"left": _ref("a_left"), "right": _ref("z_fix")}),
        ],
        [("z_fix", "total")],
    )
    parallel_final = _plan(
        [
            ("a_left", "add", {"a": 2, "b": 3}),
            ("b_right", "mul", {"a": 4, "b": 5}),
            ("total", "join", {"left": _ref("a_left"), "right": _ref("b_right")}),
        ],
        [("a_left", "total"), ("b_right", "total")],
    )
    chain = _plan(
        [
            ("a_in", "add", {"a": 2, "b": 3}),
            ("z_scale", "flaky_mul", {"a": _ref("a_in"), "b": 4}),
            ("total", "add", {"a": _ref("z_scale"), "b": 1}),
        ],
        [("a_in", "z_scale"), ("z_scale", "total")],
    )
    chain_repair = _plan(
        [
            ("z_fix", "flaky_mul", {"a": _ref("a_in"), "b": 4}),
            ("total", "add", {"a": _ref("z_fix"), "b": 1}),
        ],
        [("z_fix", "total")],
    )
    chain_final = _plan(
        [
            ("a_in", "add", {"a": 2, "b": 3}),
            ("b_scale", "mul", {"a": _ref("a_in"), "b": 4}),
            ("total", "add", {"a": _ref("b_scale"), "b": 1}),
        ],
        [("a_in", "b_scale"), ("b_scale", "total")],
    )
    diamond = _plan(
        [
            ("a_root", "add", {"a": 1, "b": 1}),
            ("b_mid", "mul", {"a": _ref("a_root"), "b": 3}),
            ("z_mid", "flaky_add", {"a": _ref("a_root"), "b": 6}),
            ("total", "join", {"left": _ref("b_mid"), "right": _ref("z_mid")}),
        ],
        [
            ("a_root", "b_mid"),
            ("a_root", "z_mid"),
            ("b_mid", "total"),
            ("z_mid", "total"),
        ],
    )
    diamond_repair = _plan(
        [
            ("z_fix", "flaky_add", {"a": _ref("a_root"), "b": 6}),
            ("total", "join", {"left": _ref("b_mid"), "right": _ref("z_fix")}),
        ],
        [("z_fix", "total")],
    )
    diamond_final = _plan(
        [
            ("a_root", "add", {"a": 1, "b": 1}),
            ("b_mid", "mul", {"a": _ref("a_root"), "b": 3}),
            ("c_mid", "add", {"a": _ref("a_root"), "b": 6}),
            ("total", "join", {"left": _ref("b_mid"), "right": _ref("c_mid")}),
        ],
        [
            ("a_root", "b_mid"),
            ("a_root", "c_mid"),
            ("b_mid", "total"),
            ("c_mid", "total"),
        ],
    )
    wide = _plan(
        [
            ("a_left", "add", {"a": 1, "b": 1}),
            ("m_mid", "add", {"a": 3, "b": 3}),
            ("z_flaky", "flaky_add", {"a": 2, "b": 2}),
            ("p_sum", "join", {"left": _ref("a_left"), "right": _ref("z_flaky")}),
            ("total", "join", {"left": _ref("p_sum"), "right": _ref("m_mid")}),
        ],
        [
            ("a_left", "p_sum"),
            ("z_flaky", "p_sum"),
            ("p_sum", "total"),
            ("m_mid", "total"),
        ],
    )
    wide_repair = _plan(
        [
            ("z_fix", "flaky_add", {"a": 2, "b": 2}),
            ("p_sum", "join", {"left": _ref("a_left"), "right": _ref("z_fix")}),
            ("total", "join", {"left": _ref("p_sum"), "right": _ref("m_mid")}),
        ],
        [("z_fix", "p_sum"), ("p_sum", "total")],
    )
    wide_final = _plan(
        [
            ("a_left", "add", {"a": 1, "b": 1}),
            ("m_mid", "add", {"a": 3, "b": 3}),
            ("b_right", "add", {"a": 2, "b": 2}),
            ("p_sum", "join", {"left": _ref("a_left"), "right": _ref("b_right")}),
            ("total", "join", {"left": _ref("p_sum"), "right": _ref("m_mid")}),
        ],
        [
            ("a_left", "p_sum"),
            ("b_right", "p_sum"),
            ("p_sum", "total"),
            ("m_mid", "total"),
        ],
    )
    return [
        TaskSpec(
            id="fail_parallel",
            name="Add 2+3 and multiply 4*5 in parallel, then add. The product fails once.",
            expected=25,
            failed_once=True,
            plan=parallel,
            repair=parallel_repair,
            replan_mid=_open_stage(),
            replan_final=parallel_final,
        ),
        TaskSpec(
            id="fail_chain",
            name="Add 2+3, multiply by 4, then add 1. The multiply fails once.",
            expected=21,
            failed_once=True,
            plan=chain,
            repair=chain_repair,
            replan_mid=_open_stage(),
            replan_final=chain_final,
        ),
        TaskSpec(
            id="fail_diamond",
            name="Add 1+1, then multiply by 3 and add 6 in parallel, then add. The add fails once.",
            expected=14,
            failed_once=True,
            plan=diamond,
            repair=diamond_repair,
            replan_mid=_open_stage(),
            replan_final=diamond_final,
        ),
        TaskSpec(
            id="fail_wide",
            name="Add 1+1, 2+2, and 3+3 in parallel, then fold. The 2+2 add fails once.",
            expected=12,
            failed_once=True,
            plan=wide,
            repair=wide_repair,
            replan_mid=_open_stage(),
            replan_final=wide_final,
        ),
    ]


TASKS = _catalog()


class _CountingLLM:
    """Counts ``complete_structured``. The inner client performs the call."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls = 0

    def complete(self, messages: list[dict], **kwargs: Any) -> str:
        return self.inner.complete(messages, **kwargs)

    def complete_structured(self, messages: list[dict], schema: type[BaseModel]) -> BaseModel:
        self.calls += 1
        return self.inner.complete_structured(messages, schema)


def _script(task: TaskSpec, arm: str) -> list[Any]:
    missing = task.repair is None or task.replan_mid is None or task.replan_final is None
    if task.failed_once and missing:
        raise ValueError(f"{task.id} is missing a failing-arm script")
    if not task.failed_once or arm == "sequential":
        items: list[Any] = [task.plan]
    elif arm == "localized":
        items = [task.plan, task.repair]
    elif arm == "global_replan":
        items = [task.plan, task.replan_mid, task.replan_final]
    else:
        raise ValueError(arm)
    return [item.model_copy(deep=True) for item in items]


def _offline_llm(task: TaskSpec, arm: str) -> _CountingLLM:
    return _CountingLLM(MockLLM(_script(task, arm)))


def _sink_value(graph: TaskGraph) -> Any:
    sinks = [node_id for node_id in graph.node_ids() if not graph.successors(node_id)]
    if len(sinks) != 1:
        return None
    outputs = graph.get(sinks[0]).outputs
    if not outputs or "value" not in outputs:
        return None
    return outputs["value"]


def _run_node(graph: TaskGraph, registry: ToolRegistry, metrics: Metrics, node_id: str) -> bool:
    """Run one ready node. Return True when the tool fails."""

    node = graph.get(node_id)
    graph.transition(node_id, NodeStatus.running)
    if not node.tool_name or node.tool_name not in registry:
        graph.transition(node_id, NodeStatus.failed, error="no callable for node")
        metrics.failures += 1
        return True
    try:
        kwargs = resolve_inputs(graph, node_id)
        value = registry.get(node.tool_name).fn(**kwargs)
    except Exception as exc:
        graph.transition(node_id, NodeStatus.failed, error=f"{type(exc).__name__}: {exc}")
        metrics.failures += 1
        return True
    graph.transition(
        node_id,
        NodeStatus.done,
        outputs=normalize_output(value, list(node.declared_outputs)),
    )
    metrics.tool_calls += 1
    metrics.waves += 1
    return False


def _sequential_pass(graph: TaskGraph, registry: ToolRegistry, metrics: Metrics) -> bool:
    """Return True when a tool fails. Ready nodes stay one-at-a-time."""

    for _ in range(len(graph) + 1):
        ready = [
            node_id
            for node_id in graph.mark_ready()
            if graph.get(node_id).status == NodeStatus.ready
        ]
        if not ready:
            return False
        if _run_node(graph, registry, metrics, ready[0]):
            return True
    return True


def _execute_sequential(graph: TaskGraph, registry: ToolRegistry, metrics: Metrics) -> None:
    """Topological order, one tool at a time.

    ``execute`` records ``max_parallel`` as the whole ready set, so this arm
    does not call it. A failure clears every output and runs the chain once
    more. Siblings are not frozen.
    """

    metrics.max_parallel = 1
    for attempt in (0, 1):
        failed = _sequential_pass(graph, registry, metrics)
        if not failed or attempt == 1:
            return
        for node_id in list(graph.node_ids()):
            graph.reset_for_repair(node_id)


def _compile_and_check(
    root: TaskNode,
    registry: ToolRegistry,
    llm: Any,
    metrics: Metrics,
) -> TaskGraph | None:
    graph, _history = compile_task(root, registry, llm)
    report = thought_experiment(graph, registry, None)
    if not report.ok:
        metrics.notes.extend(report.errors)
        return None
    return graph


def _global_replan(
    root: TaskNode, registry: ToolRegistry, llm: Any, metrics: Metrics
) -> tuple[TaskGraph, bool]:
    """On a tool failure, replace the whole graph under the original root.

    Measurement only. This does not call ``repair_graph``.
    """

    graph = _compile_and_check(root, registry, llm, metrics)
    if graph is None:
        return TaskGraph(), False
    execute(graph, registry, metrics=metrics)
    failed = [
        node_id
        for node_id in graph.node_ids()
        if graph.get(node_id).status == NodeStatus.failed
    ]
    if not failed:
        return graph, True
    metrics.repairs += 1
    rebuilt = _compile_and_check(root, registry, llm, metrics)
    if rebuilt is None:
        return graph, True
    execute(rebuilt, registry, metrics=metrics)
    return rebuilt, True


def _run_localized(root: TaskNode, registry: ToolRegistry, llm: Any) -> tuple[TaskGraph, Metrics, bool]:
    result = run_task(root, registry, llm, judge=False)
    return result.graph, result.metrics, result.thought.ok


def _run_one(task: TaskSpec, arm: str, llm: _CountingLLM) -> dict[str, Any]:
    registry = make_registry(task.failed_once)
    root = TaskNode(id="job", name=task.name, declared_outputs=["value"])
    started = time.perf_counter()
    plan_ok = False
    if arm == "localized":
        graph, metrics, plan_ok = _run_localized(root, registry, llm)
    elif arm == "global_replan":
        metrics = Metrics()
        graph, plan_ok = _global_replan(root, registry, llm, metrics)
    elif arm == "sequential":
        metrics = Metrics()
        graph = _compile_and_check(root, registry, llm, metrics)
        plan_ok = graph is not None
        if graph is None:
            graph = TaskGraph()
            metrics.max_parallel = 1
        else:
            _execute_sequential(graph, registry, metrics)
    else:
        raise ValueError(arm)
    elapsed = time.perf_counter() - started
    actual = _sink_value(graph)
    return {
        "id": task.id,
        "failed_once": task.failed_once,
        "expected": task.expected,
        "actual": actual,
        "success": actual == task.expected,
        "plan_ok": plan_ok,
        "llm_calls": llm.calls,
        "tool_calls": metrics.tool_calls,
        "nodes_frozen_reused": metrics.nodes_frozen_reused,
        "repairs": metrics.repairs,
        "wall_time_s": round(elapsed, 6),
        "max_parallel": metrics.max_parallel,
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "success": sum(1 for row in rows if row["success"]),
        "plan_ok": sum(1 for row in rows if row["plan_ok"]),
        "llm_calls": sum(row["llm_calls"] for row in rows),
        "tool_calls": sum(row["tool_calls"] for row in rows),
        "nodes_frozen_reused": sum(row["nodes_frozen_reused"] for row in rows),
        "repairs": sum(row["repairs"] for row in rows),
        "wall_time_s": round(sum(row["wall_time_s"] for row in rows), 6),
        "max_parallel": max(row["max_parallel"] for row in rows),
        "tasks": rows,
    }


def run_suite(
    llm_factory: Callable[[TaskSpec, str], _CountingLLM],
    *,
    offline: bool,
) -> dict[str, Any]:
    """Run every task on localized, global_replan, and sequential."""

    rows = {
        arm: [_run_one(task, arm, llm_factory(task, arm)) for task in TASKS]
        for arm in _ARMS
    }
    localized = rows["localized"]
    return {
        "suite": "toy-poc",
        "mode": "offline" if offline else "live",
        "note": _NOTE,
        "task_count": len(localized),
        "failed_once_count": sum(1 for row in localized if row["failed_once"]),
        "arms": {arm: _summarize(rows[arm]) for arm in _ARMS},
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Toy PoC offline report",
        "",
        report["note"],
        "",
        "Localized repair is the product path (Decision 0014). "
        "Global replan and sequential replay are measurement arms only.",
        "",
        "`repairs` on localized counts `repair_graph` calls. "
        "On global replan it counts one whole-graph recompile after a tool failure. "
        "Sequential replay discards outputs and runs the chain again, so its `repairs` stays 0.",
        "",
        "`max_parallel` is the widest wave in that arm, not a sum across tasks.",
        "",
        "| arm | success | llm_calls | tool_calls | nodes_frozen_reused | repairs | wall_time_s | max_parallel |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, body in report["arms"].items():
        lines.append(
            "| {arm} | {success} | {llm_calls} | {tool_calls} | {frozen} | {repairs} | {wall:.6f} | {width} |".format(
                arm=name,
                success=body["success"],
                llm_calls=body["llm_calls"],
                tool_calls=body["tool_calls"],
                frozen=body["nodes_frozen_reused"],
                repairs=body["repairs"],
                wall=body["wall_time_s"],
                width=body["max_parallel"],
            )
        )
    localized = report["arms"]["localized"]
    global_arm = report["arms"]["global_replan"]
    sequential = report["arms"]["sequential"]
    lines.extend(
        [
            "",
            (
                f"Check: localized llm_calls ({localized['llm_calls']}) < "
                f"global_replan llm_calls ({global_arm['llm_calls']}) "
                f"is {str(localized['llm_calls'] < global_arm['llm_calls']).lower()}."
            ),
            f"Check: sequential max_parallel is {sequential['max_parallel']}.",
            "",
            "## Tasks",
            "",
            "| task | failed_once | expected | loc_llm | glob_llm | seq_llm | loc_tools | seq_tools | loc_frozen | loc_ok | glob_ok | seq_ok |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    by_arm = {
        arm: {row["id"]: row for row in body["tasks"]}
        for arm, body in report["arms"].items()
    }
    for task_id in (row["id"] for row in localized["tasks"]):
        loc = by_arm["localized"][task_id]
        glob = by_arm["global_replan"][task_id]
        seq = by_arm["sequential"][task_id]
        lines.append(
            "| {id} | {fail} | {expected} | {loc_llm} | {glob_llm} | {seq_llm} | {loc_tools} | {seq_tools} | {frozen} | {loc_ok} | {glob_ok} | {seq_ok} |".format(
                id=task_id,
                fail="yes" if loc["failed_once"] else "no",
                expected=loc["expected"],
                loc_llm=loc["llm_calls"],
                glob_llm=glob["llm_calls"],
                seq_llm=seq["llm_calls"],
                loc_tools=loc["tool_calls"],
                seq_tools=seq["tool_calls"],
                frozen=loc["nodes_frozen_reused"],
                loc_ok="yes" if loc["success"] else "no",
                glob_ok="yes" if glob["success"] else "no",
                seq_ok="yes" if seq["success"] else "no",
            )
        )
    lines.append("")
    return "\n".join(lines)


def _write_offline(report: dict[str, Any]) -> None:
    OFFLINE_JSON.parent.mkdir(parents=True, exist_ok=True)
    OFFLINE_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    OFFLINE_MD.write_text(_markdown(report), encoding="utf-8")


def run_offline_suite() -> dict[str, Any]:
    """Run the scripted suite and write the offline report files."""

    report = run_suite(_offline_llm, offline=True)
    _write_offline(report)
    return report


def _print_summary(report: dict[str, Any]) -> None:
    for arm, body in report["arms"].items():
        print(
            f"{arm} success={body['success']} llm_calls={body['llm_calls']} "
            f"tool_calls={body['tool_calls']} frozen={body['nodes_frozen_reused']} "
            f"repairs={body['repairs']} max_parallel={body['max_parallel']}"
        )


def _write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    path.with_suffix(".md").write_text(_markdown(report), encoding="utf-8")


def _live(
    model: str,
    *,
    host: str | None,
    only: bool,
    client_name: str,
    base_url: str | None,
    report_path: str | None,
) -> int:
    models = [model]
    if not only:
        models.extend(name for name in FALLBACK_MODELS if name != model)
    errors: list[str] = []
    for name in models:
        if client_name == "openai":
            client = OpenAICompatClient(name, base_url=base_url, timeout_s=180)
        else:
            client = OllamaClient(name, host=host, timeout_s=180)

        def factory(_task: TaskSpec, _arm: str, _client: OllamaClient = client) -> _CountingLLM:
            return _CountingLLM(_client)

        try:
            report = run_suite(factory, offline=False)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        print(f"model={name} client={client_name}")
        _print_summary(report)
        if report_path:
            target = Path(report_path)
            if len(models) > 1:
                target = target.with_name(f"{target.stem}-{name}{target.suffix}")
            _write_report(report, target)
            print(f"wrote {target}")
        if all(report["arms"][arm]["success"] == report["task_count"] for arm in _ARMS):
            return 0
        errors.append(
            f"{name}: successes "
            + ", ".join(f"{arm}={report['arms'][arm]['success']}" for arm in _ARMS)
        )
    print("\n".join(errors), file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="scripted MockLLM (default)")
    parser.add_argument("--live", action="store_true", help="call local Ollama; not used by tests")
    parser.add_argument("--model", default=os.environ.get("ATG_MODEL", DEFAULT_MODEL))
    parser.add_argument("--host", default=os.environ.get("ATG_OLLAMA_HOST"))
    parser.add_argument("--only", action="store_true", help="do not try fallback tags")
    parser.add_argument("--client", choices=("ollama", "openai"), default="ollama")
    parser.add_argument("--base-url", default=os.environ.get("ATG_BASE_URL"))
    parser.add_argument("--report", default=None, help="write a live JSON report to this path")
    args = parser.parse_args(argv)
    if args.live and args.offline:
        print("pass only one of --live or --offline", file=sys.stderr)
        return 2
    if args.live:
        return _live(
            args.model,
            host=args.host,
            only=args.only,
            client_name=args.client,
            base_url=args.base_url,
            report_path=args.report,
        )
    report = run_offline_suite()
    _print_summary(report)
    print(f"wrote {OFFLINE_JSON}")
    print(f"wrote {OFFLINE_MD}")
    failed = [arm for arm in _ARMS if report["arms"][arm]["success"] != report["task_count"]]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
