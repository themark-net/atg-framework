from pathlib import Path

import atg

ROOT = Path(__file__).resolve().parents[1]


def test_license_is_mit():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    assert "Copyright (c) 2026 themark-net" in text


def test_package_exports_version_and_attribution():
    assert atg.__version__ == "0.2.0"
    text = atg.__doc__ or ""
    assert "Zhang et al." in text
    assert "2607.01942" in text
    assert "official" in text
    assert atg.DEFAULT_MODEL == "qwen2.5:14b"
    assert callable(atg.run_task)
    assert callable(atg.compile_task)
    assert callable(atg.repair_graph)
