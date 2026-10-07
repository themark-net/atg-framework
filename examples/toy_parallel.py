"""Compile and run a two-branch sum.

Offline (default) uses a scripted decomposition. ``--live`` asks the local
model in ``ATG_MODEL`` (default ``qwen2.5:14b``, Decision 0023).
``--client openai`` uses ``OpenAICompatClient`` (Decision 0021). The default
client is Ollama.

    uv run python examples/toy_parallel.py
    ATG_MODEL=llama3.1:8b uv run python examples/toy_parallel.py --live
    uv run python examples/toy_parallel.py --live --client openai
"""

import argparse
import os
import sys

from atg.llm import DEFAULT_MODEL, FALLBACK_MODELS, MockLLM, OllamaClient, OpenAICompatClient
from atg.planner import ChildNode, Decomposition, EdgeSpec
from atg.run import run_task
from atg.tools import ToolRegistry
from atg.types import TaskNode


def registry() -> ToolRegistry:
    tools = ToolRegistry()

    def add(a: int, b: int) -> dict:
        return {"value": a + b}

    def mul(a: int, b: int) -> dict:
        return {"value": a * b}

    tools.register(
        add,
        name="add",
        description="Add integers a and b. Returns value.",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    )
    tools.register(
        mul,
        name="mul",
        description="Multiply integers a and b. Returns value.",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    )
    return tools


def scripted() -> Decomposition:
    return Decomposition(
        nodes=[
            ChildNode(
                id="s",
                name="sum",
                tool_name="add",
                inputs={"a": 2, "b": 3},
                declared_outputs=["value"],
                refine=False,
            ),
            ChildNode(
                id="p",
                name="prod",
                tool_name="mul",
                inputs={"a": 4, "b": 5},
                declared_outputs=["value"],
                refine=False,
            ),
            ChildNode(
                id="t",
                name="total",
                tool_name="add",
                inputs={
                    "a": {"$ref": "s.outputs.value"},
                    "b": {"$ref": "p.outputs.value"},
                },
                declared_outputs=["value"],
                refine=False,
            ),
        ],
        edges=[EdgeSpec(src="s", dst="t"), EdgeSpec(src="p", dst="t")],
    )


def root() -> TaskNode:
    return TaskNode(
        id="job",
        name="Add 2 and 3, multiply 4 and 5, then add those two results.",
        declared_outputs=["value"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="call the selected local client")
    parser.add_argument(
        "--client",
        choices=("ollama", "openai"),
        default="ollama",
        help="live backend; openai is OpenAICompatClient (Decision 0021)",
    )
    parser.add_argument("--model", default=os.environ.get("ATG_MODEL", DEFAULT_MODEL))
    parser.add_argument("--only", action="store_true", help="do not try fallback tags")
    args = parser.parse_args(argv)
    tools = registry()
    task = root()
    if not args.live:
        result = run_task(task, tools, MockLLM([scripted()]))
        print(f"mock total={result.graph.get('t').outputs} waves={result.metrics.waves} parallel={result.metrics.max_parallel}")
        return 0
    fallbacks = [] if args.only else [name for name in FALLBACK_MODELS if name != args.model]
    models = [args.model, *fallbacks]
    errors: list[str] = []
    for model in models:
        try:
            if args.client == "openai":
                llm = OpenAICompatClient(model, timeout_s=180)
            else:
                llm = OllamaClient(model, timeout_s=180)
            result = run_task(task, tools, llm)
        except Exception as exc:
            errors.append(f"{model}: {type(exc).__name__}: {exc}")
            continue
        sinks = [node_id for node_id in result.graph.node_ids() if not result.graph.successors(node_id)]
        outputs = {node_id: result.graph.get(node_id).outputs for node_id in sinks}
        print(
            f"model={model} ok={result.thought.ok} repairs={result.metrics.repairs} "
            f"waves={result.metrics.waves} parallel={result.metrics.max_parallel} outputs={outputs}"
        )
        if result.thought.ok and result.metrics.failures == 0 and result.metrics.max_parallel >= 2:
            return 0
        errors.append(f"{model}: thought={result.thought.errors} failures={result.metrics.failures} outputs={outputs}")
    print("\n".join(errors), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
