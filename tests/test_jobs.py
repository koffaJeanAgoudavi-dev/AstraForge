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
    assert seen[0]["worker_id"] == worker.worker_id
    assert store.get_run(run_id)["status"] == "completed"
    assert store.get_run(run_id)["lease_until"] is None
    assert await worker.run_once() is False


@pytest.mark.asyncio
async def test_worker_heartbeat_prevents_lease_recovery(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(id="job-heartbeat", name="Job", description="test")
    store.save_project(project)
    run_id = store.enqueue_run(project.id, ["pytest"])

    async def execute(job):
        assert store.heartbeat_run(job["id"], job["worker_id"], lease_seconds=60)
        current = store.get_run(job["id"])
        assert current["heartbeat_at"] is not None
        assert current["lease_until"] is not None
        store.update_run(job["id"], stage="completed", status="completed")

    worker = BuildWorker(store, execute, lease_seconds=1)
    assert await worker.run_once() is True
    assert store.get_run(run_id)["status"] == "completed"


@pytest.mark.asyncio
async def test_worker_recovers_expired_lease(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(id="job-2", name="Job", description="test")
    store.save_project(project)
    run_id = store.enqueue_run(project.id, ["pytest"])

    worker = BuildWorker(store, execute=lambda job: asyncio.sleep(0), lease_seconds=1)
    claimed = store.claim_next_queued_run(worker.worker_id, lease_seconds=1)
    assert claimed["id"] == run_id

    with store._connect() as db:
        db.execute(
            "UPDATE runs SET lease_until=? WHERE id=?",
            ("2000-01-01T00:00:00+00:00", run_id),
        )
        db.commit()

    assert store.recover_stale_runs(300) == 1
    assert store.get_run(run_id)["status"] == "queued"


@pytest.mark.asyncio
async def test_worker_timeout_marks_run_failed(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(id="job-timeout", name="Job", description="test")
    store.save_project(project)
    run_id = store.enqueue_run(project.id, ["pytest"])

    async def execute(job):
        await asyncio.sleep(1)

    worker = BuildWorker(store, execute, max_runtime=0.01)
    assert await worker.run_once() is True
    run = store.get_run(run_id)
    assert run["status"] == "failed"
    assert "timeout" in run["error"].lower()


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
