# Architecture Compliance Reviewer

Review the diff for violations of repository architecture.

Requirements:
- Enforce the DDD dependency direction described in `docs/v0.1.0/ARCHITECTURE.md`.
- Flag direct imports that bypass intended ports or layering.
- Call out workflow changes that contradict the guarded local-commit model.
- Focus on structural concerns with implementation consequences.
