"""Persistent long-term memory with optional semantic retrieval."""

import json
import math
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
                embedding TEXT,
                UNIQUE(kind, key)
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(memories)")}
            if "embedding" not in columns:
                db.execute("ALTER TABLE memories ADD COLUMN embedding TEXT")
            db.commit()

    def remember(self, kind: str, key: str, content: dict | str, project_id: str | None = None,
                 embedding: list[float] | None = None) -> None:
        payload = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        vector = json.dumps(embedding) if embedding else None
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO memories(kind,key,content,project_id,created_at,embedding)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(kind,key) DO UPDATE SET
                   content=excluded.content, project_id=excluded.project_id,
                   created_at=excluded.created_at, embedding=excluded.embedding""",
                (kind, key, payload, project_id, datetime.now(timezone.utc).isoformat(), vector),
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
        return [self._row_to_dict(r) for r in rows]

    def semantic_recall(self, embedding: list[float], kind: str | None = None,
                        limit: int = 8, min_score: float = 0.35) -> list[dict]:
        sql = "SELECT id,kind,key,content,project_id,created_at,embedding FROM memories WHERE embedding IS NOT NULL"
        args = []
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        with sqlite3.connect(self.path) as db:
            rows = db.execute(sql, args).fetchall()

        ranked = []
        for row in rows:
            vector = json.loads(row[6])
            score = self._cosine(embedding, vector)
            if score >= min_score:
                item = self._row_to_dict(row[:6])
                item["score"] = round(score, 6)
                ranked.append(item)
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        numerator = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return numerator / (norm_a * norm_b)

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {"id": row[0], "kind": row[1], "key": row[2], "content": row[3],
                "project_id": row[4], "created_at": row[5]}
