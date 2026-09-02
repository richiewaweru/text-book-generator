# Phase 05 — Typed Failure, Retry and Scoped Repair
## Goal
Make recovery explicit and local.

Reuse `core.llm.runner.RetryPolicy`, existing planning validator-feedback retry, runtime retry runner and current error/status fields/events.

## Changes
1. central failure policy/classifier;
2. separate retry/repair budgets;
3. backoff+jitter for transient/provider limits if current runner lacks sufficient behavior;
4. exact component validation failure → scoped repair payload;
5. siblings stay valid;
6. code/config failures terminal;
7. persist structured last error;
8. emit retry/repair events.

## Injection tests
Timeout, 429, 500, malformed structured output, invalid Lectio payload, failed repair, TypeError, sibling readiness.

## Gate
Each failure class maps to one deterministic recovery action and correct durable error state.
