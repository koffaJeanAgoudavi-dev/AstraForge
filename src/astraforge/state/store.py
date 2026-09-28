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
