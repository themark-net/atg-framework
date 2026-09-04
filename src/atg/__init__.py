"""atg-framework — independent prototype of Atomic Task Graph control ideas.

Inspired by Zhang et al. (2026), *Atomic Task Graph: A Unified Framework for
Agentic Planning and Execution*, arXiv:2607.01942. This package does **not**
propose ATG and is not an official implementation. See docs/ATTRIBUTION.md.
"""

from atg.graph import TaskGraph
from atg.history import GraphHistory, GraphSnapshot
from atg.tools import ToolRegistry, ToolSpec
from atg.types import InputRef, NodeStatus, TaskNode, TaskSpec
from atg.validation import ValidationError, validate_graph

__version__ = "0.1.0"
__attribution__ = (
    "ATG method: Zhang et al. (2026), arXiv:2607.01942. "
    "https://doi.org/10.48550/arXiv.2607.01942"
)

__all__ = [
    "GraphHistory",
    "GraphSnapshot",
    "InputRef",
    "NodeStatus",
    "TaskGraph",
    "TaskNode",
    "TaskSpec",
    "ToolRegistry",
    "ToolSpec",
    "ValidationError",
    "validate_graph",
    "__version__",
    "__attribution__",
]
