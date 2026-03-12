# Project Docs

Live project-specific documentation for Textbook Generation Agent.

## Contents

| Doc | What it covers |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | DDD layer rules and architecture guard |
| [SETUP.md](SETUP.md) | Install commands and project-local tools |
| [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) | How CI and validation work |
| [context-summary.yaml](context-summary.yaml) | Machine-readable project config (used by `tools/agent/` scripts) |
| [runs/](runs/) | Tracking checklists and runbooks |

## Relationship to `agents/`

- `agents/` has the universal standards, workflows, and project config in `agents/project.md`.
- This directory has project-specific docs that go deeper: architecture details, setup instructions, CI workflow.
- `agents/project.md` is the quick reference. These docs are the detailed reference.
