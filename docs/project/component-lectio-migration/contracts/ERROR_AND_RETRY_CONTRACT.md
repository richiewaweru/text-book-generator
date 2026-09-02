# Error, Retry and Repair Contract

A retry is not a repair. A schema failure is not a network timeout. A code bug is not model variance.

## Required classes
- `transport_retryable`: connection resets, transient provider 5xx/timeouts.
- `rate_limited`: 429/throttling; backoff+jitter.
- `model_output_retryable`: malformed structured output before component validation.
- `component_repairable`: parsed output violates selected Lectio contract/semantic invariant.
- `visual_retryable`: scoped visual/media transient failure.
- `terminal_code_error`: programmer/config/impossible-invariant failures.
- `lease_lost`: worker no longer owns generation; stop without writing.
- `cancelled`: explicit stop.

## Separate budgets
Initial target unless equivalent config already exists:
```text
transport_attempts: 3
rate_limit_attempts: 3
model_output_attempts: 2
component_repairs: 1
```

A component repair call receives: block/component ID, purpose, invalid output, exact validator errors, exact component card/schema, and instruction to return only corrected component payload.

Reuse current planning behavior that feeds validation errors into a later attempt and isolates failed sections, but generalize it into runtime policy.

## Strict schema deferral
Do not add forced strict-tool/provider schemas in this round. Runtime Pydantic/Lectio validation remains authoritative.
