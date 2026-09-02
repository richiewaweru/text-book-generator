# Phase 07 — Durable Worker Ownership, Lease and Fencing
## Goal
Remove generation ownership from HTTP request and in-process task dictionaries.

Reuse runner/lanes and existing heartbeat/error fields where present.

## Changes
1. durable DB-backed claim/lease;
2. ownership token + heartbeat + expiry/renewal;
3. mutating writes verify ownership;
4. lease lost → stop, no late write;
5. start/retry persist desired work and return;
6. restart reclaims expired work;
7. replace Studio background-task maps/in-memory ownership locks for canonical path;
8. do not add a heavy queue product if DB leasing is sufficient.

## Tests
Single claim, reclaim after death, late write rejected, heartbeat renewal, restart recovery, retry endpoint returns without long LLM execution.

## Gate
Lesson execution survives request/process lifetime with single-writer ownership.
