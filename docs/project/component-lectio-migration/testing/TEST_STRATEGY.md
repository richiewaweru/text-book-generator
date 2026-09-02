# Test Strategy
Every phase proves the smallest new responsibility before downstream integration.

- Contract tests: spec IDs vs Lectio, component-card/schema availability, generated Pydantic coverage, LessonDocument round-trip.
- Planning tests: intent plan obeys spec; selector never leaves candidate set; budgets/forbidden/manual-only.
- Runtime unit tests: failure classification, separate retry budgets, repair payload, state transitions, leases/fencing, idempotency.
- Integration tests: plan→selection; selection→work order; work order→writer→validation; invalid→repair→checkpoint; checkpoints→LessonDocument; LessonDocument→Builder.
- Adversarial tests: bad outputs and concurrency races, not only happy paths.
- Full mocked E2E: real application services/DB where possible; only external LLM/media replaced with deterministic fakes.

A phase is not GO if new tests pass but related previously-green tests regress.
