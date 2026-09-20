"""Weekend-trip demo: compile → thought experiment → parallel execute → repair.

Runs fully offline with a scripted ``MockLLMClient`` by default. Pass
``--real`` to plan with a real model through LiteLLM (``pip install
'atg-framework[llm]'`` and set ``ATG_MODEL``, e.g. ``ollama/<tag>``; Decision
0015). The hotel search tool fails on its first call so you can watch the
repair localize to that node and reuse the frozen weather/activities results.

ATG method: Zhang et al. (2026), arXiv:2607.01942 (zhang2026atg). This repo is
an independent reimplementation; see docs/ATTRIBUTION.md.

    python examples/weekend_trip.py
    python examples/weekend_trip.py --real
"""

from __future__ import annotations

import argparse
import json
import sys
from time import sleep

from atg import ATGAgent, MockLLMClient, TaskSpec, ToolRegistry, ToolSpec

CITY = {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}

SCRIPTS = {
    "root": {
        "rationale": "Weather, lodging and activities are independent; compose joins them.",
        "nodes": [
            {"id": "weather", "tool_name": "get_weather", "inputs": {"city": {"$parent": "city"}}},
            {"id": "lodging", "output_keys": ["hotels"], "inputs": {"city": {"$parent": "city"}}},
            {
                "id": "activities",
                "tool_name": "search_activities",
                "inputs": {"city": {"$parent": "city"}},
            },
            {
                "id": "compose",
                "tool_name": "compose_itinerary",
                "inputs": {
                    "weather": {"$ref": "weather.outputs.forecast"},
                    "hotels": {"$ref": "lodging.outputs.hotels"},
                    "activities": {"$ref": "activities.outputs.result"},
                },
            },
        ],
        "output_bindings": {"itinerary": "compose.outputs.result"},
    },
    "lodging": {
        "nodes": [
            {"id": "hotels", "tool_name": "search_hotels", "inputs": {"city": {"$parent": "city"}}}
        ],
        "output_bindings": {"hotels": "hotels.outputs.result"},
    },
    # Repair of the failed atomic node: same tool, fresh node (a retry).
    "hotels": {
        "nodes": [
            {
                "id": "hotels_retry",
                "tool_name": "search_hotels",
                "inputs": {"city": {"$parent": "city"}},
            }
        ],
        "output_bindings": {"result": "hotels_retry.outputs.result"},
    },
}


def build_registry(delay: float) -> tuple[ToolRegistry, dict[str, int]]:
    calls: dict[str, int] = {}
    reg = ToolRegistry()

    def hit(name: str) -> int:
        calls[name] = calls.get(name, 0) + 1
        sleep(delay)
        return calls[name]

    def get_weather(city: str) -> dict:
        hit("get_weather")
        return {"forecast": f"22°C and sunny in {city}"}

    def search_hotels(city: str) -> list[str]:
        if hit("search_hotels") == 1:
            raise RuntimeError("HTTP 503 from hotel provider")
        return [f"Hôtel {city} Centre", f"{city} Riverside Inn"]

    def search_activities(city: str) -> list[str]:
        hit("search_activities")
        return [f"{city} old town walk", f"{city} museum night"]

    def compose_itinerary(weather: str, hotels: list[str], activities: list[str]) -> str:
        hit("compose_itinerary")
        return f"Weather: {weather}. Stay at {hotels[0]}. Do: {', '.join(activities)}."

    reg.register(
        ToolSpec(
            name="get_weather",
            description="Weekend forecast for a city",
            parameters=CITY,
            returns={"type": "object", "properties": {"forecast": {"type": "string"}}},
        ),
        get_weather,
    )
    reg.register(
        ToolSpec(name="search_hotels", description="Hotels in a city", parameters=CITY),
        search_hotels,
    )
    reg.register(
        ToolSpec(name="search_activities", description="Things to do", parameters=CITY),
        search_activities,
    )
    reg.register(
        ToolSpec(
            name="compose_itinerary",
            description="Write the final itinerary text",
            parameters={
                "type": "object",
                "properties": {
                    "weather": {"type": "string"},
                    "hotels": {"type": "array"},
                    "activities": {"type": "array"},
                },
                "required": ["weather", "hotels", "activities"],
            },
        ),
        compose_itinerary,
    )
    return reg, calls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--real", action="store_true", help="plan with LiteLLM / ATG_MODEL")
    parser.add_argument("--city", default="Paris")
    parser.add_argument("--delay", type=float, default=0.2, help="simulated tool latency")
    args = parser.parse_args(argv)

    registry, calls = build_registry(args.delay)
    if args.real:
        from atg import LiteLLMClient

        llm = LiteLLMClient()
    else:
        llm = MockLLMClient(structured=SCRIPTS)

    agent = ATGAgent(registry, llm)
    spec = TaskSpec(
        description=f"Plan a weekend trip to {args.city}",
        inputs={"city": args.city},
        outputs={"itinerary": "Short itinerary text covering weather, hotel, activities"},
    )
    result = agent.run(spec)
    plan = result.plan
    assert plan is not None

    print("== outputs ==")
    print(json.dumps(result.outputs, indent=2, ensure_ascii=False))
    print("\n== metrics ==")
    print(json.dumps(result.metrics.model_dump(exclude={"events"}), indent=2))
    print("\n== tool calls ==", calls)
    print("\n== repairs ==")
    for event in result.repairs:
        print(f"  attempt {event.attempt}: failed={event.failed_ids} lca={event.lca} "
              f"region={event.region} frozen={event.frozen}")
    print("\n== history ==")
    for snap in plan.history.snapshots():
        print(f"  [{snap.index}] {snap.reason}: {len(snap.payload['nodes'])} nodes")
    print("\n== final graph (mermaid) ==")
    print(plan.graph.to_mermaid())
    if result.error:
        print("\nERROR:", result.error)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
