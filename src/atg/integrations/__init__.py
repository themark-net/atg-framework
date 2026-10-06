"""One-way adapters. Core does not import DSPy or LangGraph (Decision 0002, 0016)."""

from atg.integrations.dspy_adapter import as_dspy_forward
from atg.integrations.langgraph_adapter import as_langgraph_node

__all__ = ["as_dspy_forward", "as_langgraph_node"]
