import time

import pytest

from atg.executor import execute
from atg.graph import GraphError, TaskGraph
from atg.llm import MockLLM
from atg.metrics import Metrics
from atg.persist import load_history, save_history
from atg.planner import ChildNode, CompileError, Decomposition, EdgeSpec, compile_task
from atg.repair import lowest_common_ancestor, repair_region
from atg.run import run_task
from atg.thought import JudgeVerdict, structural_thought, thought_experiment
from atg.tools import ToolRegistry
from atg.types import NodeStatus, TaskNode
from atg.integrations.dspy_adapter import as_dspy_forward
from atg.integrations.langgraph_adapter import as_langgraph_node


def _registry() -> ToolRegistry:
    registry = ToolRegistry()

    def add(a: int, b: int) -> dict:
        return {"value": a + b}

    def mul(a: int, b: int) -> dict:
        return {"value": a * b}

    registry.register(add, name="add", description="Add two integers")
    registry.register(mul, name="mul", description="Multiply two integers")
    return registry


def _parallel_spec() -> Decomposition:
    return Decomposition(
        nodes=[
            ChildNode(
                id="s",
                name="sum",
                tool_name="add",
                inputs={"a": 2, "b": 3},
                declared_outputs=["value"],
                refine=False,
            ),
            ChildNode(
                id="p",
                name="prod",
                tool_name="mul",
                inputs={"a": 4, "b": 5},
                declared_outputs=["value"],
                refine=False,
            ),
            ChildNode(
                id="t",
                name="total",
                tool_name="add",
                inputs={
                    "a": {"$ref": "s.outputs.value"},
                    "b": {"$ref": "p.outputs.value"},
                },
                declared_outputs=["value"],
                refine=False,
            ),
        ],
        edges=[EdgeSpec(src="s", dst="t"), EdgeSpec(src="p", dst="t")],
    )


def test_compile_and_execute_parallel_branch():
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    graph, history = compile_task(root, registry, MockLLM([_parallel_spec()]))
    assert [node_id for node_id in graph.node_ids()] 
    assert set(graph.node_ids()) == {"s", "p", "t"}
    assert len(history) == 2
    metrics = execute(graph, registry)
    assert metrics.max_parallel >= 2
    assert metrics.waves == 2
    assert graph.get("t").outputs == {"value": 25}
    assert graph.get("s").status == NodeStatus.done


def test_thread_wave_overlaps():
    registry = ToolRegistry()
    spans: list[tuple[str, float, float]] = []

    def slow(name: str):
        def fn() -> dict:
            start = time.perf_counter()
            time.sleep(0.3)
            spans.append((name, start, time.perf_counter()))
            return {"value": 1}

        return fn

    registry.register(slow("a"), name="ta", description="slow a")
    registry.register(slow("b"), name="tb", description="slow b")
    graph = TaskGraph()
    graph.add_node(TaskNode(id="a", name="a", tool_name="ta", declared_outputs=["value"], refine=False))
    graph.add_node(TaskNode(id="b", name="b", tool_name="tb", declared_outputs=["value"], refine=False))
    metrics = execute(graph, registry)
    assert metrics.max_parallel == 2
    assert len(spans) == 2
    _name_a, start_a, end_a = spans[0]
    _name_b, start_b, end_b = spans[1]
    assert start_a < end_b and start_b < end_a


def test_dependent_tool_waits_and_failure_blocks_descendant():
    order: list[str] = []
    registry = ToolRegistry()

    def first() -> dict:
        order.append("first")
        return {"value": 1}

    def boom(value: int) -> dict:
        order.append("boom")
        raise RuntimeError("nope")

    def later(value: int) -> dict:
        order.append("later")
        return {"value": value}

    registry.register(first, name="first", description="first")
    registry.register(boom, name="boom", description="boom")
    registry.register(later, name="later", description="later")
    graph = TaskGraph()
    for node_id, tool in (("a", "first"), ("b", "boom"), ("c", "later")):
        inputs = {} if node_id == "a" else {"value": {"$ref": f"{'a' if node_id == 'b' else 'b'}.outputs.value"}}
        graph.add_node(
            TaskNode(
                id=node_id,
                name=node_id,
                tool_name=tool,
                inputs=inputs,
                declared_outputs=["value"],
                refine=False,
            )
        )
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    metrics = execute(graph, registry)
    assert order == ["first", "boom"]
    assert metrics.failures == 1
    assert graph.get("c").status == NodeStatus.pending
    assert "nope" in (graph.get("b").error or "")


