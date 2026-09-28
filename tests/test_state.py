from astraforge.projects.schemas import ProjectSpec, ProjectStatus
from astraforge.state.store import StateStore


def test_project_state_roundtrip(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(name="demo", description="test", requirements=["auth"])
    project.status = ProjectStatus.BUILDING
    store.save_project(project)
    restored = store.get_project(project.id)
    assert restored is not None
    assert restored.name == "demo"
    assert restored.requirements == ["auth"]
    assert restored.status == ProjectStatus.BUILDING


def test_run_checkpoint_roundtrip(tmp_path):
    store = StateStore(tmp_path / "state.db")
    project = ProjectSpec(name="demo", description="test")
    store.save_project(project)
    run_id = store.start_run(project.id, ["pytest", "-q"])
    store.update_run(run_id, stage="testing", status="running", attempts=1)
    run = store.get_latest_run(project.id)
    assert run["stage"] == "testing"
    assert run["status"] == "running"
    assert run["attempts"] == 1
