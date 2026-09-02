# Codex Computer-Use Handoff
Run only after Phase 10 GO.

Cursor proves deterministic/mocked architecture. Codex then proves real DB/server/provider/browser/rendering.

Checklist:
1. Start supported DB/backend/frontend/worker workflow.
2. Confirm migrations and worker healthy.
3. Create/use a unit path.
4. Generate at least four lessons with the same general lesson spec: math, science, social studies/history, English.
5. Record generation/unit/lesson IDs, intent plan, components, stage timings, retries/repairs, model calls, final status, Builder result, PDF result.
6. Exercise browser refresh, SSE/poll reconnect, component regeneration, visual regeneration, and safe human-edit race if possible.
7. Verify logs show validator errors + block/component IDs.
8. Verify removed Studio routes/modules are not hit.
9. Verify valid blocks are not unnecessarily regenerated.
10. Verify terminal failures are visible and only retryable when policy says so.

Output a live verification report with reproduction steps, logs/IDs, failure layer classification, smallest fix, and regression test to add before fixing.

After several real runs, quantify schema failures and only then decide whether to implement forced strict-tool API schemas for DeepSeek/OpenAI-compatible providers.
