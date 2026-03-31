# Development Workflow

## How Agents Work on This Project

1. Read `agents/ENTRY.md` (the universal entry point).
2. Read `agents/project.md` (this project's specific rules).
3. Pick the right workflow from `agents/workflows/`.
4. Follow the workflow's tracking checklist.
5. Run validation before marking work complete.

## CI Required Checks

| Check | What it validates |
| --- | --- |
| `backend-quality` | Ruff lint + pytest |
| `frontend-quality` | Svelte type-check + build |
| `architecture-guard` | Shell/core/pipeline boundary rules plus no-import-back-into-shell checks |
| `agent-governance` | PR structure and process compliance |

All checks must pass before merge.

Project-local validation uses `python tools/agent/validate_repo.py --scope all`, which now covers backend, frontend, and tooling automation tests declared in `docs/project/context-summary.yaml`.

## Runtime Verification

Before testing textbook generation in dev:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5173
```

Verify that:

- `/health` returns the current runtime fingerprint (`instance_id`, `started_at`, `pipeline_architecture`)
- the frontend root responds on the expected port
- the backend and frontend agree on the configured API origin before starting new generations

For Docker-based verification, use `docker compose up --build` from the repo root and confirm the `backend` and `frontend` services both report healthy.

## Execution Boundary

- `agents/` -- universal standards and workflows (portable, agent-agnostic)
- `tools/agent/` -- project-local validation scripts (reads `context-summary.yaml`)
- `backend/src/core/` -- shared infrastructure and shared auth/profile/user primitives
- `backend/src/generation/` -- generation app (HTTP, persistence, generation orchestration)
- `backend/src/planning/` -- Teacher Studio planning layer
- `backend/src/pipeline/` -- standalone generation engine
- `.github/workflows/` -- CI runners that call `tools/agent/` scripts
