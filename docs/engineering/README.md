# Engineering Docs

This directory holds the living engineering process for the repository.

## Decision Map
- [Versioning and Releases](versioning-and-releases.md): branch strategy, commit policy, SemVer tags, changelog flow.
- [GitHub Governance](github-governance.md): branch protections, review policy, labels, CODEOWNERS, and ruleset intent.
- [Agentic Coding Playbook](agentic-coding-playbook.md): how local agents plan, validate, commit, and hand off work.
- [Review Agents](review-agents.md): external oversight agents, when they run, and how their output is consumed.

## Usage
- Keep durable process changes here instead of duplicating them into `docs/vX.Y.Z/` snapshots.
- Snapshot docs under `docs/vX.Y.Z/` only when the released system or public contracts materially change.
- Treat this directory as the current source of truth for engineering workflow.
