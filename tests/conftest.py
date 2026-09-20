"""Shared synthetic-tool fixtures (Decision 0004: mocks, no real LLM)."""

from __future__ import annotations

from typing import Any

import pytest

from atg.tools import ToolRegistry, ToolSpec

CITY_PARAMS = {
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"],
}


class Counter:
    """Tracks tool invocations and optionally fails the first N calls of a tool."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {}
        self.fail_first: dict[str, int] = {}

    def hit(self, name: str) -> int:
        self.calls[name] = self.calls.get(name, 0) + 1
        if self.calls[name] <= self.fail_first.get(name, 0):
            raise RuntimeError(f"{name} failed (call {self.calls[name]})")
        return self.calls[name]


@pytest.fixture
def counter() -> Counter:
    return Counter()


@pytest.fixture
def trip_registry(counter: Counter) -> ToolRegistry:
    reg = ToolRegistry()

    def get_weather(city: str) -> dict[str, Any]:
        counter.hit("get_weather")
        return {"forecast": f"sunny in {city}"}

    def search_hotels(city: str) -> list[str]:
        counter.hit("search_hotels")
        return [f"{city}-hotel"]

    def search_activities(city: str) -> list[str]:
        counter.hit("search_activities")
        return [f"{city}-museum"]

    def compose(weather: str, hotels: list[str], activities: list[str]) -> str:
        counter.hit("compose")
        return f"{weather}; stay {hotels[0]}; do {activities[0]}"

    reg.register(
        ToolSpec(
            name="get_weather",
            parameters=CITY_PARAMS,
            returns={"type": "object", "properties": {"forecast": {"type": "string"}}},
        ),
        get_weather,
    )
    reg.register(ToolSpec(name="search_hotels", parameters=CITY_PARAMS), search_hotels)
    reg.register(
        ToolSpec(name="search_activities", parameters=CITY_PARAMS), search_activities
    )
    reg.register(
        ToolSpec(
            name="compose",
            parameters={
                "type": "object",
                "properties": {"weather": {}, "hotels": {}, "activities": {}},
                "required": ["weather", "hotels", "activities"],
            },
        ),
        compose,
    )
    reg.register(ToolSpec(name="blackbox", refine=False), lambda prompt: "bb")
    return reg


ROOT_DECOMP = {
    "nodes": [
        {
            "id": "weather",
            "tool_name": "get_weather",
            "inputs": {"city": {"$parent": "city"}},
        },
        {
            "id": "lodging",
            "output_keys": ["hotels"],
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
                "hotels": {"$ref": "lodging.outputs.hotels"},
                "activities": {"$ref": "activities.outputs.result"},
            },
        },
    ],
    "output_bindings": {"itinerary": "compose.outputs.result"},
}

LODGING_DECOMP = {
    "nodes": [
        {
            "id": "hotels",
            "tool_name": "search_hotels",
            "inputs": {"city": {"$parent": "city"}},
        }
    ],
    "output_bindings": {"hotels": "hotels.outputs.result"},
}


@pytest.fixture
def trip_scripts() -> dict[str, Any]:
    return {"root": ROOT_DECOMP, "lodging": LODGING_DECOMP}
