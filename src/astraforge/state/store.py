"""SQLite-backed project state store."""

import json
import sqlite3
from pathlib import Path

from astraforge.projects.schemas import ProjectSpec, ProjectStatus


class StateStore:
    def __init__(self, path: str | Path = ".astraforge/state.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    command TEXT,
                    error TEXT,
                    updated_at TEXT NOT NULL
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    requirements TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            db.commit()

    def _connect(self):
        return sqlite3.connect(self.path)

    def save_project(self, project: ProjectSpec) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO projects
                   (id,name,description,requirements,status,created_at)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                   name=excluded.name, description=excluded.description,
                   requirements=excluded.requirements, status=excluded.status""",
                (
                    project.id,
                    project.name,
                    project.description,
                    json.dumps(project.requirements),
                    project.status.value,
                    project.created_at.isoformat(),
                ),
            )
            db.commit()


    def start_run(self, project_id: str, command: list[str]) -> int:
        from datetime import datetime, timezone
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO runs(project_id,stage,status,command,updated_at) VALUES(?,?,?,?,?)",
                (project_id, "planning", "running", json.dumps(command),
                 datetime.now(timezone.utc).isoformat()),
            )
            db.commit()
            return int(cursor.lastrowid)

    def update_run(self, run_id: int, *, stage: str, status: str,
                   attempts: int = 0, error: str | None = None) -> None:
        from datetime import datetime, timezone
        with self._connect() as db:
            db.execute(
                "UPDATE runs SET stage=?,status=?,attempts=?,error=?,updated_at=? WHERE id=?",
                (stage, status, attempts, error,
                 datetime.now(timezone.utc).isoformat(), run_id),
            )
            db.commit()

    def get_latest_run(self, project_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id,stage,status,attempts,command,error,updated_at "
                "FROM runs WHERE project_id=? ORDER BY id DESC LIMIT 1",
                (project_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "stage": row[1], "status": row[2],
            "attempts": row[3], "command": json.loads(row[4]) if row[4] else [],
            "error": row[5], "updated_at": row[6],
        }

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
            id=row[0],
            name=row[1],
            description=row[2],
            requirements=json.loads(row[3]),
            status=ProjectStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
        )
