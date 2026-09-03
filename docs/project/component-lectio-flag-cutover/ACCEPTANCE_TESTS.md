# Acceptance Tests — Casa Phase

These are implementation tests, not the later live Codex product verification.

Casa should run the repository's existing lint/typecheck/unit/build gates plus the targeted cases below.

## Gate 1 — default selection

With default:

```text
GENERATION_PIPELINE_DEFAULT=component_lectio
```

admit a generation.

Assert:

```text
persisted pipeline == component_lectio
```

and dispatch targets the production Component Lectio service.

FAIL if the request reaches the mocked pipeline.  
FAIL if V3 Studio owns generation execution.

## Gate 2 — explicit rollback

Set:

```text
GENERATION_PIPELINE_DEFAULT=v3_studio
```

Create a new generation.

Assert persisted pipeline is `v3_studio` and the legacy flow remains usable.

## Gate 3 — immutable per-generation pipeline

1. Set default to `component_lectio`.
2. Admit generation A.
3. Change default to `v3_studio`.
4. Request status/retry/resume for A.

Assert A remains `component_lectio`.

Then create B and assert B uses `v3_studio`.

## Gate 4 — no automatic fallback

Inject a controlled exception after Component Lectio dispatch.

Assert:

```text
legacy call count == 0
```

and the failure is recorded against Component Lectio.

## Gate 5 — real writer proof

Spy/mock the existing real executor boundary.

Assert:

```text
real executor called
mock_writer not called
```

The deterministic mocked pipeline can retain its own unit tests.

## Gate 6 — exact component identity

Use known:

```text
block_id
component_id
section_id
position
```

Run through work-order translation to executor dispatch.

Assert identity remains unchanged.

If an executor changes component identity, validation rejects it.

## Gate 7 — durable state proof

With test DB:

1. create generation;
2. persist at least one ready/checkpoint event;
3. destroy/recreate service/repository objects;
4. reload state from DB.

Assert ready work is reconstructed.

## Gate 8 — resume does not regenerate ready blocks

Persist:

```text
B1 ready
B2 missing
B3 ready
```

Resume and assert only `B2` executes.

## Gate 9 — pipeline marker observable

For Component Lectio assert:

```text
DB state: component_lectio
status/detail API: component_lectio
structured log/event: component_lectio
```

Optional header may also be checked.

## Gate 10 — historical row

Load a representative old generation without pipeline marker.

Assert resolver returns:

```text
v3_studio
```

with inference logging.

## Gate 11 — Builder direct contract

For Component Lectio with canonical LessonDocument:

Assert Builder ingestion does not call:

```text
adaptV3PackToLectioDocument
```

For V3 Studio, assert legacy adapter still works.

## Gate 12 — public UI compatibility smoke

Verify:

- frontend compiles;
- generation UI can submit/request generation;
- status response shape does not crash frontend;
- Builder can open a Component Lectio-shaped lesson in test/fixture form;
- legacy mode still compiles.

## Gate 13 — config validation

Assert:

```text
GENERATION_PIPELINE_DEFAULT=banana
```

fails clearly at settings/startup validation.

## Gate 14 — no legacy deletion

Verify `backend/src/generation/v3_studio/*` remains.

## Gate 15 — no broad drift

FAIL this phase if implementation unnecessarily introduces:

- a second component registry;
- duplicate Lectio schemas;
- a second writer family;
- Redis/new queue infrastructure;
- page-oriented semantics;
- broad endpoint rename;
- legacy deletion;
- unrelated UI redesign.

## Existing repository gates

Use the repository's actual scripts for:

```text
backend unit tests
backend lint/type checks where configured
frontend lint
frontend typecheck
frontend tests
frontend production build
```

## Phase verdict

Finish with exactly one:

```text
READY FOR INSPECTION
PARTIALLY READY — BLOCKERS REMAIN
BLOCKED
```

`READY FOR INSPECTION` requires:

- flag exists;
- default is Component Lectio;
- rollback works;
- live entrypoint uses real executors;
- pipeline identity is persisted;
- no silent fallback;
- status/retry bind to persisted pipeline;
- Builder has a viable direct Component Lectio ingestion path;
- targeted tests pass.

It does not mean production stability has been proven.
