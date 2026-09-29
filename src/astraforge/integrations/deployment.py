"""Deployment adapters for completed AstraForge projects."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class DeploymentResult:
    provider: str
    url: str
    deployment_id: str | None = None


class CloudflarePagesDeployer:
    """Deploy a validated workspace through Wrangler.

    Deployment is deliberately separate from the sandbox: it is a privileged
    operation and must only be invoked after tests/review and explicit publish.
    """

    provider = "cloudflare_pages"

    def __init__(
        self,
        api_token: str,
        account_id: str,
        project_name: str,
        output_dir: str = ".",
        timeout: int = 300,
    ) -> None:
        if not api_token or not account_id or not project_name:
            raise ValueError("Cloudflare token, account ID and project name are required")
        if timeout <= 0:
            raise ValueError("Deployment timeout must be positive")
        self.api_token = api_token
        self.account_id = account_id
        self.project_name = project_name
        self.output_dir = output_dir
        self.timeout = timeout

    def deploy(self, workspace: Path) -> DeploymentResult:
        workspace = workspace.resolve()
        target = (workspace / self.output_dir).resolve()
        if target != workspace and workspace not in target.parents:
            raise ValueError("Deployment output directory must be inside the workspace")
        if not target.is_dir():
            raise ValueError(f"Deployment output directory does not exist: {self.output_dir}")

        env = os.environ.copy()
        env["CLOUDFLARE_API_TOKEN"] = self.api_token
        env["CLOUDFLARE_ACCOUNT_ID"] = self.account_id

        command = [
            "npx", "wrangler", "pages", "deploy", str(target),
            "--project-name", self.project_name,
            "--commit-dirty=true",
        ]
        try:
            result = subprocess.run(
                command, cwd=workspace, env=env,
                capture_output=True, text=True, timeout=self.timeout, check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Node.js/npx is required for Cloudflare Pages deployment") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Cloudflare deployment timed out") from exc

        if result.returncode != 0:
            raise RuntimeError(
                "Cloudflare deployment failed: "
                + (result.stderr.strip() or result.stdout.strip())
            )

        url = _extract_deployment_url(result.stdout)
        if not url:
            raise RuntimeError("Deployment succeeded but Wrangler returned no valid Pages URL")
        return DeploymentResult(self.provider, url)


def _extract_deployment_url(output: str) -> str | None:
    for token in output.split():
        candidate = token.rstrip(".,);]")
        parsed = urlparse(candidate)
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme == "https"
            and (hostname == "pages.dev" or hostname.endswith(".pages.dev"))
            and parsed.username is None
            and parsed.password is None
        ):
            return candidate
    return None


def build_deployer():
    from astraforge.config import settings

    if settings.deployment_backend == "cloudflare_pages":
        if not all(
            [settings.cloudflare_api_token, settings.cloudflare_account_id,
             settings.cloudflare_pages_project]
        ):
            return None
        return CloudflarePagesDeployer(
            settings.cloudflare_api_token,
            settings.cloudflare_account_id,
            settings.cloudflare_pages_project,
            settings.deployment_output_dir,
        )
    raise ValueError(f"Unsupported deployment backend: {settings.deployment_backend}")
