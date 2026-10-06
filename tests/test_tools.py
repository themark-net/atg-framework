import pytest
from pydantic import ValidationError

from atg.tools import ToolError, ToolRegistry, is_atomic
from atg.types import TaskNode


def _add(left: int, right: int) -> int:
    return left + right


def test_registry_binds_schema_and_callable_and_exports_openai_shape():
    registry = ToolRegistry()
    spec = registry.register(
        _add,
        description="Add two integers",
        parameters={
            "type": "object",
            "properties": {"left": {"type": "integer"}, "right": {"type": "integer"}},
            "required": ["left", "right"],
        },
    )
    assert spec.name == "_add"
    assert registry.get("_add").fn(left=2, right=3) == 5
    exported = registry.as_openai_tools()
    assert exported == [
        {
            "type": "function",
            "function": {
                "name": "_add",
                "description": "Add two integers",
                "parameters": spec.parameters,
            },
        }
    ]
    assert "fn" not in exported[0]["function"]


def test_duplicate_and_missing_and_bad_name():
    registry = ToolRegistry()
    registry.register(_add, name="add", description="add")
    with pytest.raises(ToolError):
        registry.register(_add, name="add", description="again")
    with pytest.raises(ToolError):
        registry.get("missing")
    with pytest.raises(ValidationError):
        registry.register(_add, name="bad.name", description="nope")


def test_atomicity_rules():
    registry = ToolRegistry()
    registry.register(_add, name="add", description="add", refine=False)
    registered = TaskNode(id="n1", name="n1", tool_name="add")
    forced = TaskNode(id="n2", name="n2", refine=False)
    abstract = TaskNode(id="n3", name="plan")
    unknown = TaskNode(id="n4", name="n4", tool_name="missing")
    assert is_atomic(registered, registry)
    assert is_atomic(forced, registry)
    assert is_atomic(forced, None)
    assert not is_atomic(abstract, registry)
    assert not is_atomic(unknown, registry)
    assert registry.get("add").spec.refine is False
