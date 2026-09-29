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
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                publish INTEGER NOT NULL DEFAULT 0, deploy INTEGER NOT NULL DEFAULT 0,
                worker_id TEXT, lease_until TEXT, heartbeat_at TEXT, started_at TEXT
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
            if "publish" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN publish INTEGER NOT NULL DEFAULT 0")
            if "deploy" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN deploy INTEGER NOT NULL DEFAULT 0")
            if "worker_id" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN worker_id TEXT")
            if "lease_until" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN lease_until TEXT")
            if "heartbeat_at" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN heartbeat_at TEXT")
            if "started_at" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN started_at TEXT")
            db.execute("CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id, id DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_runs_queue ON runs(status, id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON build_events(project_id, id)")
            db.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def save_project(self, project: ProjectSpec) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO projects
                (id,name,description,requirements,status,created_at) VALUES (?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                description=excluded.description, requirements=excluded.requirements,
                status=excluded.status""",
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
                "SELECT id,name,description,requirements,status,created_at "
                "FROM projects WHERE id=?",
                (project_id,),
            ).fetchone()
        if not row:
            return None
        return ProjectSpec(
            id=row[0],
            name=row[1],
            description=row[2],
            requirements=json.loads(row[3]),
            status=ProjectStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
        )

    def start_run(self, project_id: str, command: list[str], stage: str = "planning") -> int:
        with self._connect() as db:
            cursor = db.execute(
                """INSERT INTO runs(
                    project_id,stage,status,command,updated_at,context,cancel_requested
                ) VALUES(?,?,?,?,?,?,0)""",
                (
                    project_id,
                    stage,
                    "running",
                    json.dumps(command),
                    datetime.now(timezone.utc).isoformat(),
                    "{}",
                ),
            )
            db.commit()
            return int(cursor.lastrowid)

    def enqueue_run(
        self,
        project_id: str,
        command: list[str],
        *,
        publish: bool = False,
        deploy: bool = False,
    ) -> int:
        with self._connect() as db:
            cursor = db.execute(
                """INSERT INTO runs(
                    project_id,stage,status,command,updated_at,context,cancel_requested,publish,deploy
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    project_id,
                    "queued",
                    "queued",
                    json.dumps(command),
                    datetime.now(timezone.utc).isoformat(),
                    "{}",
                    0,
                    int(publish),
                    int(deploy),
                ),
            )
            db.commit()
            return int(cursor.lastrowid)

    def claim_next_queued_run(self, worker_id: str, lease_seconds: int = 60) -> dict | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT id,project_id,stage,status,attempts,command,error,updated_at,
                          context,cancel_requested,publish,deploy,worker_id,lease_until,heartbeat_at,started_at
                   FROM runs WHERE status='queued' AND cancel_requested=0
                   ORDER BY id ASC LIMIT 1"""
            ).fetchone()
            if not row:
                db.commit()
                return None
            now_dt = datetime.now(timezone.utc)
            now = now_dt.isoformat()
            lease_until = datetime.fromtimestamp(now_dt.timestamp() + lease_seconds, tz=timezone.utc).isoformat()
            db.execute(
                "UPDATE runs SET status='running',stage='starting',updated_at=?,worker_id=?,lease_until=?,heartbeat_at=?,started_at=COALESCE(started_at,?) WHERE id=? AND status='queued'",
                (now, worker_id, lease_until, now, now, row[0]),
            )
            db.commit()
            values = list(row)
            values[2] = "starting"
            values[3] = "running"
            return self._run_dict(tuple(values))

    def recover_stale_runs(self, max_age_seconds: int = 300) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_seconds
        recovered = 0
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,updated_at,lease_until FROM runs WHERE status='running'"
            ).fetchall()
            for run_id, updated_at, lease_until in rows:
                try:
                    expired = (datetime.fromisoformat(lease_until).timestamp() if lease_until else datetime.fromisoformat(updated_at).timestamp() < cutoff)
                except ValueError:
                    continue
                if expired:
                    cursor = db.execute(
                        """UPDATE runs SET status='queued',stage='recovered',updated_at=?,error=?,
                           worker_id=NULL,lease_until=NULL,heartbeat_at=NULL WHERE id=? AND status='running'""",
                        (
                            datetime.now(timezone.utc).isoformat(),
                            "Worker lease expired; run requeued for recovery",
                            run_id,
                        ),
                    )
                    recovered += cursor.rowcount
            db.commit()
        return recovered

    def heartbeat_run(self, run_id: int, worker_id: str, lease_seconds: int = 60) -> bool:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        lease_until = datetime.fromtimestamp(now_dt.timestamp() + lease_seconds, tz=timezone.utc).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE runs SET heartbeat_at=?,lease_until=?,updated_at=? WHERE id=? AND status='running' AND worker_id=?",
                (now, lease_until, now, run_id, worker_id),
            )
            db.commit()
            return cursor.rowcount == 1

    def update_run(
        self,
        run_id: int,
        *,
        stage: str,
        status: str,
        attempts: int = 0,
        error: str | None = None,
        context: dict | None = None,
    ) -> None:
        with self._connect() as db:
            db.execute(
                """UPDATE runs SET stage=?,status=?,attempts=?,error=?,updated_at=?,context=?,worker_id=CASE WHEN ? IN ('completed','failed','cancelled') THEN NULL ELSE worker_id END,
                   lease_until=CASE WHEN ? IN ('completed','failed','cancelled') THEN NULL ELSE lease_until END,
                   heartbeat_at=CASE WHEN ? IN ('completed','failed','cancelled') THEN NULL ELSE heartbeat_at END
                   WHERE id=?""",
                (
                    stage,
                    status,
                    attempts,
                    error,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(context or {}),
                    status,
                    status,
                    status,
                    run_id,
                ),
            )
            db.commit()

    def request_cancel(self, run_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                """UPDATE runs SET cancel_requested=1,updated_at=?
                   WHERE id=? AND status IN ('queued','running')""",
                (datetime.now(timezone.utc).isoformat(), run_id),
            )
            if cursor.rowcount:
                db.execute(
                    "UPDATE runs SET status='cancelled',stage='cancelled' "
                    "WHERE id=? AND status='queued'",
                    (run_id,),
                )
            db.commit()
            return cursor.rowcount == 1

    def resume_run(self, run_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                """UPDATE runs SET status='queued',stage='queued',cancel_requested=0,
                   error=NULL,updated_at=? WHERE id=? AND status='cancelled'""",
                (datetime.now(timezone.utc).isoformat(), run_id),
            )
            db.commit()
            return cursor.rowcount == 1

    def is_cancel_requested(self, run_id: int) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT cancel_requested FROM runs WHERE id=?", (run_id,)
            ).fetchone()
        return bool(row and row[0])

    def get_run(self, run_id: int) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                """SELECT id,project_id,stage,status,attempts,command,error,updated_at,
                   context,cancel_requested,publish,deploy,worker_id,lease_until,heartbeat_at,started_at FROM runs WHERE id=?""",
                (run_id,),
            ).fetchone()
        return self._run_dict(row) if row else None

    def list_runs(self, project_id: str, limit: int = 50) -> list[dict]:
        limit = max(1, min(limit, 200))
        with self._connect() as db:
            rows = db.execute(
                """SELECT id,project_id,stage,status,attempts,command,error,updated_at,
                   context,cancel_requested,publish,deploy,worker_id,lease_until,heartbeat_at,started_at
                   FROM runs WHERE project_id=? ORDER BY id DESC LIMIT ?""",
                (project_id, limit),
            ).fetchall()
        return [self._run_dict(row) for row in rows]

    def get_latest_run(self, project_id: str) -> dict | None:
        runs = self.list_runs(project_id, 1)
        return runs[0] if runs else None

    def find_resumable_run(self, project_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                """SELECT id,project_id,stage,status,attempts,command,error,updated_at,
                   context,cancel_requested,publish,deploy
                   FROM runs WHERE project_id=? AND status='running' AND cancel_requested=0
                   ORDER BY id DESC LIMIT 1""",
                (project_id,),
            ).fetchone()
        return self._run_dict(row) if row else None

    def append_event(
        self,
        project_id: str,
        stage: str,
        status: str,
        message: str | None = None,
        metadata: dict | None = None,
        run_id: int | None = None,
    ) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                """INSERT INTO build_events(
                    project_id,run_id,timestamp,stage,status,message,metadata
                ) VALUES(?,?,?,?,?,?,?)""",
                (
                    project_id,
                    run_id,
                    timestamp,
                    stage,
                    status,
                    message,
                    json.dumps(metadata or {}),
                ),
            )
            db.commit()
            event_id = int(cursor.lastrowid)
        return {
            "id": event_id,
            "type": "stage",
            "project_id": project_id,
            "run_id": run_id,
            "timestamp": timestamp,
            "stage": stage,
            "status": status,
            "message": message,
            "metadata": metadata or {},
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
            {
                "id": row[0],
                "type": "stage",
                "project_id": row[1],
                "run_id": row[2],
                "timestamp": row[3],
                "stage": row[4],
                "status": row[5],
                "message": row[6],
                "metadata": json.loads(row[7] or "{}"),
            }
            for row in rows
        ]

    @staticmethod
    def _run_dict(row) -> dict:
        return {
            "id": row[0],
            "project_id": row[1],
            "stage": row[2],
            "status": row[3],
            "attempts": row[4],
            "command": json.loads(row[5]) if row[5] else [],
            "error": row[6],
            "updated_at": row[7],
            "context": json.loads(row[8] or "{}"),
            "cancel_requested": bool(row[9]),
            "publish": bool(row[10]),
            "deploy": bool(row[11]),
            "worker_id": row[12],
            "lease_until": row[13],
            "heartbeat_at": row[14],
            "started_at": row[15],
        }
