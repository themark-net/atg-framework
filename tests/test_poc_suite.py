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


def test_one_bad_ref_fails_that_task_and_the_next_task_still_runs():
    suite = _load()
    bad = suite.Decomposition(
        nodes=[
            suite.ChildNode(
                id="sink",
                name="sink",
                tool_name="add",
                inputs={"a": {"$ref": "add_step.value"}, "b": 4},
                declared_outputs=["value"],
                refine=False,
            )
        ]
    )
    bad_task = suite.TaskSpec(
        id="badref",
        name="bad ref",
        expected=5,
        failed_once=False,
        plan=bad,
    )
    good = suite.TASKS[0]
    original = suite.TASKS
    suite.TASKS = [bad_task, good]

    def factory(task, arm):
        if task.id == "badref":
            return suite._CountingLLM(suite.MockLLM([bad]))
        return suite._offline_llm(task, arm)

    try:
        report = suite.run_suite(factory, offline=True)
    finally:
        suite.TASKS = original
    localized = report["arms"]["localized"]["tasks"]
    assert [row["id"] for row in localized] == ["badref", good.id]
    assert localized[0]["success"] is False
    assert localized[0]["plan_ok"] is False
    assert localized[0]["tool_calls"] == 0
    assert "CompileError" in localized[0]["error"]
    assert localized[1]["success"] is True
    assert report["arms"]["global_replan"]["tasks"][0]["tool_calls"] == 0
    assert report["arms"]["sequential"]["tasks"][0]["tool_calls"] == 0
