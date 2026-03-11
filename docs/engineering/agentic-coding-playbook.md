# Agentic Coding Playbook

## Local Execution Model
- Agents work on short-lived branches, never directly on `main`.
- Local validation is the source of truth before commit and before opening or updating a pull request.
- Required local baseline:
  - `uv run ruff check src/ tests/`
  - `uv run pytest`
  - `npm run check`
  - `npm run build`

## Standard Agent Loop
1. Read the relevant architecture, schema, and handoff docs.
2. Make the smallest coherent change set that solves the task.
3. Stage only the files that belong to that change.
4. Run `automation/scripts/commit_if_green.py` or the equivalent manual validation flow.
5. Open or update the PR with validation evidence and architecture notes.
6. Leave a handoff using `automation/templates/handoff.md` when work stops midstream.

## Commit Guard Rules
- Protected branches are off-limits for automated local commits.
- The guarded commit flow refuses if no files are staged.
- The guarded commit flow refuses if unstaged or untracked changes exist, to keep the validated tree identical to the committed tree.
- GitHub Actions do not write code back to the branch.

## Handoff Expectations
- State what changed.
- State what validation ran and the outcome.
- State known risks, missing tests, and next actions.
