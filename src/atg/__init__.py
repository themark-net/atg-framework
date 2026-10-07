"""Atomic Task Graph control library.

Independent reimplementation of concepts from Zhang et al. (2026),
Atomic Task Graph, arXiv:2607.01942. BibTeX key ``zhang2026atg``.
Not an official release from the paper authors.
Policy: docs/ATTRIBUTION.md.
"""

from atg.executor import execute
from atg.graph import CycleError, GraphError, TaskGraph
from atg.history import GraphHistory, GraphSnapshot
from atg.llm import DEFAULT_MODEL, LLMError, MockLLM, OllamaClient, OpenAICompatClient
from atg.metrics import Metrics
from atg.persist import load_history, save_history
from atg.planner import CompileError, Decomposition, compile_task
from atg.repair import RepairError, repair_graph
from atg.run import RunResult, run_task
from atg.thought import ThoughtReport, thought_experiment
from atg.tools import RegisteredTool, ToolError, ToolRegistry, ToolSchema, is_atomic
from atg.types import NodeStatus, Ref, TaskNode, parse_ref
from atg.validation import InterfaceError, assert_interface_preserved, assert_refs, assert_valid

__version__ = "0.2.0"

__all__ = [
    "CompileError",
    "CycleError",
    "DEFAULT_MODEL",
    "Decomposition",
    "GraphError",
    "GraphHistory",
    "GraphSnapshot",
    "InterfaceError",
    "LLMError",
    "Metrics",
    "MockLLM",
    "NodeStatus",
    "OllamaClient",
    "OpenAICompatClient",
    "Ref",
    "RegisteredTool",
    "RepairError",
    "RunResult",
    "TaskGraph",
    "TaskNode",
    "ThoughtReport",
    "ToolError",
    "ToolRegistry",
    "ToolSchema",
    "assert_interface_preserved",
    "assert_refs",
    "assert_valid",
    "compile_task",
    "execute",
    "is_atomic",
    "load_history",
    "parse_ref",
    "repair_graph",
    "run_task",
    "save_history",
    "thought_experiment",
]
