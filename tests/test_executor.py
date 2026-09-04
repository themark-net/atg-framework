from time import sleep, perf_counter

import pytest

from atg.executor import ExecutionError, GraphExecutor
from atg.graph import TaskGraph
from atg.runner import SequentialRunner, ThreadPoolRunner
from atg.tools import ToolRegistry, ToolSpec
from atg.types import NodeStatus, TaskNode


def _graph_diamond() -> TaskGraph:
    g = TaskGraph()
    g.add_node(TaskNode(id="src", name="src", tool_name="echo", inputs={"x": "hi"}))
    g.add_node(
        TaskNode(
            id="left",
            name="left",
            tool_name="slow",
            inputs={"x": {"$ref": "src.outputs.result"}},
        )
    )
    g.add_node(
        TaskNode(
            id="right",
            name="right",
            tool_name="slow",
            inputs={"x": {"$ref": "src.outputs.result"}},
        )
    )
    g.add_node(
        TaskNode(
            id="join",
            name="join",
            tool_name="join",
            inputs={
                "a": {"$ref": "left.outputs.result"},
                "b": {"$ref": "right.outputs.result"},
            },
        )
    )
    g.add_edge("src", "left")
    g.add_edge("src", "right")
    g.add_edge("left", "join")
    g.add_edge("right", "join")
    return g


def _registry(delay: float = 0.15) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolSpec(name="echo"), lambda x: x)
    reg.register(ToolSpec(name="slow"), lambda x: (sleep(delay), x)[1])
    reg.register(ToolSpec(name="join"), lambda a, b: f"{a}+{b}")
    return reg


def test_diamond_parallel_width_and_order():
    g = _graph_diamond()
    ex = GraphExecutor(_registry(0.2), runner=ThreadPoolRunner())
    t0 = perf_counter()
    result = ex.run(g)
    elapsed = perf_counter() - t0
    assert result.ok
    assert result.metrics.max_parallel >= 2
    assert elapsed < 0.55
    assert g.get("join").outputs == {"result": "hi+hi"}
    assert [n.status for n in g.nodes()] == [NodeStatus.done] * 4


def test_dependency_order_with_sequential_runner():
    order: list[str] = []
    reg = ToolRegistry()

    def tagged(name: str):
        def fn(**kwargs):
            order.append(name)
            return kwargs.get("x", name)

        return fn

    for name in ("a", "b", "c"):
        reg.register(ToolSpec(name=name), tagged(name))

    g = TaskGraph()
    g.add_node(TaskNode(id="a", name="a", tool_name="a", inputs={"x": 1}))
    g.add_node(
        TaskNode(id="b", name="b", tool_name="b", inputs={"x": {"$ref": "a.outputs.result"}})
    )
    g.add_node(
        TaskNode(id="c", name="c", tool_name="c", inputs={"x": {"$ref": "b.outputs.result"}})
    )
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    GraphExecutor(reg, runner=SequentialRunner()).run(g)
    assert order == ["a", "b", "c"]


def test_frozen_nodes_not_rerun():
    calls = {"src": 0}
    reg = ToolRegistry()

    def src(x):
        calls["src"] += 1
        return x

    reg.register(ToolSpec(name="src"), src)
    reg.register(ToolSpec(name="next"), lambda x: x + "-ok")

    g = TaskGraph()
    g.add_node(
        TaskNode(
            id="src",
            name="src",
            tool_name="src",
            inputs={"x": "v"},
            status=NodeStatus.frozen,
            outputs={"result": "cached"},
        )
    )
    g.add_node(
        TaskNode(
            id="next",
            name="next",
            tool_name="next",
            inputs={"x": {"$ref": "src.outputs.result"}},
        )
    )
    g.add_edge("src", "next")
    result = GraphExecutor(reg, runner=SequentialRunner()).run(g)
    assert calls["src"] == 0
    assert result.metrics.nodes_frozen_reused == 1
    assert g.get("next").outputs == {"result": "cached-ok"}


def test_failure_blocks_dependents():
    reg = ToolRegistry()
    reg.register(ToolSpec(name="boom"), lambda: (_ for _ in ()).throw(RuntimeError("nope")))
    reg.register(ToolSpec(name="later"), lambda x: x)

    g = TaskGraph()
    g.add_node(TaskNode(id="boom", name="boom", tool_name="boom"))
    g.add_node(
        TaskNode(
            id="later",
            name="later",
            tool_name="later",
            inputs={"x": {"$ref": "boom.outputs.result"}},
        )
    )
    g.add_edge("boom", "later")
    with pytest.raises(ExecutionError) as ei:
        GraphExecutor(reg, runner=SequentialRunner()).run(g)
    assert g.get("boom").status is NodeStatus.failed
    assert g.get("later").status is NodeStatus.pending
    assert ei.value.result.metrics.nodes_failed == 1
