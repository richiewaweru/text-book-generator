# Run 6 database summary (sanitized)

Read-only reconciliation was performed against the healthy Docker PostgreSQL
database after the run.

| Check | Result |
|---|---|
| Alembic revision | `20260906_0035` (head) |
| Exact generation | `7be66903-f3cc-4594-8c10-0144135d213b` |
| Pipeline marker | `component_lectio` |
| Scalar terminal state | `completed` |
| Chunked terminal stage | `complete` |
| Quality state | `quality_passed=true`; no terminal error |
| Heartbeat/completion | both present and equal at terminal reconciliation |
| Lesson document | present, object-shaped, 5 sections, 6 structured blocks |
| Generation steps | 6 `block_ready`, ordered by `created_at,id` |
| Step attempts | all attempt 1; no failed steps; no recovery retry |
| Linked Builder rows | exactly 1 Component Lectio row |
| Builder id | `ff310d12-a59c-41d5-bb85-cdfc248f8c69` |
| Builder save/reload | `updated_at` advanced; document remained present |
| Run 5 generation | absent; no repair performed |

At the run boundary the database contained 44 generation rows and one new row
for this run since the campaign start window. There was exactly one new
Component Lectio Builder row and six new generation steps. The database total
was 728 `llm_calls`, of which six belong to this generation; all six were
successful and zero were failed. No duplicate generation or Builder row was
created.

The unit remained approved with the expected active path version. Historical
legacy Builder data was not modified and remained excluded from the canonical
history surface.
