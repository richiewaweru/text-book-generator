# Phase 08 — Direct LessonDocument and Live Builder
## Goal
Generated artifact is directly Builder-native and durable progress streams into Builder.

Reuse Lectio LessonDocument semantics, Builder CRUD/store/sync, generation poller, live stream reconciliation, Builder generation-stream, visual regeneration and block generation.

## Changes
1. assemble checkpoints directly into valid LessonDocument;
2. stop treating V3 pack as canonical;
3. use stable canonical block IDs;
4. partial lesson can open; ready blocks appear as checkpoints land;
5. reconnect reconstructs from persisted state;
6. add human-edit revision fence so newer teacher edit beats stale generator;
7. preserve save/reopen/block AI/visual/PDF;
8. simplify occurrence-count inference where stable IDs make it unnecessary;
9. tune model routing only after correctness is green and only with evidence.

## Tests
Partial open, ready block while unrelated visual pending, reconnect, SSE→poll catch-up, human edit race, save/reopen, block AI, visual regenerate, final document validation, PDF/document order.

## Gate
No Studio adapter required for canonical generated lesson to edit in Builder.
