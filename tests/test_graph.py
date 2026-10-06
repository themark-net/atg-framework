import sys

import pytest

import atg.graph as graph_module
from atg.graph import CycleError, GraphError, TaskGraph
from atg.types import NodeStatus, TaskNode


def _node(node_id: str, **kwargs) -> TaskNode:
    return TaskNode(id=node_id, name=kwargs.pop("name", node_id), **kwargs)


def _diamond() -> TaskGraph:
    graph = TaskGraph()
    for node_id in ("a", "b", "c", "d"):
        graph.add_node(_node(node_id))
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "d")
    graph.add_edge("c", "d")
    return graph


def test_topological_order_is_stable_for_a_diamond():
    assert _diamond().topological_order() == ["a", "b", "c", "d"]


def test_cycle_is_rejected_and_rolled_back():
    graph = TaskGraph()
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge("a", "b")
    with pytest.raises(CycleError) as raised:
        graph.add_edge("b", "a")
    assert "a" in raised.value.nodes and "b" in raised.value.nodes
    assert graph.edges() == (("a", "b"),)


def test_self_loop_and_duplicate_node_and_edge():
    graph = TaskGraph()
    graph.add_node(_node("a"))
    with pytest.raises(CycleError):
        graph.add_edge("a", "a")
    with pytest.raises(GraphError):
        graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge("a", "b")
    with pytest.raises(GraphError):
        graph.add_edge("a", "b")


def test_freeze_only_from_done_and_satisfies_dependents():
    graph = TaskGraph()
    graph.add_node(_node("a"))
    graph.add_node(_node("b"))
    graph.add_edge("a", "b")
    with pytest.raises(GraphError):
        graph.freeze("a")
    graph.transition("a", NodeStatus.ready)
    graph.transition("a", NodeStatus.running)
    graph.transition("a", NodeStatus.done, outputs={"value": 1})
    graph.freeze("a")
    assert graph.get("a").status == NodeStatus.frozen
    assert graph.mark_ready() == ["b"]
    assert graph.get("b").status == NodeStatus.ready


def test_ready_set_runs_independent_branches_and_blocks_descendants_of_failure():
    graph = _diamond()
    assert graph.mark_ready() == ["a"]
    graph.transition("a", NodeStatus.running)
    graph.transition("a", NodeStatus.done, outputs={"value": 1})
    assert graph.mark_ready() == ["b", "c"]
    assert graph.mark_ready() == ["b", "c"]
    assert graph.get("b").status == NodeStatus.ready
    graph.transition("b", NodeStatus.running)
    graph.transition("b", NodeStatus.failed, error="boom")
    assert graph.get("b").error == "boom"
    assert graph.ready_ids() == ["c"]
    assert "d" not in graph.ready_ids()


def test_illegal_transitions():
    graph = TaskGraph()
    graph.add_node(_node("a"))
    with pytest.raises(GraphError):
        graph.transition("a", NodeStatus.done)
    graph.transition("a", NodeStatus.ready)
    graph.transition("a", NodeStatus.running)
    with pytest.raises(GraphError):
        graph.transition("a", NodeStatus.failed)
    graph.transition("a", NodeStatus.failed, error="x")
    with pytest.raises(GraphError):
        graph.transition("a", NodeStatus.pending)


def test_subgraph_is_induced_and_copy_is_independent():
    graph = _diamond()
    graph.transition("a", NodeStatus.ready)
    extracted = graph.subgraph({"a", "c"})
    assert extracted.edges() == (("a", "c"),)
    assert extracted.topological_order() == ["a", "c"]
    no_shortcut = graph.subgraph({"a", "d"})
    assert no_shortcut.edges() == ()
    cloned = graph.copy()
    cloned.transition("a", NodeStatus.running)
    assert graph.get("a").status == NodeStatus.ready
    assert cloned.get("a").status == NodeStatus.running


def test_nodes_are_frozen_and_owned_by_the_graph():
    graph = TaskGraph()
    original = _node("a")
    stored = graph.add_node(original)
    assert stored is graph.get("a")
    assert stored is not original
    with pytest.raises(Exception):
        stored.status = NodeStatus.ready  # type: ignore[misc]


def test_networkx_is_not_imported():
    assert "networkx" not in sys.modules
    assert "networkx" not in graph_module.__dict__
