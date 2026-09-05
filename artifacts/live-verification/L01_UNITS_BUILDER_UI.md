# L01 Units → Builder UI Verification

## Verdict

`INVALID_SCOPE_SELECTION`

This is a read-only reconciliation of the already completed L01 generation. Builder linkage and UI interaction passed as subchecks, but the selected lesson's identification-only scope did not match the campaign scenario. No generation, approval, retry, regeneration, provider call, or source edit was performed.

## Scope and identity

- Verification timestamp (UTC): `2026-09-05T15:09:35.870Z`
- Approved generation: `24586f47-c8bd-415a-9a43-cc77401a299b`
- Verified SHA: `63390e64`
- Unit: `59ad0eb4-da1e-48d3-9cbe-efe4761e4eef`
- Unit: approved `Mathematics`, `Grade 7`; title/objective: `By the end, students can solve and check one-step linear equations`
- L01 path lesson: `ce44273a-995b-4583-8d6a-4a1a67dd0b85`, title `Identify the operation`, `position=0`, `pack_id=24586f47-c8bd-415a-9a43-cc77401a299b`
- Classification: provider-capacity generation `1 of 12`; path position `0` explicitly excludes `solving the equation`, so content did not match the campaign scenario `solve and check one-step linear equations`.

## Units → Builder navigation

- Starting page: `http://127.0.0.1:5173/units` (Codex In-app Browser tab 1).
- Units UI visibly showed the approved Grade 7 Mathematics card and its objective; the card was followed through the UI.
- Final URL: `http://127.0.0.1:5173/builder/6ebbcec4-fd94-494b-b163-ec4322ae2c3a`.
- URL invariant: no observed navigation to `/studio`.

## Builder rendering and controls

- Builder heading: `Identify the operation`; status text: `Mathematics - default Saved`; estimated length: `~2 pages`. The `default` preset warning was confirmed and fixed separately.
- Five rendered sections: `Why it matters`, `Classify the operations`, `Practice with hints`, `Practice alone`, and `Check mastery`.
- Rendered Component Lectio block IDs: `hook-hero`, `comparison-grid`, `practice-stack` (guided), `practice-stack` (independent), `quiz-check`.
- Visible controls included `Add block`, four `Edit` buttons, section controls, `Check print`, `History`, `Media`, `Print preview`, `Print / PDF`, `Teacher PDF`, `Student PDF`, and `Export`.
- The first block `Edit` control opened an editor exposing settable `Hook style`, `Headline`, `Body`, and `Anchor concept` fields plus a live preview. The editor was closed without changing or saving content; the Builder remained on the same URL.

## Sanitized network/API evidence

Authenticated read-only GETs from the in-app page returned:

| Method | Path | Status | Relevant result |
| --- | --- | ---: | --- |
| GET | `/api/v1/units/59ad0eb4-da1e-48d3-9cbe-efe4761e4eef` | 200 | approved Grade 7 Mathematics unit |
| GET | `/api/v1/units/59ad0eb4-da1e-48d3-9cbe-efe4761e4eef/path` | 200 | L01 at position 0 with `pack_id=24586f47-c8bd-415a-9a43-cc77401a299b` |
| GET | `/api/v1/builder/lessons/6ebbcec4-fd94-494b-b163-ec4322ae2c3a` | 200 | editable Component Lectio lesson; fields below |

The browser performance resource list also recorded the Builder GET and the Units/path hydration requests. Credentials, headers, prompts, and document prose were not retained in this evidence.

## Editable lesson reconciliation

The Builder GET response is the read-only reconciliation of the persisted editable lesson row:

- `editable_lessons.id`: `6ebbcec4-fd94-494b-b163-ec4322ae2c3a`
- `title`: `Identify the operation`
- `source_type`: `component_lectio`
- `source_generation_id`: `24586f47-c8bd-415a-9a43-cc77401a299b` (matches the expected generation)
- `document`: present with five sections and five Component Lectio blocks
- `updated_at`: `2026-09-05T14:44:31.207002`

## Result

`INVALID_SCOPE_SELECTION` — the Units → Builder path opened the persisted editable Component Lectio lesson with usable controls and no `/studio` fallback (UI/linkage subchecks passed), but the generated L01 content only identifies operations while the campaign scenario requires solving and checking. This generation is excluded from latency/pass statistics; no L02 was started.
