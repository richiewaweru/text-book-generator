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
| `architecture-guard` | DDD layer boundary compliance |
| `agent-governance` | PR structure and process compliance |

All checks must pass before merge.

## Execution Boundary

- `agents/` -- universal standards and workflows (portable, agent-agnostic)
- `tools/agent/` -- project-local validation scripts (reads `context-summary.yaml`)
- `.github/workflows/` -- CI runners that call `tools/agent/` scripts
