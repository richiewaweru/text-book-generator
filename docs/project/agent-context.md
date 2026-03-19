# Agent Context

This file is the human-readable source of truth for the current project state.

## Current Runtime Shape

- `backend/src/textbook_agent/` is the product shell.
- `backend/src/pipeline/` is the only live generation engine.
- The canonical saved artifact is a JSON `PipelineDocument`.
- The frontend hydrates from `/document` and appends new sections from `/events`.
- Draft generations can be enhanced into balanced or strict runs through a seeded child generation.

## Current Schema Highlights

- `Generation` stores document metadata, template/preset ids, lineage, timing, and failure metadata.
- `SectionContent` is Lectio-aligned and rendered natively in the frontend.
- `grade_band` is derived in the shell from `StudentProfile.education_level`.
- `learner_fit` currently defaults to `general`.

## Current Prompt Source of Truth

- Prompt builders live in `backend/src/pipeline/prompts/`.
- Contract loading lives in `backend/src/pipeline/contracts.py`.
- Reference docs under `docs/` are descriptive only. Code in `backend/src/` is authoritative.

## Current Viewer Contract

- `/textbook/[id]` is generation-centric.
- The frontend loads generation detail and saved document by generation ID.
- SSE carries pipeline progress and section updates.
- Raw filesystem paths are internal storage details and are not part of the viewer contract.
