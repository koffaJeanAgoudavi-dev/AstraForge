"""Execution event log stored alongside project state."""

from datetime import datetime, timezone
from pathlib import Path
import json


class EventLog:
    def __init__(self, path: str | Path = ".astraforge/events.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, project_id: str, event: str, data: dict | None = None) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "event": event,
            "data": data or {},
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")