def test_short_ref_is_a_compile_error_and_tools_do_not_run():
    registry = ToolRegistry()
    seen: list[tuple[int, int]] = []

    def add(a: int, b: int) -> dict:
        seen.append((a, b))
        return {"value": a + b}

    registry.register(add, name="add", description="Add two integers")
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    spec = Decomposition(
        nodes=[
            ChildNode(
                id="add_step",
                name="add",
                tool_name="add",
                inputs={"a": 1, "b": 2},
                declared_outputs=["value"],
                refine=False,
            ),
            ChildNode(
                id="sink",
                name="sink",
                tool_name="add",
                inputs={"a": {"$ref": "add_step.value"}, "b": 4},
                declared_outputs=["value"],
                refine=False,
            ),
        ],
        edges=[EdgeSpec(src="add_step", dst="sink")],
    )
    with pytest.raises(CompileError, match="sink"):
        compile_task(root, registry, MockLLM([spec]))
    assert seen == []


def test_edges_that_name_the_parent_are_ignored():
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    spec = _parallel_spec()
    spec.edges.append(EdgeSpec(src="t", dst="job"))
    graph, _history = compile_task(root, registry, MockLLM([spec]))
    assert ("t", "job") not in graph.edges()
    assert graph.get("t").outputs is None
    execute(graph, registry)
    assert graph.get("t").outputs == {"value": 25}


def test_depth_cap():
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    mock = MockLLM(
        [
            Decomposition(
                nodes=[
                    ChildNode(id="again", name="again", declared_outputs=["value"], refine=True)
                ]
            )
        ]
    )
    with pytest.raises(CompileError):
        compile_task(root, registry, mock, max_depth=1)


def test_rules_pass_and_judge_can_reject():
    registry = _registry()
    graph = TaskGraph()
    graph.add_node(
        TaskNode(
            id="s",
            name="sum",
            tool_name="add",
            inputs={"a": 1, "b": 1},
            declared_outputs=["value"],
            refine=False,
        )
    )
    assert structural_thought(graph, registry).ok
    judged = thought_experiment(
        graph,
        registry,
        MockLLM([JudgeVerdict(ok=False, reason="wrong tool for the job")]),
    )
    assert not judged.ok
    assert judged.judge_used
    assert thought_experiment(graph, registry, None).ok


