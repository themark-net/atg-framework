"""atg-framework — independent prototype of Atomic Task Graph control ideas.

Inspired by Zhang et al. (2026), *Atomic Task Graph: A Unified Framework for
Agentic Planning and Execution*, arXiv:2607.01942. This package does **not**
propose ATG and is not an official implementation. See docs/ATTRIBUTION.md.
"""

from atg.agent import AgentResult, ATGAgent
from atg.executor import ExecutionError, ExecutionResult, GraphExecutor
from atg.graph import GraphError, TaskGraph
from atg.history import GraphHistory, GraphSnapshot
from atg.llm import LiteLLMClient, LLMClient, LLMError, MockLLMClient
from atg.metrics import RunMetrics
from atg.planner import CompiledPlan, Decomposition, PlanError, PlannedNode, Planner
from atg.repair import Repairer, RepairError, RepairEvent
from atg.runner import ParallelRunner, SequentialRunner, ThreadPoolRunner
from atg.thought import ThoughtExperiment, ThoughtIssue, ThoughtReport
from atg.tools import ToolRegistry, ToolSpec
from atg.types import InputRef, NodeStatus, TaskNode, TaskSpec
from atg.validation import ValidationError, validate_graph

__version__ = "0.1.0"
__attribution__ = "ATG method: Zhang et al. (2026), arXiv:2607.01942. https://doi.org/10.48550/arXiv.2607.01942"

__all__ = [
    "ATGAgent",
    "AgentResult",
    "CompiledPlan",
    "Decomposition",
    "ExecutionError",
    "ExecutionResult",
    "GraphError",
    "GraphExecutor",
    "GraphHistory",
    "GraphSnapshot",
    "InputRef",
    "LLMClient",
    "LLMError",
    "LiteLLMClient",
    "MockLLMClient",
    "NodeStatus",
    "ParallelRunner",
    "PlanError",
    "PlannedNode",
    "Planner",
    "RepairError",
    "RepairEvent",
    "Repairer",
    "RunMetrics",
    "SequentialRunner",
    "TaskGraph",
    "TaskNode",
    "TaskSpec",
    "ThoughtExperiment",
    "ThoughtIssue",
    "ThoughtReport",
    "ThreadPoolRunner",
    "ToolRegistry",
    "ToolSpec",
    "ValidationError",
    "validate_graph",
    "__version__",
    "__attribution__",
]
