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
