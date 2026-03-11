# Versioning and Releases

## Branch Strategy
- `main` is the protected trunk and the only branch that receives release tags.
- Work happens on short-lived branches named from the templates in `automation/templates/branch-naming.md`.
- Merge to `main` only through pull requests with required checks green.

## Commits
- Use Conventional Commits with the allowed types in `automation/templates/commit-message.md`.
- Agent-authored commits may be created by `automation/scripts/commit_if_green.py` only on non-protected branches.
- The guarded commit flow assumes the staged diff is the exact validated change set.

## Release Policy
- Release tags follow SemVer: `vMAJOR.MINOR.PATCH`.
- Tag only milestone-ready states on `main` after CI is green and changelog notes are prepared.
- `CHANGELOG.md` is the human release ledger. Each tagged release must have a matching changelog section.

## Docs Policy
- `docs/vX.Y.Z/` remains the historical snapshot for shipped architecture and schema state.
- `docs/engineering/` holds evergreen process and workflow guidance.
- Create a new snapshot doc set only when architecture, contracts, or release-facing process materially change.

## Release Flow
1. Merge the release-ready work into `main`.
2. Update `CHANGELOG.md` and any necessary snapshot docs.
3. Create and push the `vX.Y.Z` tag from `main`.
4. Let `release.yml` re-run validation and publish the GitHub Release from the changelog section.
