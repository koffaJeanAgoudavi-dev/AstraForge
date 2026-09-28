from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore


def test_build_history_cancel_and_resume(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(id="p1", name="Test", description="test")
    store.save_project(project)
    run_id = store.start_run(project.id, ["pytest"])
    assert store.get_latest_run(project.id)["status"] == "running"

    assert store.request_cancel(run_id) is True
    assert store.is_cancel_requested(run_id) is True

    store.update_run(run_id, stage="cancelled", status="cancelled")
    assert store.resume_run(run_id) is True
    assert store.get_run(run_id)["status"] == "running"
    assert store.get_run(run_id)["cancel_requested"] is False


def test_persistent_events(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(id="p2", name="Test", description="test")
    store.save_project(project)
    run_id = store.start_run(project.id, ["pytest"])
    event = store.append_event(project.id, "testing", "running", "Tests started", run_id=run_id)
    events = store.list_events(project.id)
    assert events[0]["id"] == event["id"]
    assert events[0]["message"] == "Tests started"
