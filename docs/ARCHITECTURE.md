# AstraForge — MVP architecture

## Goal
Accept a software brief, turn it into a structured project, generate code in an isolated workspace, run controlled checks, request an independent review, and publish changes to GitHub. Deployment is a later milestone.

## Initial components

- **FastAPI service**: API boundary and health endpoint.
- **Project domain**: project specification and lifecycle status.
- **Provider adapters**: common async contract for Gemini, Groq, DeepSeek, and future providers.
- **Model router (next milestone)**: provider selection, retries, rate-limit handling, and fallback policies.
- **Workspace executor (next milestone)**: isolated project directory and allowlisted commands; no unrestricted model shell access.
- **Quality gate (next milestone)**: tests, linting, review, and bounded repair cycles.
- **GitHub adapter (next milestone)**: create branch, commit artifacts, and open a pull request.
- **Deployment adapter (later)**: explicit target configuration and deployment approval.

## Safety and secrets

- Real API keys belong in a local `.env` file and must never be committed.
- `.env.example` contains names only, no credentials.
- Generated code execution must be sandboxed and resource-limited.
- Model output is untrusted input. Tools run only through orchestrator-controlled, validated operations.
- Destructive actions and deployment require explicit user approval.

## MVP sequence

1. API configuration and health check.
2. Provider interface and one provider integration.
3. Project creation and persistent task state.
4. Workspace file operations and constrained test runner.
5. Review/repair loop with iteration limits.
6. GitHub branch/commit/PR flow.
7. Deployment integration after the build-and-test loop is reliable.