def test_repair_freezes_successful_sibling_and_reruns_failure():
    calls = {"keep": 0, "work": 0}
    registry = ToolRegistry()

    def keep() -> dict:
        calls["keep"] += 1
        return {"value": 1}

    def work() -> dict:
        calls["work"] += 1
        if calls["work"] == 1:
            raise RuntimeError("boom")
        return {"value": 7}

    registry.register(keep, name="keep", description="keep")
    registry.register(work, name="work", description="work")
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    first = Decomposition(
        nodes=[
            ChildNode(
                id="keep",
                name="keep",
                tool_name="keep",
                declared_outputs=["value"],
                refine=False,
            ),
            ChildNode(
                id="work",
                name="work",
                tool_name="work",
                declared_outputs=["value"],
                refine=False,
            ),
        ]
    )
    again = Decomposition(
        nodes=[
            ChildNode(
                id="work2",
                name="work2",
                tool_name="work",
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )
    mock = MockLLM([first, again])
    result = run_task(root, registry, mock)
    assert any("RuntimeError: boom" in str(message) for message in mock.messages)
    assert calls == {"keep": 1, "work": 2}
    assert result.metrics.repairs == 1
    assert result.graph.get("keep").status == NodeStatus.frozen
    assert result.graph.get("work2").outputs == {"value": 7}
    assert "work" not in result.graph


def test_lca_is_the_shared_parent_not_the_root():
    graph = TaskGraph()
    graph.add_node(TaskNode(id="b", name="b", parent_id="plan"))
    graph.add_node(TaskNode(id="c", name="c", parent_id="plan"))
    from atg.history import GraphHistory

    history = GraphHistory()
    history.append(graph, "leaves")
    assert lowest_common_ancestor(["b", "c"], graph, history) == "plan"
    assert repair_region(["b"], graph, history) == {"b"}


def test_reset_for_repair_refuses_frozen_nodes():
    graph = TaskGraph()
    graph.add_node(TaskNode(id="a", name="a"))
    graph.transition("a", NodeStatus.ready)
    graph.transition("a", NodeStatus.running)
    graph.transition("a", NodeStatus.done, outputs={"value": 1})
    graph.reset_for_repair("a")
    assert graph.get("a").status == NodeStatus.pending
    assert graph.get("a").outputs is None
    graph.transition("a", NodeStatus.ready)
    graph.transition("a", NodeStatus.running)
    graph.transition("a", NodeStatus.done, outputs={"value": 1})
    graph.freeze("a")
    with pytest.raises(GraphError):
        graph.reset_for_repair("a")


def test_thought_failure_repairs_before_execution():
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    bad = Decomposition(
        nodes=[
            ChildNode(
                id="n",
                name="n",
                tool_name="missing",
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )
    good = Decomposition(
        nodes=[
            ChildNode(
                id="n2",
                name="n2",
                tool_name="add",
                inputs={"a": 2, "b": 3},
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )
    result = run_task(root, registry, MockLLM([bad, good]))
    assert result.thought.ok
    assert result.metrics.repairs == 1
    assert result.metrics.tool_calls == 1
    assert result.graph.get("n2").outputs == {"value": 5}


def test_unscoped_judge_rejection_does_not_repair():
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    spec = Decomposition(
        nodes=[
            ChildNode(
                id="n2",
                name="n2",
                tool_name="add",
                inputs={"a": 1, "b": 1},
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )
    result = run_task(
        root,
        registry,
        MockLLM([spec, JudgeVerdict(ok=False, reason="wrong tool for the job")]),
        judge=True,
    )
    assert not result.thought.ok
    assert result.metrics.repairs == 0
    assert result.metrics.tool_calls == 0
    assert result.metrics.judge_disagreements == 1


def test_running_node_fails_on_resume_without_calling_the_tool():
    registry = _registry()
    graph = TaskGraph()
    graph.add_node(
        TaskNode(
            id="n",
            name="n",
            tool_name="add",
            inputs={"a": 1, "b": 1},
            declared_outputs=["value"],
            refine=False,
        )
    )
    graph.transition("n", NodeStatus.ready)
    graph.transition("n", NodeStatus.running)
    metrics = execute(graph, registry)
    assert graph.get("n").status == NodeStatus.failed
    assert graph.get("n").error == "interrupted before completion"
    assert metrics.failures == 1
    assert metrics.tool_calls == 0


def test_save_history_keeps_the_previous_file_when_the_write_fails(tmp_path, monkeypatch):
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    _graph, history = compile_task(root, registry, MockLLM([_parallel_spec()]))
    path = tmp_path / "history.json"
    save_history(history, path)
    original = path.read_text(encoding="utf-8")

    def fail_write(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.write_text", fail_write)
    with pytest.raises(OSError):
        save_history(history, path)
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_name(path.name + ".tmp").exists()


def test_history_json_round_trip(tmp_path):
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    _graph, history = compile_task(root, registry, MockLLM([_parallel_spec()]))
    path = tmp_path / "history.json"
    save_history(history, path)
    loaded = load_history(path)
    assert len(loaded) == len(history)
    assert loaded[1].edges == history[1].edges
    assert {node.id for node in loaded[1].nodes} == {"s", "p", "t"}


def test_adapters_are_one_way_and_do_not_import_frameworks():
    registry = _registry()
    root = TaskNode(id="job", name="job", declared_outputs=["value"])
    llm = MockLLM([_parallel_spec()])
    node = as_langgraph_node(root, registry, llm)
    patch = node({"messages": []})
    assert patch["atg_ok"] is True
    assert patch["atg_outputs"]["t"]["value"] == 25
    forward = as_dspy_forward(
        root,
        registry,
        MockLLM([_parallel_spec()]),
    )
    assert forward(question="ignored")["ok"] is True
