# Release Checklist

## Preconditions
- Change is already merged to `main`
- Required checks are green
- Changelog entry exists for the target version

## Steps
1. Confirm `CHANGELOG.md` contains the release notes section.
2. Confirm snapshot docs under `docs/vX.Y.Z/` are updated if the release changes shipped architecture or contracts.
3. Tag `main` with `vX.Y.Z`.
4. Push the tag and watch `release.yml` complete successfully.
5. Verify the generated GitHub Release notes match the changelog.

## Validation Evidence
- Backend quality status:
- Frontend quality status:
- Architecture guard status:
- Release workflow URL:
