# Phase 06 — Durable Checkpoints, Resume and Idempotency
## Goal
Validated work becomes reusable progress.

Reuse GenerationStepModel append-only persistence, step helpers/fold patterns, GenerationModel chunked state and current revisions.

## Changes
1. explicit persisted runtime state;
2. immutable steps for completed work;
3. no giant mutable concurrent per-block blob;
4. idempotency/uniqueness protection for duplicate start/retry;
5. resume schedules only missing/retryable work;
6. persist plan revision/hash with work;
7. retain raw output/errors only where useful and bounded;
8. always persist terminal/complete.

## Tests
Crash after B1-B3; B4 repair only; duplicate retry; plan revision change; concurrent inserts; terminal/complete survive restart.

## Gate
Generation reconstructs/resumes from DB without in-process memory.
