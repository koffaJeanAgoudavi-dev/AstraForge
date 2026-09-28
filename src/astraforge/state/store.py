"""SQLite-backed persistent execution state."""

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
                command TEXT, error TEXT, updated_at TEXT NOT NULL, context TEXT
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(runs)")}
            if "context" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN context TEXT")
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
            row = db.execute("SELECT id,name,description,requirements,status,created_at FROM projects WHERE id=?",
                             (project_id,)).fetchone()
        if not row:
            return None
        from datetime import datetime
        return ProjectSpec(id=row[0], name=row[1], description=row[2],
                           requirements=json.loads(row[3]), status=ProjectStatus(row[4]),
                           created_at=datetime.fromisoformat(row[5]))

    def start_run(self, project_id: str, command: list[str], stage: str = "planning") -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO runs(project_id,stage,status,command,updated_at,context) VALUES(?,?,?,?,?,?)",
                (project_id, stage, "running", json.dumps(command),
                 datetime.now(timezone.utc).isoformat(), "{}"))
            db.commit()
            return int(cursor.lastrowid)

    def update_run(self, run_id: int, *, stage: str, status: str, attempts: int = 0,
                   error: str | None = None, context: dict | None = None) -> None:
        with self._connect() as db:
            db.execute("UPDATE runs SET stage=?,status=?,attempts=?,error=?,updated_at=?,context=? WHERE id=?",
                       (stage, status, attempts, error, datetime.now(timezone.utc).isoformat(),
                        json.dumps(context or {}), run_id))
            db.commit()

    def get_latest_run(self, project_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT id,stage,status,attempts,command,error,updated_at,context "
                             "FROM runs WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()
        return self._run_dict(row) if row else None

    def find_resumable_run(self, project_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT id,stage,status,attempts,command,error,updated_at,context "
                             "FROM runs WHERE project_id=? AND status='running' ORDER BY id DESC LIMIT 1",
                             (project_id,)).fetchone()
        return self._run_dict(row) if row else None

    @staticmethod
    def _run_dict(row) -> dict:
        return {"id": row[0], "stage": row[1], "status": row[2], "attempts": row[3],
                "command": json.loads(row[4]) if row[4] else [], "error": row[5],
                "updated_at": row[6], "context": json.loads(row[7] or "{}")}
