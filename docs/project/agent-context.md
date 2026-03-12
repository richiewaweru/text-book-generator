# Agent Context

This file is the human-readable source of truth for the current project state.

## Current Runtime Shape

- The backend generates textbooks through six pipeline nodes followed by a final HTML renderer stage.
- The rendered textbook remains a full standalone HTML document.
- The frontend does not inject textbook HTML into the app DOM. It fetches textbook HTML through an authenticated generation-owned backend route and mounts it with `iframe srcdoc`.
- The saved HTML artifact is intended to be self-contained and portable.

## Current Schema Highlights

- `SectionContent` now includes 11 fields.
- `practice_problems` contains exactly three structured problems (`warm`, `medium`, `cold`).
- `QualityIssue` includes `check_source` for `mechanical` vs `llm`.

## Current Prompt Source of Truth

- Shared prompt rules live in `backend/src/textbook_agent/domain/prompts/`.
- `base_prompt.py` composes the prompt bundle version and the shared pedagogical + formatting rules.
- Reference prompt docs under `docs/` are descriptive only. Code in `backend/src/` is authoritative.

## Current Viewer Contract

- `/textbook/[id]` is generation-centric.
- The frontend loads generation status/detail by generation ID.
- The frontend fetches rendered HTML through the authenticated generation-owned backend endpoint.
- Raw filesystem paths are internal storage details and are not part of the viewer contract.
