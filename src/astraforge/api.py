"""API endpoints for starting orchestration runs."""

import secrets

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse

from astraforge.agents.coder import CodingAgent
from astraforge.agents.factory import build_router
from astraforge.agents.reviewer import ReviewerAgent
from astraforge.config import settings
from astraforge.integrations.deployment import build_deployer
from astraforge.integrations.github import GitHubAdapter
from astraforge.orchestration.engine import Orchestrator
from astraforge.orchestration.events import build_events
from astraforge.orchestration.jobs import JobManager
from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import DockerCommandRunner, E2BCommandRunner

router = APIRouter(prefix="/projects", tags=["projects"])
orchestrator = Orchestrator()
state_store = StateStore(settings.state_db_path)


def _build_command_runner():
    """Select the execution sandbox explicitly; never silently fall back."""
    backend = settings.sandbox_backend.strip().lower()
    if backend == "docker":
        return DockerCommandRunner()
    if backend == "e2b":
        return E2BCommandRunner()
    raise RuntimeError("SANDBOX_BACKEND must be either 'docker' or 'e2b'")


def require_api_key(x_astraforge_key: str | None = Header(default=None)) -> None:
    if not settings.astraforge_api_key:
        return
    if not x_astraforge_key or not secrets.compare_digest(
        x_astraforge_key, settings.astraforge_api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing AstraForge API key")


CONTROL_UI = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AstraForge Control</title>
<style>
body{font-family:system-ui;margin:0;background:#0f1115;color:#eee}
main{max-width:900px;margin:40px auto;padding:20px}
input,textarea,button{width:100%;box-sizing:border-box;margin:8px 0;padding:12px;border-radius:8px;border:1px solid #333;background:#191c23;color:#fff}
button{cursor:pointer;background:#2563eb;border:0}
pre{white-space:pre-wrap;background:#090b0f;padding:14px;border-radius:8px}
</style>
</head>
<body>
<main>
<h1>AstraForge</h1>
<p>Control Center</p>
<input id="name" placeholder="Nom du projet">
<textarea id="description" placeholder="Décris le SaaS à construire"></textarea>
<textarea id="requirements" placeholder="Une exigence par ligne"></textarea>
<button onclick="build()">Construire et suivre</button>
<p id="status"></p>
<pre id="log"></pre>
<script>
const key = new URLSearchParams(location.search).get("key") || "";
let ws;
function log(x) {
  document.getElementById("log").textContent += x + String.fromCharCode(10);
}
async function build() {
  const id = crypto.randomUUID();
  const project = {
    id,
    name: document.getElementById("name").value || "AstraForge project",
    description: document.getElementById("description").value,
    requirements: document.getElementById("requirements").value
      .split(String.fromCharCode(10)).filter(Boolean)
  };
  const wsProtocol = location.protocol === "https:" ? "wss://" : "ws://";
  const token = key ? "?token=" + encodeURIComponent(key) : "";
  ws = new WebSocket(
    wsProtocol + location.host + "/projects/" + id + "/events" + token
  );
  ws.onmessage = event => {
    const data = JSON.parse(event.data);
    document.getElementById("status").textContent =
      data.stage || data.type || data.status;
    log(JSON.stringify(data));
  };
  ws.onopen = async () => {
    const response = await fetch(
      "/projects/build?publish=false&deploy=false",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(key ? {"X-AstraForge-Key": key} : {})
        },
        body: JSON.stringify(project)
      }
    );
    log(JSON.stringify(await response.json(), null, 2));
  };
}
</script>
</main>
</body>
</html>"""


@router.post("/plan")
def create_project_plan(project: ProjectSpec, _: None = Depends(require_api_key)) -> dict:
    state_store.save_project(project)
    plan = orchestrator.create_plan(project)
    state_store.save_project(project)
    return {
        "project_id": plan.project_id,
        "status": project.status,
        "tasks": [{"role": task.role, "instruction": task.instruction} for task in plan.tasks],
    }


async def _execute_build_job(job: dict) -> None:
    project = state_store.get_project(job["project_id"])
    if project is None:
        raise RuntimeError(f"Project {job['project_id']} no longer exists")

    model_router = build_router()
    workspace_manager = WorkspaceManager(settings.workspace_root)
    coder = CodingAgent(model_router, workspace_manager)
    reviewer = ReviewerAgent(model_router, workspace_manager)

    github = None
    deployer = None
    if job["publish"]:
        github = GitHubAdapter(settings.github_token, settings.github_repository)
    if job["deploy"]:
        deployer = build_deployer()

    pipeline = AutonomousPipeline(
        coder,
        workspace_manager,
        _build_command_runner(),
        github=github,
        reviewer=reviewer,
        state_store=state_store,
        deployer=deployer,
    )
    try:
        await pipeline.run(
            project,
            job["command"],
            resume=True,
            run_id=job["id"],
        )
    finally:
        state_store.save_project(project)


job_manager = JobManager(state_store, _execute_build_job)


def _public_run(run: dict) -> dict:
    """Return run metadata safe for external clients; never expose worker leases or raw context."""
    return {
        "id": run["id"], "project_id": run["project_id"], "stage": run["stage"],
        "status": run["status"], "attempts": run["attempts"], "error": run["error"],
        "updated_at": run["updated_at"], "started_at": run["started_at"],
        "cancel_requested": run["cancel_requested"], "publish": run["publish"], "deploy": run["deploy"],
    }


def _workspace_for(project_id: str):
    workspace_manager = WorkspaceManager(settings.workspace_root)
    workspace = (workspace_manager.root / project_id).resolve()
    try:
        workspace.relative_to(workspace_manager.root)
    except ValueError:
        return None
    return workspace if workspace.exists() else None


async def _queue_build(project: ProjectSpec, *, publish: bool, deploy: bool) -> dict:
    if publish and (not settings.github_token or not settings.github_repository):
        raise HTTPException(status_code=400, detail="GitHub publishing requires GITHUB_TOKEN and GITHUB_REPOSITORY")
    if deploy:
        if not publish:
            raise HTTPException(status_code=400, detail="Deployment requires publish=true")
        if build_deployer() is None:
            raise HTTPException(status_code=400, detail="Cloudflare deployment requires CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_PAGES_PROJECT")
    run_id = state_store.enqueue_run(project.id, ["python", "-m", "pytest", "-q"], publish=publish, deploy=deploy)
    return {"project_id": project.id, "run_id": run_id, "status": "queued"}


@router.post("")
def create_project(project: ProjectSpec, _: None = Depends(require_api_key)) -> dict:
    state_store.save_project(project)
    return {"project": project.model_dump(mode="json")}


@router.post("/{project_id}/build")
async def build_existing_project(project_id: str, publish: bool = False, deploy: bool = False, _: None = Depends(require_api_key)) -> dict:
    project = state_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return await _queue_build(project, publish=publish, deploy=deploy)


@router.get("/{project_id}/files")
def get_project_files(project_id: str, path: str | None = Query(default=None), _: None = Depends(require_api_key)) -> dict:
    if state_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    workspace = _workspace_for(project_id)
    if workspace is None:
        return {"project_id": project_id, "files": []}
    manager = WorkspaceManager(settings.workspace_root)
    if path:
        try:
            content = manager.read_file(workspace, path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="File not found") from None
        except (IsADirectoryError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid file path") from None
        return {"project_id": project_id, "path": path, "content": content}
    files = sorted(str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file())
    return {"project_id": project_id, "files": files}


@router.get("/{project_id}/tests")
def get_project_tests(project_id: str, _: None = Depends(require_api_key)) -> dict:
    if state_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = state_store.get_latest_run(project_id)
    context = (run or {}).get("context", {})
    return {"project_id": project_id, "run_id": run["id"] if run else None,
            "tests": context.get("test_results", []), "tester_findings": context.get("tester_findings", []),
            "reviewer_findings": context.get("reviewer_findings", []), "repairs": context.get("repairs", [])}


@router.post("/{project_id}/deploy")
async def deploy_project(project_id: str, _: None = Depends(require_api_key)) -> dict:
    project = state_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return await _queue_build(project, publish=True, deploy=True)


@router.post("/build")
async def build_project(
    project: ProjectSpec,
    publish: bool = False,
    deploy: bool = False,
    _: None = Depends(require_api_key),
) -> dict:
    state_store.save_project(project)

    result = await _queue_build(project, publish=publish, deploy=deploy)
    result["message"] = "Build queued for the durable worker. Follow the run and event endpoints."
    return result


@router.get("/{project_id}/runs")
def list_project_runs(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_api_key),
) -> dict:
    if state_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "runs": [_public_run(run) for run in state_store.list_runs(project_id, limit)]}


@router.get("/{project_id}/runs/{run_id}")
def get_project_run(
    project_id: str,
    run_id: int,
    _: None = Depends(require_api_key),
) -> dict:
    run = state_store.get_run(run_id)
    if not run or run["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return _public_run(run)


@router.get("/{project_id}/events")
def get_project_events(
    project_id: str,
    after_id: int = Query(default=0, ge=0),
    _: None = Depends(require_api_key),
) -> dict:
    if state_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "events": state_store.list_events(project_id, after_id)}


@router.post("/{project_id}/runs/{run_id}/cancel")
def cancel_project_run(
    project_id: str,
    run_id: int,
    _: None = Depends(require_api_key),
) -> dict:
    run = state_store.get_run(run_id)
    if not run or run["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    if not state_store.request_cancel(run_id):
        raise HTTPException(status_code=409, detail="Run is no longer active")
    state_store.append_event(
        project_id,
        run["stage"],
        "cancellation_requested",
        "Cancellation requested",
        run_id=run_id,
    )
    return {"run_id": run_id, "status": "cancellation_requested"}


@router.post("/{project_id}/resume")
async def resume_project(
    project_id: str,
    publish: bool = False,
    deploy: bool = False,
    _: None = Depends(require_api_key),
) -> dict:
    project = state_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    latest = state_store.get_latest_run(project_id)
    if not latest or latest["status"] != "cancelled":
        raise HTTPException(status_code=409, detail="No cancelled run to resume")

    if publish and (not settings.github_token or not settings.github_repository):
        raise HTTPException(
            status_code=400,
            detail="GitHub publishing requires GITHUB_TOKEN and GITHUB_REPOSITORY",
        )
    if deploy:
        if not publish:
            raise HTTPException(status_code=400, detail="Deployment requires publish=true")
        if build_deployer() is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cloudflare deployment requires CLOUDFLARE_API_TOKEN, "
                    "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_PAGES_PROJECT"
                ),
            )

    if not state_store.resume_run(latest["id"]):
        raise HTTPException(status_code=409, detail="Run cannot be resumed")
    return {
        "project_id": project_id,
        "run_id": latest["id"],
        "status": "queued",
        "message": "Build resumed and queued for the worker.",
    }


@router.get("/control", response_class=HTMLResponse, include_in_schema=False)
def control_center() -> str:
    return CONTROL_UI


@router.get("/{project_id}")
def get_project_state(project_id: str, _: None = Depends(require_api_key)) -> dict:
    project = state_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = state_store.get_latest_run(project_id)
    return {"project": project.model_dump(mode="json"), "latest_run": _public_run(run) if run else None}


@router.websocket("/{project_id}/events")
async def project_events(
    websocket: WebSocket,
    project_id: str,
    token: str | None = Query(default=None),
) -> None:
    if settings.astraforge_api_key:
        if not token or not secrets.compare_digest(token, settings.astraforge_api_key):
            await websocket.close(code=1008)
            return
    await websocket.accept()
    last_id = 0
    try:
        for event in state_store.list_events(project_id):
            await websocket.send_json(event)
            last_id = max(last_id, int(event["id"]))
        async for event in build_events.subscribe(project_id):
            event_id = int(event.get("id", 0))
            if event_id and event_id <= last_id:
                continue
            await websocket.send_json(event)
            if event.get("status") in {"completed", "failed", "cancelled"}:
                break
    except WebSocketDisconnect:
        return
