# Component Contract Verification Matrix
Phase 04 should generate this matrix programmatically from the current Lectio contract, not maintain a duplicate registry.

For each planner-facing component record:
- component ID;
- section field;
- cognitive job;
- writer_excluded;
- capabilities;
- schema ref;
- generated Pydantic model availability;
- producer/lane;
- block validator;
- repair owner;
- template availability.

Fail if a planner-selectable component lacks a known producer/validator strategy. Inline/manual-only components must not enter AI candidate sets. Visual/media components must not silently pass generic text validation. Question/answer-key relationships remain owned by item/question logic where applicable.
