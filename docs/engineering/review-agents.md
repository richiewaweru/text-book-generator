# Review Agents

## Purpose
Review agents are external oversight prompts and workflows that evaluate a pull request after the coding agent finishes implementation.

## Agents
- `bug-risk.md`: hunts for likely behavioral bugs and regression vectors.
- `architecture-compliance.md`: checks for DDD boundary drift and violations of project structure.
- `test-gap.md`: looks for missing validation, coverage gaps, or weak assertions.

## Execution Model
- Static checks are always authoritative and can block merges.
- AI review is advisory only and runs when the PR carries the `ai-review` label or when the workflow is dispatched manually.
- AI review must never modify repository files. Its outputs are PR comments and workflow artifacts only.

## Severity Expectations
- `critical`: likely production breakage, data loss, or major architectural breach.
- `high`: serious correctness or integration risk.
- `medium`: plausible bug or incomplete validation.
- `low`: worthwhile cleanup or follow-up, but not merge-blocking by itself.

## Consumption
- Human reviewers remain the merge gate for `main`.
- AI findings should be triaged explicitly: fix now, convert to follow-up issue, or reject with rationale in the PR discussion.
