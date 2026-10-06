"""Local model check. Not part of the default suite."""

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(os.environ.get("ATG_RUN_INTEGRATION") != "1", reason="set ATG_RUN_INTEGRATION=1")
def test_live_parallel_compile():
    completed = subprocess.run(
        [sys.executable, "examples/toy_parallel.py", "--live"],
        check=False,
    )
    assert completed.returncode == 0
