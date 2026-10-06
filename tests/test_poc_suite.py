"""Offline toy PoC. Calls the suite in-process. No network and no --live."""

import importlib.util
import json
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "examples" / "poc_suite.py"
    spec = importlib.util.spec_from_file_location("poc_suite", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_offline_poc_suite():
    suite = _load()
    suite.run_offline_suite()
    report = json.loads(suite.OFFLINE_JSON.read_text(encoding="utf-8"))
    markdown = suite.OFFLINE_MD.read_text(encoding="utf-8")
    assert report["mode"] == "offline"
    assert report["task_count"] == 12
    assert report["failed_once_count"] == 4
    assert set(report["arms"]) == {"localized", "global_replan", "sequential"}

    localized = report["arms"]["localized"]
    global_arm = report["arms"]["global_replan"]
    sequential = report["arms"]["sequential"]
    assert len(localized["tasks"]) == 12
    assert localized["success"] == global_arm["success"] == 12
    assert sequential["success"] == 12
    assert localized["llm_calls"] < global_arm["llm_calls"]
    assert localized["nodes_frozen_reused"] > 0
    assert sequential["max_parallel"] == 1
    assert all(row["max_parallel"] == 1 for row in sequential["tasks"])

    failed = [row for row in localized["tasks"] if row["failed_once"]]
    assert len(failed) == 4
    assert all(row["repairs"] >= 1 for row in failed)
    seq_by_id = {row["id"]: row for row in sequential["tasks"]}
    assert sum(seq_by_id[row["id"]]["tool_calls"] for row in failed) > sum(
        row["tool_calls"] for row in failed
    )
    assert "localized" in markdown and "global_replan" in markdown
    assert "sequential" in markdown
