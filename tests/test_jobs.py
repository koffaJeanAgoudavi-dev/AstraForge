import asyncio

import pytest

from astraforge.orchestration.jobs import BuildWorker
from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore


@pytest.mark.asyncio
async def test_worker_claims_and_executes_queued_run(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(id="job-1", name="Job", description="test")
    store.save_project(project)
    run_id = store.enqueue_run(project.id, ["pytest"], publish=True)

    seen = []

    async def execute(job):
        seen.append(job)
        store.update_run(job["id"], stage="completed", status="completed")

    worker = BuildWorker(store, execute)
    assert await worker.run_once() is True
    assert seen[0]["id"] == run_id
    assert seen[0]["publish"] is True
    assert store.get_run(run_id)["status"] == "completed"
    assert await worker.run_once() is False


@pytest.mark.asyncio
async def test_worker_recovers_stale_running_run(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(id="job-2", name="Job", description="test")
    store.save_project(project)
    run_id = store.start_run(project.id, ["pytest"])

    with store._connect() as db:
        db.execute(
            "UPDATE runs SET updated_at=? WHERE id=?",
            ("2000-01-01T00:00:00+00:00", run_id),
        )
        db.commit()

    seen = []

    async def execute(job):
        seen.append(job)
        store.update_run(job["id"], stage="completed", status="completed")

    worker = BuildWorker(store, execute, recovery_age=1)
    store.recover_stale_runs(1)
    assert store.get_run(run_id)["status"] == "queued"
    assert await worker.run_once() is True
    assert seen[0]["id"] == run_id


@pytest.mark.asyncio
async def test_worker_stop_event_stops_polling(tmp_path):
    store = StateStore(tmp_path / "state.db")

    async def execute(job):
        return None

    worker = BuildWorker(store, execute, poll_interval=0.01)
    task = asyncio.create_task(worker.run_forever())
    await asyncio.sleep(0.02)
    worker.stop()
    await asyncio.wait_for(task, timeout=1)
