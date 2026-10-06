import pytest
from pydantic import ValidationError

from atg.graph import TaskGraph
from atg.types import NodeStatus, TaskNode
from atg.validation import InterfaceError, assert_interface_preserved, assert_valid


def _graph() -> TaskGraph:
    graph = TaskGraph()
    graph.add_node(
        TaskNode(id="src", name="src", declared_outputs=["city"])
    )
    graph.add_node(
        TaskNode(
            id="dst",
            name="dst",
            inputs={"city": {"$ref": "src.outputs.city"}},
            declared_outputs=["advice"],
        )
    )
    graph.add_edge("src", "dst")
    return graph


def test_closed_graph_refs_round_trip_and_reject_bad_bindings():
    graph = _graph()
    assert_valid(graph)
    node = graph.get("dst")
    assert TaskNode.model_validate(node.model_dump()) == node
    with pytest.raises(ValidationError):
        TaskNode(id="bad.id", name="nope")
    with pytest.raises(ValidationError):
        TaskNode(id="n", name="n", inputs={"q": {"$ref": "not a ref"}})


def test_ref_must_be_an_ancestor_and_a_declared_field():
    graph = TaskGraph()
    graph.add_node(TaskNode(id="a", name="a", declared_outputs=["x"]))
    graph.add_node(
        TaskNode(id="b", name="b", inputs={"q": {"$ref": "a.outputs.missing"}})
    )
    graph.add_edge("a", "b")
    with pytest.raises(InterfaceError):
        assert_valid(graph)

    sideways = TaskGraph()
    sideways.add_node(TaskNode(id="a", name="a", declared_outputs=["x"]))
    sideways.add_node(TaskNode(id="b", name="b", declared_outputs=["x"]))
    sideways.add_node(
        TaskNode(id="c", name="c", inputs={"q": {"$ref": "b.outputs.x"}})
    )
    sideways.add_edge("a", "c")
    with pytest.raises(InterfaceError):
        assert_valid(sideways)


def test_produced_output_must_contain_the_ref_field():
    graph = _graph()
    graph.transition("src", NodeStatus.ready)
    graph.transition("src", NodeStatus.running)
    graph.transition("src", NodeStatus.done, outputs={"other": 1})
    with pytest.raises(InterfaceError):
        assert_valid(graph)


def test_interface_preservation():
    parent = TaskNode(
        id="plan",
        name="plan",
        inputs={"city": {"$ref": "src.outputs.city"}},
        declared_outputs=["advice"],
    )
    good = TaskGraph()
    good.add_node(
        TaskNode(
            id="lookup",
            name="lookup",
            inputs={"city": {"$ref": "src.outputs.city"}},
            declared_outputs=["facts"],
        )
    )
    good.add_node(
        TaskNode(
            id="write",
            name="write",
            inputs={"facts": {"$ref": "lookup.outputs.facts"}},
            declared_outputs=["advice"],
        )
    )
    good.add_edge("lookup", "write")
    assert_interface_preserved(parent, good)

    extra = TaskGraph()
    extra.add_node(
        TaskNode(
            id="lookup",
            name="lookup",
            inputs={"city": {"$ref": "other.outputs.city"}},
            declared_outputs=["advice"],
        )
    )
    with pytest.raises(InterfaceError):
        assert_interface_preserved(parent, extra)

    dropped = TaskGraph()
    dropped.add_node(
        TaskNode(
            id="write",
            name="write",
            inputs={"note": "literal"},
            declared_outputs=["advice"],
        )
    )
    with pytest.raises(InterfaceError):
        assert_interface_preserved(parent, dropped)
