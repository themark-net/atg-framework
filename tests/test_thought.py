from atg.llm import MockLLMClient
from atg.planner import Planner
from atg.thought import ThoughtExperiment
from atg.types import TaskNode, TaskSpec

SPEC = TaskSpec(
    description="trip", inputs={"city": "Paris"}, outputs={"itinerary": "text"}
)


def test_clean_plan_passes(trip_registry, trip_scripts):
    plan = Planner(trip_registry, MockLLMClient(structured=trip_scripts)).compile(SPEC)
    report = ThoughtExperiment(trip_registry).check(plan)
    assert report.ok, report.issues


def test_structural_rules_flag_params_and_output_fields(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    plan.graph.remove_node("root")
    plan.graph.add_node(
        TaskNode(id="w", name="w", tool_name="get_weather", inputs={"town": "Paris"})
    )
    plan.graph.add_node(
        TaskNode(
            id="c",
            name="c",
            tool_name="compose",
            inputs={
                "weather": {"$ref": "w.outputs.temperature"},
                "hotels": [],
                "activities": [],
            },
        )
    )
    plan.graph.add_node(TaskNode(id="abstract", name="abstract", output_keys=["x"]))
    plan.graph.add_edge("w", "c")

    report = ThoughtExperiment(trip_registry).check(plan)
    codes = {(i.node_id, i.code) for i in report.issues}
    assert ("w", "missing_params") in codes
    assert ("w", "unknown_params") in codes
    assert ("c", "unknown_output_field") in codes
    assert ("abstract", "non_atomic") in codes
    assert set(report.node_ids()) == {"w", "c", "abstract"}
    assert "missing_params" in report.messages_by_node()["w"]


def test_invalid_graph_reported_as_wildcard(trip_registry):
    planner = Planner(trip_registry, MockLLMClient())
    plan = planner.initial_plan(SPEC)
    plan.graph.add_node(
        TaskNode(
            id="dangling",
            name="d",
            tool_name="compose",
            inputs={"weather": {"$ref": "ghost.outputs.x"}},
        )
    )
    report = ThoughtExperiment(trip_registry).check(plan)
    assert [i.code for i in report.issues] == ["invalid_graph"]
    assert report.node_ids() == ["*"]


def test_optional_llm_judge_runs_only_after_rules_pass(trip_registry, trip_scripts):
    plan = Planner(trip_registry, MockLLMClient(structured=trip_scripts)).compile(SPEC)
    judge = MockLLMClient(
        structured=[
            {
                "ok": False,
                "issues": [
                    {
                        "node_id": "activities",
                        "code": "wrong_tool",
                        "message": "use museums",
                    },
                    {
                        "node_id": "ghost",
                        "code": "x",
                        "message": "ignored: not in graph",
                    },
                ],
            }
        ]
    )
    report = ThoughtExperiment(trip_registry, judge=judge).check(plan)
    assert [i.node_id for i in report.issues] == ["activities"]
    assert judge.calls[0]["context"] == {"reason": "thought_judge"}
