import pytest

from atg.executor import ExecutionError, GraphExecutor
from atg.llm import MockLLMClient
from atg.planner import Planner
from atg.repair import Repairer, RepairError
from atg.runner import SequentialRunner
from atg.types import NodeStatus, TaskSpec

SPEC = TaskSpec(
    description="trip", inputs={"city": "Paris"}, outputs={"itinerary": "text"}
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

TWO_HOTEL_SEARCHES = {
    "nodes": [
        {
            "id": "hotels",
            "tool_name": "search_hotels",
            "inputs": {"city": {"$parent": "city"}},
        },
        {
            "id": "hostels",
            "tool_name": "search_hotels",
            "inputs": {"city": {"$parent": "city"}},
        },
    ],
    "output_bindings": {"hotels": "hotels.outputs.result"},
}


def _run_until_failure(registry, graph):
    with pytest.raises(ExecutionError) as ei:
        GraphExecutor(registry, runner=SequentialRunner()).run(graph)
    return ei.value.result


def test_single_failure_repairs_only_that_node_and_freezes_the_rest(
    trip_registry, trip_scripts, counter
):
    counter.fail_first["search_hotels"] = 1
    scripts = {**trip_scripts, "hotels": RETRY_HOTELS}
    planner = Planner(trip_registry, MockLLMClient(structured=scripts))
    plan = planner.compile(SPEC)

    first = _run_until_failure(trip_registry, plan.graph)
    assert first.failed_ids() == ["hotels"]
    assert "search_hotels failed" in plan.graph.get("hotels").metadata["error"]

    event = Repairer(planner).repair(plan, first.failed_ids())
    assert event.lca == "hotels"
    assert event.region == ["hotels"]
    assert sorted(event.frozen) == ["activities", "weather"]
    assert "search_hotels failed" in event.errors["hotels"]
    assert event.refinements == 1
    # the planner was told about the failure
    ctx = planner.llm.calls[-1]["context"]
    assert ctx["reason"] == "repair" and ctx["failure"]["failed_nodes"] == ["hotels"]
    assert planner.llm.calls[-1]["context"]["node_id"] == "hotels"
    # consumer rewired to the replacement node; frozen work untouched
    assert plan.graph.get("compose").inputs["hotels"] == {
        "$ref": "hotels_retry.outputs.result"
    }
    assert plan.graph.get("weather").status is NodeStatus.frozen
    assert plan.graph.get("weather").outputs == {"forecast": "sunny in Paris"}
    assert [s.reason for s in plan.history.snapshots()][-2:] == [
        "repair:localize:hotels",
        "repair:hotels",
    ]

    second = GraphExecutor(trip_registry, runner=SequentialRunner()).run(plan.graph)
    assert second.ok
    assert second.metrics.nodes_frozen_reused == 2
    assert counter.calls == {
        "get_weather": 1,
        "search_activities": 1,
        "search_hotels": 2,
        "compose": 1,
    }
    assert plan.task_outputs() == {
        "itinerary": "sunny in Paris; stay Paris-hotel; do Paris-museum"
    }


def test_two_failed_siblings_localize_to_their_parent(
    trip_registry, trip_scripts, counter
):
    counter.fail_first["search_hotels"] = 2
    scripts = {**trip_scripts, "lodging": [TWO_HOTEL_SEARCHES, trip_scripts["lodging"]]}
    planner = Planner(trip_registry, MockLLMClient(structured=scripts))
    plan = planner.compile(SPEC)
    assert {"hotels", "hostels"} <= set(plan.graph.node_ids())

    first = _run_until_failure(trip_registry, plan.graph)
    assert set(first.failed_ids()) == {"hotels", "hostels"}

    repairer = Repairer(planner)
    assert repairer.lca(plan, ["hotels", "hostels"]) == "lodging"
    event = repairer.repair(plan, first.failed_ids())
    assert event.lca == "lodging"
    assert event.region == ["hostels", "hotels"]
    # region replaced by the second scripted decomposition of 'lodging'
    assert "hostels" not in plan.graph and "hotels" in plan.graph
    assert plan.lineage("hotels") == ["hotels", "lodging", "root"]
    assert plan.graph.get("compose").inputs["hotels"] == {
        "$ref": "hotels.outputs.result"
    }
    assert "hostels" not in plan.records

    second = GraphExecutor(trip_registry, runner=SequentialRunner()).run(plan.graph)
    assert second.ok
    assert counter.calls["get_weather"] == 1
    assert counter.calls["search_hotels"] == 3


def test_repeated_failure_escalates_to_parent_region(
    trip_registry, trip_scripts, counter
):
    counter.fail_first["search_hotels"] = 2
    alt_lodging = {
        "nodes": [
            {
                "id": "hotels_v2",
                "tool_name": "search_hotels",
                "inputs": {"city": {"$parent": "city"}},
            }
        ],
        "output_bindings": {"hotels": "hotels_v2.outputs.result"},
    }
    scripts = {
        **trip_scripts,
        "lodging": [trip_scripts["lodging"], alt_lodging],
        "hotels": RETRY_HOTELS,
    }
    planner = Planner(trip_registry, MockLLMClient(structured=scripts))
    plan = planner.compile(SPEC)
    repairer = Repairer(planner, escalate_after=1)

    first = _run_until_failure(trip_registry, plan.graph)
    ev1 = repairer.repair(plan, first.failed_ids())
    assert ev1.lca == "hotels"

    second = _run_until_failure(trip_registry, plan.graph)
    assert second.failed_ids() == ["hotels_retry"]
    ev2 = repairer.repair(plan, second.failed_ids())
    assert ev2.lca == "lodging"
    assert ev2.region == ["hotels_retry"]
    assert "hotels_v2" in plan.graph
    assert plan.graph.get("compose").inputs["hotels"] == {
        "$ref": "hotels_v2.outputs.result"
    }

    third = GraphExecutor(trip_registry, runner=SequentialRunner()).run(plan.graph)
    assert third.ok
    assert counter.calls["get_weather"] == 1
    assert plan.graph.get("weather").status is NodeStatus.frozen
    assert len(plan.repair_log) == 2


def test_root_failure_is_full_replan(trip_registry, trip_scripts, counter):
    counter.fail_first["compose"] = 1
    scripts = {
        **trip_scripts,
        "compose": {
            "nodes": [
                {
                    "id": "compose2",
                    "tool_name": "compose",
                    "inputs": {
                        "weather": {"$parent": "weather"},
                        "hotels": {"$parent": "hotels"},
                        "activities": {"$parent": "activities"},
                    },
                }
            ],
            "output_bindings": {"result": "compose2.outputs.result"},
        },
    }
    planner = Planner(trip_registry, MockLLMClient(structured=scripts))
    plan = planner.compile(SPEC)
    first = _run_until_failure(trip_registry, plan.graph)
    assert first.failed_ids() == ["compose"]

    event = Repairer(planner).repair(plan, ["compose"])
    assert event.lca == "compose"
    assert sorted(event.frozen) == ["activities", "hotels", "weather"]
    # inherited $parent inputs keep the upstream refs, so edges are rebuilt
    assert set(plan.graph.predecessors("compose2")) == {
        "activities",
        "hotels",
        "weather",
    }
    assert plan.output_bindings == {"itinerary": "compose2.outputs.result"}

    GraphExecutor(trip_registry, runner=SequentialRunner()).run(plan.graph)
    assert plan.task_outputs()["itinerary"].startswith("sunny in Paris")
    assert counter.calls == {
        "get_weather": 1,
        "search_activities": 1,
        "search_hotels": 1,
        "compose": 2,
    }


def test_repair_requires_live_failed_nodes(trip_registry, trip_scripts):
    planner = Planner(trip_registry, MockLLMClient(structured=trip_scripts))
    plan = planner.compile(SPEC)
    with pytest.raises(RepairError):
        Repairer(planner).repair(plan, ["ghost"])
    with pytest.raises(RepairError):
        Repairer(planner).lca(plan, [])
