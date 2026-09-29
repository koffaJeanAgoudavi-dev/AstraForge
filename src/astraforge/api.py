"""API endpoints for starting orchestration runs."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from astraforge.agents.coder import CodingAgent
from astraforge.agents.factory import build_router
from astraforge.agents.reviewer import ReviewerAgent
from astraforge.config import settings
from astraforge.integrations.github import GitHubAdapter
from astraforge.integrations.deployment import build_deployer
from astraforge.orchestration.engine import Orchestrator
from astraforge.orchestration.pipeline import AutonomousPipeline
from astraforge.orchestration.jobs import JobManager
from astraforge.projects.schemas import ProjectSpec
from astraforge.state.store import StateStore
from astraforge.workspace.manager import WorkspaceManager
from astraforge.workspace.runner import DockerCommandRunner

router = APIRouter(prefix="/projects", tags=["projects"])
orchestrator = Orchestrator()
state_store = StateStore()


def require_api_key(x_astraforge_key: str | None = Header(default=None)) -> None:
    if not settings.astraforge_api_key:
        return
    if not x_astraforge_key or not secrets.compare_digest(x_astraforge_key, settings.astraforge_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing AstraForge API key")

CONTROL_UI = '''<!doctype html>
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
    requirements: document.getElementById("requirements").value.split(String.fromCharCode(10)).filter(Boolean)
  };
  const wsProtocol = location.protocol === "https:" ? "wss://" : "ws://";
  const token = key ? "?token=" + encodeURIComponent(key) : "";
  ws = new WebSocket(wsProtocol + location.host + "/projects/" + id + "/events" + token);
  ws.onmessage = event => {
    const data = JSON.parse(event.data);
    document.getElementById("status").textContent = data.stage || data.type || data.status;
    log(JSON.stringify(data));
  };
  ws.onopen = async () => {
    const response = await fetch("/projects/build?publish=false&deploy=false", {
      method: "POST",
      headers: {"Content-Type": "application/json", ...(key ? {"X-AstraForge-Key": key} : {})},
      body: JSON.stringify(project)
    });
    log(JSON.stringify(await response.json(), null, 2));
  };
}
</script>
</main>
</body>
</html>'''



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
    workspace_manager = WorkspaceManager()
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
        DockerCommandRunner(),
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

