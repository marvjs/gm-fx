"""Append-only JSON-lines execution journal."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ExecutionJournal:
    def __init__(self, path: Path = Path("data/execution/demo_journal.jsonl")) -> None:
        self.path = path

    def append(self, event: str, **payload: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": datetime.now(UTC).isoformat(), "event": event, **payload}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
