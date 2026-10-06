"""One callable shaped like a DSPy module ``forward``. No DSPy import.

Decision 0016. Arguments are ignored; the ATG root already carries the
task. Revisit if a DSPy signature must map field-by-field into ``TaskNode``.
"""

from typing import Any

from atg.run import run_task
from atg.tools import ToolRegistry
from atg.types import TaskNode


def as_dspy_forward(root: TaskNode, registry: ToolRegistry, llm: Any):
    def forward(**kwargs: Any) -> dict:
        result = run_task(root, registry, llm)
        return {
            "metrics": result.metrics.model_dump(),
            "ok": result.thought.ok and result.metrics.failures == 0,
            "ignored_kwargs": sorted(kwargs),
        }

    return forward
