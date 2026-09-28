"""SQLite-backed persistent execution state and build history."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from astraforge.projects.schemas import ProjectSpec, ProjectStatus


class StateStore:
    def __init__(self, path: str | Path = ".astraforge/state.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
                requirements TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
                stage TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                command TEXT, error TEXT, updated_at TEXT NOT NULL, context TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS build_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
                run_id INTEGER, timestamp TEXT NOT NULL, stage TEXT NOT NULL,
                status TEXT NOT NULL, message TEXT, metadata TEXT
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(runs)")}
            if "context" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN context TEXT")
            if "cancel_requested" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0")
            db.execute("CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id, id DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON build_events(project_id, id)")
            db.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def save_project(self, project: ProjectSpec) -> None:
        with self._connect() as db:
            db.execute("""INSERT INTO projects
                (id,name,description,requirements,status,created_at) VALUES (?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                description=excluded.description, requirements=excluded.requirements,
                status=excluded.status""",
                (project.id, project.name, project.description, json.dumps(project.requirements),
                 project.status.value, project.created_at.isoformat()))
            db.commit()

    def get_project(self, project_id: str) -> ProjectSpec | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id,name,description,requirements,status,created_at FROM projects WHERE id=?",
                (project_id,),
            ).fetchone()
        if not row:
            return None
        from datetime import datetime
        return ProjectSpec(
            id=row[0], name=row[1], description=row[2],
            requirements=json.loads(row[3]), status=ProjectStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
        )

    def start_run(self, project_id: str, command: list[str], stage: str = "planning") -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO runs(project_id,stage,status,command,updated_at,context,cancel_requested) VALUES(?,?,?,?,?,?,0)",
                (project_id, stage, "running", json.dumps(command),
                 datetime.now(timezone.utc).isoformat(), "{}"),
            )
            db.commit()
            return int(cursor.lastrowid)

    def update_run(
        self, run_id: int, *, stage: str, status: str, attempts: int = 0,
        error: str | None = None, context: dict | None = None,
    ) -> None:
        with self._connect() as db:
            db.execute(
                """UPDATE runs SET stage=?,status=?,attempts=?,error=?,updated_at=?,context=?
                   WHERE id=?""",
                (stage, status, attempts, error, datetime.now(timezone.utc).isoformat(),
                 json.dumps(context or {}), run_id),
            )
            db.commit()

    def request_cancel(self, run_id: int) -> bool:
        with self._connect() as db:
            cur = db.execute(
                "UPDATE runs SET cancel_requested=1,updated_at=? WHERE id=? AND status='running'",
                (datetime.now(timezone.utc).isoformat(), run_id),
            )
            db.commit()
            return cur.rowcount == 1

    def is_cancel_requested(self, run_id: int) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT cancel_requested FROM runs WHERE id=?", (run_id,)).fetchone()
        return bool(row and row[0])

    def get_run(self, run_id: int) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id,project_id,stage,status,attempts,command,error,updated_at,context,cancel_requested "
                "FROM runs WHERE id=?", (run_id,)
            ).fetchone()
        return self._run_dict(row) if row else None

    def list_runs(self, project_id: str, limit: int = 50) -> list[dict]:
        limit = max(1, min(limit, 200))
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,project_id,stage,status,attempts,command,error,updated_at,context,cancel_requested "
                "FROM runs WHERE project_id=? ORDER BY id DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        return [self._run_dict(row) for row in rows]

    def get_latest_run(self, project_id: str) -> dict | None:
        runs = self.list_runs(project_id, 1)
        return runs[0] if runs else None

    def find_resumable_run(self, project_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id,project_id,stage,status,attempts,command,error,updated_at,context,cancel_requested "
                "FROM runs WHERE project_id=? AND status='running' AND cancel_requested=0 "
                "ORDER BY id DESC LIMIT 1", (project_id,)
            ).fetchone()
        return self._run_dict(row) if row else None

    def append_event(
        self, project_id: str, stage: str, status: str,
        message: str | None = None, metadata: dict | None = None, run_id: int | None = None,
    ) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO build_events(project_id,run_id,timestamp,stage,status,message,metadata) VALUES(?,?,?,?,?,?,?)",
                (project_id, run_id, timestamp, stage, status, message, json.dumps(metadata or {})),
            )
            db.commit()
            event_id = int(cur.lastrowid)
        return {
            "id": event_id, "type": "stage", "project_id": project_id, "run_id": run_id,
            "timestamp": timestamp, "stage": stage, "status": status,
            "message": message, "metadata": metadata or {},
        }

    def list_events(self, project_id: str, after_id: int = 0, limit: int = 500) -> list[dict]:
        limit = max(1, min(limit, 1000))
        with self._connect() as db:
            rows = db.execute(
                """SELECT id,project_id,run_id,timestamp,stage,status,message,metadata
                   FROM build_events WHERE project_id=? AND id>? ORDER BY id ASC LIMIT ?""",
                (project_id, after_id, limit),
            ).fetchall()
        return [
            {"id": r[0], "type": "stage", "project_id": r[1], "run_id": r[2],
             "timestamp": r[3], "stage": r[4], "status": r[5], "message": r[6],
             "metadata": json.loads(r[7] or "{}")}
            for r in rows
        ]

    @staticmethod
    def _run_dict(row) -> dict:
        return {
            "id": row[0], "project_id": row[1], "stage": row[2], "status": row[3],
            "attempts": row[4], "command": json.loads(row[5]) if row[5] else [],
            "error": row[6], "updated_at": row[7], "context": json.loads(row[8] or "{}"),
            "cancel_requested": bool(row[9]),
        }
