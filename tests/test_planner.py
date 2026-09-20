import pytest

from atg.executor import GraphExecutor
from atg.llm import MockLLMClient
from atg.planner import Decomposition, PlanError, Planner
from atg.runner import SequentialRunner
from atg.types import TaskSpec

SPEC = TaskSpec(
    description="Plan a weekend trip",
    inputs={"city": "Paris"},
    outputs={"itinerary": "Itinerary text"},
)


def test_two_level_compile_preserves_interface(trip_registry, trip_scripts):
    planner = Planner(trip_registry, MockLLMClient(structured=trip_scripts))
    plan = planner.compile(SPEC)

    assert plan.is_atomic(trip_registry)
    assert set(plan.graph.node_ids()) == {"weather", "hotels", "activities", "compose"}
    # abstract 'lodging' was replaced and its consumer rewired to the atomic child
    assert plan.graph.get("compose").inputs["hotels"] == {
        "$ref": "hotels.outputs.result"
    }
    assert plan.output_bindings == {"itinerary": "compose.outputs.result"}
    assert set(plan.graph.edges()) == {
        ("weather", "compose"),
        ("hotels", "compose"),
        ("activities", "compose"),
    }
    # $parent inherited the literal city
    assert plan.graph.get("hotels").inputs == {"city": "Paris"}
    # history: initial + one snapshot per refinement (Decision 0009)
    assert [s.reason for s in plan.history.snapshots()] == [
        "initial",
        "refine:root",
        "refine:lodging",
    ]
    # lineage survives replacement of the abstract parent
    assert plan.lineage("hotels") == ["hotels", "lodging", "root"]
    assert plan.region("lodging") == {"hotels"}
    assert plan.records["lodging"].bindings == {"hotels": "hotels.outputs.result"}
    # the LLM saw the node id and depth in context
    llm_calls = planner.llm.calls
    assert [c["context"]["node_id"] for c in llm_calls] == ["root", "lodging"]
    assert llm_calls[1]["context"]["depth"] == 1


def test_compiled_plan_executes_and_resolves_task_outputs(trip_registry, trip_scripts):
    plan = Planner(trip_registry, MockLLMClient(structured=trip_scripts)).compile(SPEC)
    result = GraphExecutor(trip_registry, runner=SequentialRunner()).run(plan.graph)
    assert result.ok
    assert result.metrics.max_parallel == 3
    assert plan.task_outputs() == {
        "itinerary": "sunny in Paris; stay Paris-hotel; do Paris-museum"
    }


def test_missing_output_binding_rejected(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    decomp = Decomposition(
        nodes=[{"id": "w", "tool_name": "get_weather", "inputs": {"city": "Paris"}}],
        output_bindings={},
    )
    with pytest.raises(PlanError, match="Interface not preserved"):
        planner.splice(plan, "root", decomp)
    # failed splice leaves plan untouched
    assert plan.graph.node_ids() == ["root"]
    assert len(plan.history) == 1


def test_binding_to_undeclared_child_output_rejected(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    decomp = Decomposition(
        nodes=[{"id": "w", "tool_name": "get_weather", "inputs": {"city": "Paris"}}],
        output_bindings={"itinerary": "w.outputs.nope"},
    )
    with pytest.raises(PlanError, match="does not expose 'nope'"):
        planner.splice(plan, "root", decomp)


def test_unknown_tool_and_bad_parent_input_rejected(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    with pytest.raises(PlanError, match="unknown tool"):
        planner.splice(
            plan,
            "root",
            Decomposition(
                nodes=[{"id": "x", "tool_name": "nope"}],
                output_bindings={"itinerary": "x.outputs.result"},
            ),
        )
    with pytest.raises(PlanError, match="unknown parent input"):
        planner.splice(
            plan,
            "root",
            Decomposition(
                nodes=[
                    {
                        "id": "x",
                        "tool_name": "get_weather",
                        "inputs": {"city": {"$parent": "country"}},
                    }
                ],
                output_bindings={"itinerary": "x.outputs.forecast"},
            ),
        )
    with pytest.raises(PlanError, match="must declare output_keys"):
        planner.splice(
            plan,
            "root",
            Decomposition(
                nodes=[{"id": "abstract"}],
                output_bindings={"itinerary": "abstract.outputs.x"},
            ),
        )


def test_refine_false_tool_is_atomic_and_not_expanded(trip_registry):
    scripts = {
        "root": {
            "nodes": [
                {"id": "bb", "tool_name": "blackbox", "inputs": {"prompt": "go"}}
            ],
            "output_bindings": {"itinerary": "bb.outputs.result"},
        }
    }
    llm = MockLLMClient(structured=scripts)
    plan = Planner(trip_registry, llm).compile(SPEC)
    assert plan.graph.get("bb").refine is False
    assert plan.is_atomic(trip_registry)
    assert [c["context"]["node_id"] for c in llm.calls] == ["root"]


def test_child_id_clash_is_namespaced(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    children = planner.splice(
        plan,
        "root",
        Decomposition(
            nodes=[
                {"id": "root", "tool_name": "get_weather", "inputs": {"city": "Paris"}}
            ],
            output_bindings={"itinerary": "root.outputs.forecast"},
        ),
    )
    assert children == ["root/root"]
    assert plan.output_bindings == {"itinerary": "root/root.outputs.forecast"}


def test_depth_cap_raises_with_diagnostics(trip_registry):
    def forever(messages, schema, ctx):
        nid = ctx["node_id"]
        return {
            "nodes": [{"id": f"{nid}_sub", "output_keys": ["itinerary"]}],
            "output_bindings": {"itinerary": f"{nid}_sub.outputs.itinerary"},
        }

    planner = Planner(trip_registry, MockLLMClient(structured=forever), max_depth=3)
    with pytest.raises(PlanError, match="max_depth=3"):
        planner.compile(SPEC)


def test_cycle_in_decomposition_rejected(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    decomp = Decomposition(
        nodes=[
            {"id": "a", "tool_name": "get_weather", "inputs": {"city": "Paris"}},
            {"id": "b", "tool_name": "get_weather", "inputs": {"city": "Paris"}},
        ],
        edges=[["a", "b"], ["b", "a"]],
        output_bindings={"itinerary": "b.outputs.forecast"},
    )
    with pytest.raises(PlanError, match="not a DAG"):
        planner.splice(plan, "root", decomp)
    assert plan.graph.node_ids() == ["root"]


def test_prompt_contains_tools_node_and_failure_context(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    messages = planner.build_messages(
        plan, plan.graph.get("root"), {"failure": {"errors": {"x": "boom"}}}
    )
    body = messages[1]["content"]
    assert '"get_weather"' in body
    assert '"node_to_refine"' in body and '"itinerary"' in body
    assert '"previous_failure"' in body and "boom" in body
    assert '"refine": false' in body  # blackbox tool marker
