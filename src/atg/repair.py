"""Minimal necessary subgraph repair.

Implements concepts from Zhang et al. (2026), Atomic Task Graph, §4.3
(localize failures through the refinement history to the lowest common
historical ancestor of the failed atomic nodes; freeze validated regions;
re-plan only the affected subgraph). See docs/ATTRIBUTION.md and
docs/citations.bib (zhang2026atg). Independent reimplementation, not official.

First pass follows the OQ-0009 recommendation: explicit ``parent_id`` lineage
(``CompiledPlan.records``) plus history snapshots. Escalation policy (widen to
the parent after a region fails ``escalate_after`` times) is this repo's
engineering addition, tracked in OQ-0016.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from atg.planner import CompiledPlan, Planner, refs_in, rewrite_ref_string, rewrite_refs
from atg.types import InputRef, NodeStatus, TaskNode


class RepairError(RuntimeError):
    """Failure could not be localized or the region could not be re-abstracted."""


class RepairEvent(BaseModel):
    attempt: int
    failed_ids: list[str]
    errors: dict[str, str] = Field(default_factory=dict)
    lca: str
    region: list[str]
    frozen: list[str]
    refinements: int = 0


class Repairer:
    """Localize failed nodes to a history ancestor and recompile only that region."""

    def __init__(self, planner: Planner, escalate_after: int = 1) -> None:
        self.planner = planner
        self.escalate_after = escalate_after

    # ----- localization ------------------------------------------------

    def lca(self, plan: CompiledPlan, failed_ids: list[str]) -> str:
        """Deepest node common to every failed node's lineage."""
        if not failed_ids:
            raise RepairError("No failed nodes to localize")
        chains = [plan.lineage(f) for f in failed_ids]
        common = set(chains[0]).intersection(*chains[1:])
        for candidate in chains[0]:
            if candidate in common:
                return candidate
        raise RepairError(f"Failed nodes {failed_ids} share no ancestor")

    def localize(self, plan: CompiledPlan, failed_ids: list[str]) -> str:
        """LCA, widened to its parent once a region has been repaired too often."""
        lca = self.lca(plan, failed_ids)
        while self._repairs_of(plan, lca) >= self.escalate_after:
            parent = plan.records[lca].parent_id if lca in plan.records else None
            if parent is None:
                break
            lca = parent
        return lca

    def _repairs_of(self, plan: CompiledPlan, node_id: str) -> int:
        return sum(1 for event in plan.repair_log if event.get("lca") == node_id)

    # ----- repair ------------------------------------------------------

    def repair(
        self,
        plan: CompiledPlan,
        failed_ids: list[str],
        errors: dict[str, str] | None = None,
    ) -> RepairEvent:
        graph = plan.graph
        failed_ids = [f for f in failed_ids if f in graph]
        if not failed_ids:
            raise RepairError("None of the failed nodes are in the current graph")
        errors = dict(errors or {})
        for fid in failed_ids:
            err = graph.get(fid).metadata.get("error")
            if err and fid not in errors:
                errors[fid] = str(err)

        lca = self.localize(plan, failed_ids)
        region = plan.region(lca)
        if not region:
            raise RepairError(f"Ancestor {lca!r} has no live descendants to repair")
        record = plan.records.get(lca)
        if record is None:
            raise RepairError(f"No expansion record for {lca!r}")

        ext_preds: set[str] = set()
        ext_succs: set[str] = set()
        for nid in region:
            ext_preds |= set(graph.predecessors(nid)) - region
            ext_succs |= set(graph.successors(nid)) - region

        # Consumers that were rewired to descendants go back to the ancestor's interface.
        inverse: dict[tuple[str, str], str] = {
            InputRef(ref=ref).parse(): f"{lca}.outputs.{field}"
            for field, ref in record.bindings.items()
        }
        doomed = {nid for nid in plan.records if nid != lca and lca in plan.lineage(nid)}
        for node in graph.nodes():
            if node.id not in region:
                node.inputs = rewrite_refs(node.inputs, inverse)
        for rid, rec in plan.records.items():
            if rid in doomed:
                continue
            rec.inputs = rewrite_refs(rec.inputs, inverse)
            rec.bindings = {f: rewrite_ref_string(r, inverse) for f, r in rec.bindings.items()}
        plan.output_bindings = {
            f: rewrite_ref_string(r, inverse) for f, r in plan.output_bindings.items()
        }
        for node in graph.nodes():
            if node.id in region:
                continue
            for src_id, _field in refs_in(node.inputs):
                if src_id in region and src_id != lca:
                    raise RepairError(
                        f"Node {node.id!r} still references {src_id!r} inside repaired "
                        f"region {lca!r}; interface bookkeeping is inconsistent"
                    )

        output_keys = list(record.output_keys) or self._referenced_outputs(plan, lca, region)

        frozen: list[str] = []
        for node in graph.nodes():
            if node.id not in region and node.status is NodeStatus.done:
                graph.freeze(node.id)
                frozen.append(node.id)

        for nid in region:
            graph.remove_node(nid)
        for nid in doomed:
            plan.records.pop(nid, None)

        attempt = len(plan.repair_log) + 1
        graph.add_node(
            TaskNode(
                id=lca,
                name=record.name,
                inputs=dict(record.inputs),
                output_keys=output_keys,
                parent_id=record.parent_id,
                metadata={"depth": record.depth, "repair_attempt": attempt},
            )
        )
        record.bindings = {}
        record.output_keys = output_keys
        for pred in ext_preds:
            graph.add_edge(pred, lca)
        for succ in ext_succs:
            graph.add_edge(lca, succ)
        plan.history.record(graph, reason=f"repair:localize:{lca}")

        event = RepairEvent(
            attempt=attempt,
            failed_ids=failed_ids,
            errors=errors,
            lca=lca,
            region=sorted(region),
            frozen=sorted(frozen),
        )
        plan.repair_log.append(event.model_dump())

        context: dict[str, Any] = {
            "reason": "repair",
            "failure": {
                "attempt": attempt,
                "failed_nodes": failed_ids,
                "errors": errors,
                "replanned_region": sorted(region),
            },
        }
        event.refinements = self.planner.refine_until_atomic(plan, only_under=lca, context=context)
        plan.repair_log[-1]["refinements"] = event.refinements
        return event

    @staticmethod
    def _referenced_outputs(plan: CompiledPlan, lca: str, region: set[str]) -> list[str]:
        """Interface of an atomic node with no declared outputs: what consumers use."""
        fields: list[str] = []

        def note(src: str, field: str) -> None:
            if src == lca and field not in fields:
                fields.append(field)

        for node in plan.graph.nodes():
            if node.id in region:
                continue
            for src, field in refs_in(node.inputs):
                note(src, field)
        for ref in plan.output_bindings.values():
            note(*InputRef(ref=ref).parse())
        for rec in plan.records.values():
            for ref in rec.bindings.values():
                note(*InputRef(ref=ref).parse())
        return fields or ["result"]
