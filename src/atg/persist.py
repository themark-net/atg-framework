"""JSON checkpoints of full graph snapshots (Decision 0015).

In-memory history stays the runtime store (Decision 0009). JSON is the
next store. SQLite and vector search wait on the revisit triggers in
that decision. Independent reimplementation; see docs/ATTRIBUTION.md.
"""

import json
from pathlib import Path

from atg.history import GraphHistory


def save_history(history: GraphHistory, path: str | Path) -> None:
    """Write the checkpoint by replace, so a failed write leaves the old file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(json.dumps(history.dump()), encoding="utf-8")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def load_history(path: str | Path) -> GraphHistory:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return GraphHistory.load(payload)
