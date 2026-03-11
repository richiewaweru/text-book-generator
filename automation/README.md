# Automation Assets

## Directories
- `scripts/`: executable repo automation for validation, architecture checks, release notes, commit gating, and AI review.
- `templates/`: reusable markdown templates that agents can follow verbatim for repeatable routines.
- `agents/review/`: isolated oversight-agent prompts and schemas.

## Core Scripts
- `validate_repo.py --scope backend|frontend|all`
- `check_architecture.py --format text|markdown|sarif`
- `commit_if_green.py --type <type> --scope <scope> --summary "..."`
- `extract_release_notes.py --version vX.Y.Z`
- `run_ai_review.py --publish-comment`

## Principles
- Keep implementation helpers out of `backend/` and `frontend/`.
- Prefer deterministic validation as the merge gate.
- Treat AI review as advisory, reproducible input to a human reviewer rather than an autonomous merge actor.
