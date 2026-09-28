"""Long-term memory for reusable engineering knowledge."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    def __init__(self, path: str | Path = ".astraforge/memory.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                key TEXT NOT NULL,
                content TEXT NOT NULL,
                project_id TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(kind, key)
            )""")
            db.commit()

    def remember(self, kind: str, key: str, content: dict | str, project_id: str | None = None) -> None:
        payload = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO memories(kind,key,content,project_id,created_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(kind,key) DO UPDATE SET
                   content=excluded.content, project_id=excluded.project_id""",
                (kind, key, payload, project_id, datetime.now(timezone.utc).isoformat()),
            )
            db.commit()

    def recall(self, kind: str | None = None, query: str | None = None, limit: int = 10) -> list[dict]:
        sql = "SELECT id,kind,key,content,project_id,created_at FROM memories WHERE 1=1"
        args = []
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        if query:
            sql += " AND (key LIKE ? OR content LIKE ?)"
            needle = f"%{query}%"
            args.extend([needle, needle])
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with sqlite3.connect(self.path) as db:
            rows = db.execute(sql, args).fetchall()
        return [
            {"id": r[0], "kind": r[1], "key": r[2], "content": r[3],
             "project_id": r[4], "created_at": r[5]}
            for r in rows
        ]
