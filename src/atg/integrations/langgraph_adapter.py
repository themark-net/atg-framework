"""Drop an ATG run into one LangGraph node. No LangGraph import.

Decision 0016: one-way. The callable returns a state patch. It does not
read or write LangGraph checkpoints. Revisit that if a graph must pause
mid-ATG and resume from LangGraph's saver.
"""

from typing import Any

from atg.run import run_task
from atg.tools import ToolRegistry
from atg.types import TaskNode


def as_langgraph_node(root: TaskNode, registry: ToolRegistry, llm: Any):
    def node(state: dict) -> dict:
        result = run_task(root, registry, llm)
        sinks = [
            node_id
            for node_id in result.graph.node_ids()
            if not result.graph.successors(node_id)
        ]
        outputs = {node_id: result.graph.get(node_id).outputs for node_id in sinks}
        return {
            "atg_outputs": outputs,
            "atg_metrics": result.metrics.model_dump(),
            "atg_ok": result.thought.ok and result.metrics.failures == 0,
            "state_seen": sorted(state),
        }

    return node
