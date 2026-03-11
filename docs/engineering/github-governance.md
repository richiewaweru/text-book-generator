# GitHub Governance

## Repository Defaults
- Default branch: `main`
- Merge method: squash merge only
- History: linear
- Force pushes to `main`: blocked
- Auto-merge: allowed only after approval and required checks pass

## Required Pull Request Policy
- Pull request required for changes to `main`
- Minimum approvals: 1 human reviewer
- Dismiss stale approvals on new commits
- Require CODEOWNER review where CODEOWNERS applies
- Required conversations resolved before merge

## Required Checks
- `backend-quality`
- `frontend-quality`
- `architecture-guard`

## Labels
- `ai-review`: opt a PR into advisory LLM review
- `architecture`: highlights structural/design concerns
- `release`: marks release prep or tagging work

## Ruleset Artifact
- The intended `main` protection shape is captured in `.github/rulesets/main-protection.json`.
- Apply it through GitHub rulesets or the GitHub API after the repo is hosted remotely.
- This repo cannot enforce GitHub-hosted protections locally; the JSON artifact is the declarative source for those settings.
