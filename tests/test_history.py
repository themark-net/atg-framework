from atg.graph import TaskGraph
from atg.history import GraphHistory
from atg.types import NodeStatus, TaskNode


def test_snapshot_roundtrip_and_immutability():
    g = TaskGraph()
    g.add_node(TaskNode(id="a", name="a"))
    g.add_node(TaskNode(id="b", name="b"))
    g.add_edge("a", "b")

    hist = GraphHistory()
    snap0 = hist.record(g, reason="initial")
    assert snap0.index == 0
    assert len(hist) == 1

    g.mark_status("a", NodeStatus.done)
    hist.record(g, reason="a-done")

    restored = hist.restore(0)
    assert restored.get("a").status is NodeStatus.pending
    assert g.get("a").status is NodeStatus.done
    assert hist.latest() is not None
    assert hist.latest().reason == "a-done"
