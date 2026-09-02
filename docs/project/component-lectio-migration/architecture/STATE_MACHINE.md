# Runtime State Machine
Use current stable API status strings where practical; preserve these semantics.

Generation concept:
```text
queued → running → waiting_for_teacher → running → complete
                 ↘ failed_retryable / failed_terminal / cancelled
```

Block/work concept:
```text
pending → running → ready
              ↘ repairing → running/ready
              ↘ failed_retryable / failed_terminal / cancelled
```

Persist at generation scope: approved plan revision/hash, worker/lease token, heartbeat, desired work kind, broad stage, structured last error, document revision/hash where useful.

Persist at step scope: stable block ID, plan revision, component/work kind, attempt/repair metadata, validated payload/checkpoint, output hash, completion timestamp, structured failure.

Prefer immutable step rows for completed work and broad mutable control state only at generation scope.
