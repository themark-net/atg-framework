from atg.graph import TaskGraph
from atg.types import TaskNode
from atg.validation import ValidationError, validate_graph


def test_valid_graph_with_ref():
    g = TaskGraph()
    g.add_node(TaskNode(id="a", name="a", tool_name="get"))
    g.add_node(
        TaskNode(
            id="b",
            name="b",
            tool_name="use",
            inputs={"x": {"$ref": "a.outputs.val"}},
        )
    )
    g.add_edge("a", "b")
    validate_graph(g)


def test_dangling_ref_rejected():
    g = TaskGraph()
    g.add_node(
        TaskNode(
            id="b",
            name="b",
            inputs={"x": {"$ref": "missing.outputs.val"}},
        )
    )
    try:
        validate_graph(g)
        raise AssertionError("dangling ref should fail")
    except ValidationError:
        pass
