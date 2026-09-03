# Casa Completion Report Template

## 1. Verdict

Choose exactly one:

```text
READY FOR INSPECTION
PARTIALLY READY — BLOCKERS REMAIN
BLOCKED
```

Give a short reason.

## 2. Repository identity

```text
repo:
branch:
starting commit:
ending commit:
dirty state before:
dirty state after:
```

Preserve pre-existing user changes.

## 3. Feature flag

```text
setting name:
allowed values:
default:
Vercel value required:
startup validation:
```

Show exact typed settings definition.

## 4. Dispatch boundary

Show actual flow:

```text
HTTP/UI call
↓
...
↓
pipeline selector
├ component_lectio
└ v3_studio
```

Give exact files/functions.

## 5. Persistence

Where is pipeline identity persisted?

Show representative sanitized state.

Explain how historical unmarked rows resolve.

## 6. Component Lectio production entrypoint

Give exact function.

Prove it:

```text
does not call mock_writer
does not call run_mocked_component_lectio_pipeline
uses real execution infrastructure
```

List real executor functions used.

## 7. Durable checkpoint / execution ownership

State clearly:

```text
checkpoint persistence: DB-backed / not DB-backed
lease/ownership: DB-backed / not DB-backed
resume after process restart: proven / not proven
```

Do not describe in-memory stand-ins as durable.

## 8. Builder contract

Show:

```text
component_lectio path → ?
v3_studio path        → ?
```

State whether Component Lectio bypasses `v3-pack-to-lectio-document`.

## 9. No-fallback proof

Describe the test proving Component Lectio failure did not call Studio.

## 10. Retry/status binding

Explain how an existing generation resolves its pipeline after the environment default changes.

List endpoints/functions covered.

## 11. Observability

List:

```text
persisted marker
status/detail field
structured log/event
optional response header
```

## 12. Tests executed

| Command/test | Result | Notes |
|---|---|---|
| ... | PASS/FAIL | ... |

Include targeted flag tests and normal repository gates.

## 13. Files changed

### Created
```text
...
```

### Modified
```text
...
```

### Deleted

Expected:

```text
none
```

## 14. Remaining blockers before Codex live run

Classify:

```text
P0 — blocks live test
P1 — test can run but evidence/reliability incomplete
P2 — cleanup/optimization after test
```

Examples of P0:

- live route still invokes mocked writers;
- Component Lectio cannot be reached by normal UI;
- pipeline identity cannot be proven;
- new path cannot persist generation state;
- Builder cannot consume output;
- hidden fallback to V3 Studio.

## 15. Legacy path status

Confirm:

```text
V3 Studio still present:
legacy rollback tested:
no deletion performed:
```

## 16. Operator instructions

New-path default:

```text
GENERATION_PIPELINE_DEFAULT=component_lectio
```

Rollback:

```text
GENERATION_PIPELINE_DEFAULT=v3_studio
```

Include restart/redeploy requirement.

## 17. Recommended next action

Do not perform it.

State whether the branch is ready for the separate Codex full-computer-use live verification.
