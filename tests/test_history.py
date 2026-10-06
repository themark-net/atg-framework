import pytest
from pydantic import ValidationError

from atg.graph import TaskGraph
from atg.history import GraphHistory
from atg.types import NodeStatus, TaskNode


def test_snapshot_is_isolated_from_later_graph_edits():
    graph = TaskGraph()
    graph.add_node(TaskNode(id="a", name="a"))
    graph.add_node(TaskNode(id="b", name="b"))
    graph.add_edge("a", "b")
    history = GraphHistory()
    first = history.append(graph, "initial")
    graph.transition("a", NodeStatus.ready)
    assert first.version == 1
    assert first.nodes[0].status == NodeStatus.pending
    assert first.to_graph().get("a").status == NodeStatus.pending
    second = history.append(graph, "marked ready")
    assert len(history) == 2
    assert history[1] is second
    assert second.nodes[0].status == NodeStatus.ready
    assert second.edges == (("a", "b"),)


def test_snapshot_fields_are_frozen_and_reason_is_required():
    graph = TaskGraph()
    graph.add_node(TaskNode(id="a", name="a"))
    history = GraphHistory()
    snap = history.append(graph, "init")
    with pytest.raises(ValidationError):
        snap.reason = "other"  # type: ignore[misc]
    with pytest.raises(ValueError):
        history.append(graph, "   ")
