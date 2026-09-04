from atg.tools import ToolRegistry, ToolSpec, resolve_inputs
from atg.types import InputRef


def test_register_and_run():
    reg = ToolRegistry()
    spec = ToolSpec(
        name="add",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
            "required": ["x", "y"],
        },
    )
    reg.register(spec, lambda x, y: x + y)
    assert "add" in reg
    assert reg.run("add", x=2, y=3) == 5
    tools = reg.openai_tools()
    assert tools[0]["function"]["name"] == "add"


def test_refine_false_flag():
    reg = ToolRegistry()
    reg.register(ToolSpec(name="blackbox", refine=False), lambda prompt: "ok")
    assert reg.may_refine("blackbox") is False
    assert reg.may_refine("missing") is True


def test_duplicate_name_rejected():
    reg = ToolRegistry()
    reg.register(ToolSpec(name="echo"), lambda x: x)
    try:
        reg.register(ToolSpec(name="echo"), lambda x: x)
        raise AssertionError("duplicate should fail")
    except ValueError:
        pass


def test_resolve_literals_and_refs():
    inputs = {
        "city": "Paris",
        "text": {"$ref": "weather.outputs.forecast"},
    }
    bound = resolve_inputs(inputs, {"weather": {"forecast": "sunny"}})
    assert bound == {"city": "Paris", "text": "sunny"}

    ref = InputRef.from_path("n1", "score")
    assert ref.parse() == ("n1", "score")
