"""API endpoints for starting orchestration runs."""

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from astraforge.agents.coder import CodingAgent
from astraforge.agents.factory import build_router
from astraforge.agents.reviewer import ReviewerAgent
from astraforge.config import settings
from astraforge.integrations.github import GitHubAdapter
from astraforge.integrations.deployment import build_deployer
from astraforge.orchestration.engine import Orchestrator
from astraforge.orchestration.events import build_events
from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import DockerCommandRunner

router = APIRouter(prefix="/projects", tags=["projects"])
orchestrator = Orchestrator()
state_store = StateStore()

CONTROL_UI = "<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>AstraForge Control</title><style>body{font-family:system-ui;margin:0;background:#0f1115;color:#eee}main{max-width:900px;margin:40px auto;padding:20px}input,textarea,button{width:100%;box-sizing:border-box;margin:8px 0;padding:12px;border-radius:8px;border:1px solid #333;background:#191c23;color:#fff}button{cursor:pointer;background:#2563eb;border:0}pre{white-space:pre-wrap;background:#090b0f;padding:14px;border-radius:8px}</style></head><body><main><h1>AstraForge</h1><p>Control Center</p><input id=\"name\" placeholder=\"Nom du projet\"><textarea id=\"description\" placeholder=\"Décris le SaaS à construire\"></textarea><textarea id=\"requirements\" placeholder=\"Une exigence par ligne\"></textarea><button onclick=\"build()\">Construire et suivre</button><p id=\"status\"></p><pre id=\"log\"></pre><script>let ws;function log(x){document.getElementById(\"log\").textContent+=x+\"\\n\"}async function build(){const id=crypto.randomUUID();const project={id:id,name:document.getElementById(\"name\").value||\"AstraForge project\",description:document.getElementById(\"description\").value,requirements:document.getElementById(\"requirements\").value.split(\"\\n\").filter(Boolean)};ws=new WebSocket((location.protocol===\"https:\"?\"wss://\":\"ws://\")+location.host+\"/projects/\"+id+\"/events\");ws.onmessage=e=>{const x=JSON.parse(e.data);document.getElementById(\"status\").textContent=x.stage||x.type;log(JSON.stringify(x))};ws.onopen=async()=>{const r=await fetch(\"/projects/build?publish=false&deploy=false\",{method:\"POST\",headers:{\"Content-Type\":\"application/json\"},body:JSON.stringify(project)});log(JSON.stringify(await r.json(),null,2))}}</script></main></body></html>"



@router.post("/plan")
def create_project_plan(project: ProjectSpec) -> dict:
    state_store.save_project(project)
    plan = orchestrator.create_plan(project)
    state_store.save_project(project)
    return {
        "project_id": plan.project_id,
        "status": project.status,
        "tasks": [{"role": task.role, "instruction": task.instruction} for task in plan.tasks],
    }


@router.post("/build")
async def build_project(project: ProjectSpec, publish: bool = False, deploy: bool = False) -> dict:
    state_store.save_project(project)
    model_router = build_router()
    workspace_manager = WorkspaceManager()
    coder = CodingAgent(model_router, workspace_manager)
    reviewer = ReviewerAgent(model_router, workspace_manager)

    github = None
    deployer = None
    if publish:
        if not settings.github_token or not settings.github_repository:
            raise HTTPException(
                status_code=400,
                detail="GitHub publishing requires GITHUB_TOKEN and GITHUB_REPOSITORY",
            )
        github = GitHubAdapter(settings.github_token, settings.github_repository)

    if deploy:
        if not publish:
            raise HTTPException(status_code=400, detail="Deployment requires publish=true")
        deployer = build_deployer()
        if deployer is None:
            raise HTTPException(status_code=400, detail="Cloudflare deployment requires CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_PAGES_PROJECT")

    pipeline = AutonomousPipeline(
        coder,
        workspace_manager,
        DockerCommandRunner(),
        github=github,
        reviewer=reviewer,
        state_store=state_store,
        deployer=deployer,
    )
    result = await pipeline.run(project, ["python", "-m", "pytest", "-q"])
    state_store.save_project(project)

    response = {
        "project_id": result.project_id,
        "status": project.status,
        "workspace": str(result.workspace),
        "files": result.files,
        "tests_passed": result.tests_passed,
        "repair_attempts": result.attempts,
        "resumed": result.resumed,
    }
    if result.pull_request:
        response["pull_request"] = {
            "number": result.pull_request.number,
            "url": result.pull_request.url,
            "branch": result.pull_request.branch,
        }
    if result.deployment:
        response["deployment"] = {"provider": result.deployment.provider, "url": result.deployment.url}
    return response


@router.get("/{project_id}")
def get_project_state(project_id: str) -> dict:
    project = state_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = state_store.get_latest_run(project_id)
    return {"project": project.model_dump(mode="json"), "latest_run": run}


@router.get("/control", response_class=HTMLResponse, include_in_schema=False)
def control_center() -> str:
    return CONTROL_UI


@router.websocket("/{project_id}/events")
async def project_events(websocket: WebSocket, project_id: str) -> None:
    await websocket.accept()
    try:
        async for event in build_events.subscribe(project_id):
            await websocket.send_json(event)
            if event.get("status") in {"completed", "failed"}:
                break
    except WebSocketDisconnect:
        return
