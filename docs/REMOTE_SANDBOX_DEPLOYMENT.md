# Remote sandbox deployment notes

## Purpose

AstraForge's build worker currently uses Docker for generated-project checks. A standard hosted web service does not guarantee access to a Docker daemon, so the worker can be configured to execute checks in an isolated E2B sandbox instead.

## Configuration

For a hosted backend:

- Set `SANDBOX_BACKEND=e2b`.
- Add `E2B_API_KEY` as a server-side secret.
- Install the optional SDK dependency with `pip install .[sandbox]` or add the `sandbox` extra to the platform's install command.
- Keep `ASTRAFORGE_API_KEY` configured; do not expose it to the browser.
- Keep GitHub publishing and Cloudflare deployment disabled until their server-side credentials are configured and tested.

For a local machine with Docker available, leave `SANDBOX_BACKEND=docker`.

There is deliberately no automatic fallback between providers: if the configured sandbox fails, the build should fail visibly rather than execute generated code outside a sandbox.

## Current limits and caveats

- Only UTF-8 text files are uploaded to the remote sandbox; `.git`, `.venv`, `node_modules`, and `__pycache__` are skipped.
- Uploads are capped at 2 MB per file and 10 MB per workspace by default.
- The remote sandbox receives project files only, not the backend's environment variables or API credentials.
- E2B usage, sandbox availability, default image contents, and pricing depend on the user's E2B account and plan. Confirm the account's current limits before production use.
- The current implementation runs the configured command in the sandbox and returns stdout/stderr/exit code. Dependency installation and framework-specific build setup still need to be formalized for generated projects.
- The API's SQLite database and local workspace directory are still local filesystem state. They must be moved to durable storage (or a durable mounted disk) before relying on hosted deployments, because ephemeral service filesystems can lose data on restart/redeploy.
- This branch does not deploy a hosted service and does not modify `main`.

## Pre-production checklist

1. Run the backend test suite and Ruff.
2. Validate E2B command timeout handling against the selected SDK version.
3. Add a project-specific dependency setup policy before running arbitrary generated projects.
4. Configure durable persistence for SQLite and workspaces.
5. Deploy a separate staging service and verify `/health`, authenticated project creation, build status, event streaming, file listing, and cancellation.
6. Only then connect the AstraForge frontend to the staging API.
