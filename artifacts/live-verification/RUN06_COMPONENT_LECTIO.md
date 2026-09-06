# Run 6 — Grade 8 Social Studies post-cutover verification

**Campaign capacity:** provider-capacity run **6 of 12** (the separate campaign ledger counters were not rewritten).
**Environment:** local Docker PostgreSQL, one serving backend worker, in-app browser.
**Exact SHA:** `4853d1f4a9ffc3b9625058b56af1dabaabb73ea0` (`fix(lectio): expose authoritative Builder completion`).
**Classification:** `PASS` for this text-only post-cutover proof.

## Scenario and route

The Units workflow used the Grade 8 History/Social Studies target to compare
major causes of the Industrial Revolution and explain causal links. The
requested lesson settings were 45 minutes, on-grade reading/learner level, no
language support, lesson resource type, and the legal guided-concept path
preset.

The browser route began at `/units` and finished at:

`/builder/ff310d12-a59c-41d5-bb85-cdfc248f8c69`

The selected path lesson was `c86444f2-cd28-447d-addf-4054ed0ebd6c`; the path
was approved and contained four lessons. The generated lesson title was
`Comparing Causes and Explaining Their Causal Links`.

The only active product route exercised was `/units → Component Lectio →
Builder`. No Studio navigation, legacy generation, retry, or second
generation was used.

## Reconciliation

- Generation: `7be66903-f3cc-4594-8c10-0144135d213b`.
- Persisted pipeline: `component_lectio` in the generation control marker and
  control metadata.
- Terminal scalar state: `status=completed`, `quality_passed=true`,
  `completed_at` and `last_heartbeat` present.
- Terminal chunked state: `stage=complete`, `failed_sections=[]`, no persisted
  error, and `partial=false`.
- Document: present as a structured object with five sections and six blocks;
  every block has an id, component id, position, and structured content.
- Builder: exactly one Component Lectio row links the generation to
  `ff310d12-a59c-41d5-bb85-cdfc248f8c69`.
- Builder save/reload: the Builder row's `updated_at` advanced after the UI
  save/reload check; the persisted document remained valid after reload.
- Dashboard: canonical `/api/v1/generations` history was used; the completed
  generation linked to Builder, not Studio.
- Run 5 repair check: generation
  `825f0f9e-2221-4e96-8160-44f07a02aa54` is absent from this campaign database;
  no linkage repair or provider call was attempted.

## Selection and execution observability

The persisted `selection_trace` and canonical-plan trace each contain five
section decisions. Sanitized trace entries retain section role, legal-choice
flag, selected component id, section field, lane, candidate-set metadata,
budget-before metadata, and selection reason. No trace entry selected a visual
component; the run therefore made no visual/provider-QC request.

Six ordered `block_ready` events were persisted. All six used attempt `1` and
`recovery=none`; no block failed and no retry was issued. The six successful
LLM calls were persisted with `caller=v3_execution`, openai-compatible
transport, DeepSeek models, `api.deepseek.com`, and standard/fast lanes. No
failed call or transport retry was recorded for this generation.

## Acceptance result

`PASS`: valid text-only LessonDocument, truthful completed terminal state,
exact Component Lectio pipeline marker, one Builder lesson, Builder save/reload
survival, canonical dashboard linkage, no generation concurrency, and no
Legacy fallback.

This single pass does not by itself satisfy the campaign's four-consecutive
local or four-hosted-run gates. Visual behavior remains outside this proof.
