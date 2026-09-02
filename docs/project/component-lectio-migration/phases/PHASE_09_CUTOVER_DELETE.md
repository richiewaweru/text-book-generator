# Phase 09 — Cutover and Legacy/Junk Removal
## Goal
Canonical lesson path becomes the only production path and superseded iterations are removed.

## Deletion gates
Before deleting V3 Studio: new start/status/retry, worker, visual regenerate, Builder direct open, polling/streaming, PDF, required history/detail, telemetry replacement, no frontend dependency on V3 pack adapter.

## Then remove
### Backend
- obsolete `generation/v3_studio/*` orchestration/session-store/DTO/prompt helpers;
- startup `V3GenerationWriter.fail_stale_running()` dependency once leases own recovery;
- V3 Studio router mount;
- temporary legacy plan adapters when no supported persisted data requires them;
- orphaned old prompts/resources.

### Frontend
- Studio routes/components/store;
- V3 pack→Lectio adapter;
- retire/split `api/v3.ts` dead Studio operations;
- legacy unit route if unused.

### Resource flow
- remove worksheet/quiz/etc from primary creation flow;
- lesson is the production primary resource;
- do not implement derivative generation yet;
- keep old YAML only if explicitly retained for future derivative design or tooling, otherwise park/delete with report.

Run repository-wide zero-caller searches for every deleted symbol/module and full regression suite.

## Gate
One production lesson generation path, one Builder-native document path, no silent legacy fallback.
