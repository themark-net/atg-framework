"""End-to-end checks against the MVP success criteria (ARCHITECTURE §3.3)."""

from time import sleep

from atg.agent import ATGAgent
from atg.llm import MockLLMClient
from atg.runner import SequentialRunner, ThreadPoolRunner
from atg.tools import ToolRegistry, ToolSpec
from atg.types import NodeStatus, TaskSpec

SPEC = TaskSpec(
    description="Plan a weekend trip",
    inputs={"city": "Paris"},
    outputs={"itinerary": "Itinerary text"},
)

RETRY_HOTELS = {
    "nodes": [
        {
            "id": "hotels_retry",
            "tool_name": "search_hotels",
            "inputs": {"city": {"$parent": "city"}},
        }
    ],
    "output_bindings": {"result": "hotels_retry.outputs.result"},
}


def test_happy_path_runs_parallel_branches(trip_registry, trip_scripts, counter):
    agent = ATGAgent(
        trip_registry, MockLLMClient(structured=trip_scripts), runner=SequentialRunner()
    )
    result = agent.run(SPEC)
    assert result.ok and result.error is None
    assert result.outputs == {
        "itinerary": "sunny in Paris; stay Paris-hotel; do Paris-museum"
    }
    assert result.metrics.max_parallel == 3
    assert result.metrics.repairs == 0
    assert len(result.thought_reports) == 1 and result.thought_reports[0].ok
    assert counter.calls["compose"] == 1


def test_injected_failure_triggers_localized_repair(
    trip_registry, trip_scripts, counter
):
    counter.fail_first["search_hotels"] = 1
    scripts = {**trip_scripts, "hotels": RETRY_HOTELS}
    agent = ATGAgent(
        trip_registry, MockLLMClient(structured=scripts), runner=SequentialRunner()
    )
    result = agent.run(SPEC)

    assert result.ok
    assert result.metrics.repairs == 1
    assert [e.lca for e in result.repairs] == ["hotels"]
    assert result.metrics.nodes_frozen_reused == 2
    assert result.metrics.nodes_failed == 1
    # frozen successes were not re-called
    assert counter.calls == {
        "get_weather": 1,
        "search_activities": 1,
        "search_hotels": 2,
        "compose": 1,
    }
    events = result.metrics.events
    assert "run1:node_failed:hotels" in events
    assert "repair_started:hotels" in events and "repair_done:hotels" in events
    assert "run2:node_finished:hotels_retry" in events
    assert not any(e.startswith("run2:node_started:weather") for e in events)
    statuses = {n.id: n.status for n in result.plan.graph.nodes()}
    assert statuses["weather"] is NodeStatus.frozen
    assert statuses["compose"] is NodeStatus.done


def test_repair_budget_exhausted_returns_failure(trip_registry, trip_scripts, counter):
    counter.fail_first["search_hotels"] = 99
    scripts = {**trip_scripts, "hotels": RETRY_HOTELS}
    agent = ATGAgent(
        trip_registry,
        MockLLMClient(structured=scripts),
        runner=SequentialRunner(),
        max_repairs=1,
    )
    result = agent.run(SPEC)
    assert not result.ok
    assert result.metrics.repairs == 1
    assert len(result.executions) == 2
    assert "Failed nodes" in (result.error or "")
    assert result.outputs == {"itinerary": None}
    assert counter.calls["get_weather"] == 1
    assert counter.calls["search_hotels"] == 2


def test_thought_rejection_repairs_before_execution(trip_registry, counter):
    bad_root = {
        "nodes": [
            # wrong parameter name: thought experiment must catch this before running
            {
                "id": "weather",
                "tool_name": "get_weather",
                "inputs": {"town": {"$parent": "city"}},
            },
            {
                "id": "hotels",
                "tool_name": "search_hotels",
                "inputs": {"city": {"$parent": "city"}},
            },
            {
                "id": "activities",
                "tool_name": "search_activities",
                "inputs": {"city": {"$parent": "city"}},
            },
            {
                "id": "compose",
                "tool_name": "compose",
                "inputs": {
                    "weather": {"$ref": "weather.outputs.forecast"},
                    "hotels": {"$ref": "hotels.outputs.result"},
                    "activities": {"$ref": "activities.outputs.result"},
                },
            },
        ],
        "output_bindings": {"itinerary": "compose.outputs.result"},
    }
    fixed_weather = {
        "nodes": [
            {
                "id": "weather_ok",
                "tool_name": "get_weather",
                "inputs": {"city": "Paris"},
            }
        ],
        "output_bindings": {"forecast": "weather_ok.outputs.forecast"},
    }
    llm = MockLLMClient(structured={"root": bad_root, "weather": fixed_weather})
    result = ATGAgent(trip_registry, llm, runner=SequentialRunner()).run(SPEC)

    assert result.ok
    assert len(result.thought_reports) == 2
    assert not result.thought_reports[0].ok and result.thought_reports[1].ok
    assert [e.lca for e in result.repairs] == ["weather"]
    assert result.repairs[0].errors["weather"].startswith("missing_params")
    assert counter.calls["get_weather"] == 1
    assert any(e.startswith("thought_reject:weather") for e in result.metrics.events)
    assert result.outputs["itinerary"].startswith("sunny in Paris")


def test_parallel_runner_speeds_up_independent_branches(trip_scripts):
    reg = ToolRegistry()
    params = {"type": "object", "properties": {"city": {}}, "required": ["city"]}

    def slow(city):
        sleep(0.15)
        return city

    reg.register(
        ToolSpec(
            name="get_weather",
            parameters=params,
            returns={"properties": {"forecast": {}}},
        ),
        lambda city: (sleep(0.15), {"forecast": city})[1],
    )
    reg.register(ToolSpec(name="search_hotels", parameters=params), slow)
    reg.register(ToolSpec(name="search_activities", parameters=params), slow)
    reg.register(ToolSpec(name="compose"), lambda weather, hotels, activities: "ok")

    agent = ATGAgent(
        reg, MockLLMClient(structured=trip_scripts), runner=ThreadPoolRunner()
    )
    result = agent.run(SPEC)
    assert result.ok
    assert result.metrics.max_parallel == 3
    assert result.metrics.wall_time_s < 0.45
