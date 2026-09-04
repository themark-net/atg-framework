from atg.graph import GraphError, TaskGraph
from atg.types import NodeStatus, TaskNode


def _node(nid: str, **kwargs) -> TaskNode:
    return TaskNode(id=nid, name=nid, **kwargs)


def test_topo_linear():
    g = TaskGraph()
    g.add_node(_node("a"))
    g.add_node(_node("b"))
    g.add_node(_node("c"))
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    assert g.topological_order() == ["a", "b", "c"]
    assert g.is_acyclic()


def test_cycle_rejected_on_add_edge():
    g = TaskGraph()
    g.add_node(_node("a"))
    g.add_node(_node("b"))
    g.add_edge("a", "b")
    try:
        g.add_edge("b", "a")
        raise AssertionError("cycle should be rejected")
    except GraphError:
        pass
    assert g.edges() == [("a", "b")]
    assert g.is_acyclic()


def test_duplicate_node_rejected():
    g = TaskGraph()
    g.add_node(_node("a"))
    try:
        g.add_node(_node("a"))
        raise AssertionError("duplicate should be rejected")
    except GraphError:
        pass


def test_freeze_done_node():
    g = TaskGraph()
    g.add_node(_node("a", status=NodeStatus.done, outputs={"x": 1}))
    g.freeze("a")
    assert g.get("a").status is NodeStatus.frozen


def test_freeze_pending_rejected():
    g = TaskGraph()
    g.add_node(_node("a"))
    try:
        g.freeze("a")
        raise AssertionError("pending freeze should fail")
    except GraphError:
        pass


def test_ready_set_respects_predecessors():
    g = TaskGraph()
    g.add_node(_node("a", status=NodeStatus.done))
    g.add_node(_node("b"))
    g.add_node(_node("c"))
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    assert set(g.ready_set()) == {"b"}
    g.mark_status("b", NodeStatus.frozen)
    assert set(g.ready_set()) == {"c"}


def test_subgraph_and_copy():
    g = TaskGraph()
    g.add_node(_node("a"))
    g.add_node(_node("b"))
    g.add_node(_node("c"))
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    sub = g.subgraph(["a", "b"])
    assert set(sub.node_ids()) == {"a", "b"}
    assert sub.edges() == [("a", "b")]
    copied = g.copy()
    copied.mark_status("a", NodeStatus.done)
    assert g.get("a").status is NodeStatus.pending
