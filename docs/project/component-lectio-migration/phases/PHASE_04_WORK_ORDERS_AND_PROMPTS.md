# Phase 04 — Exact Lectio Work Orders, Prompt Migration and Validation
## Goal
Turn selected blocks into exact component-specific work orders and adapt existing executors.

## Reuse
`contracts.lectio` helpers, selected-card pattern in section expander, existing executors, `lectio_validation.py`.

## Changes
1. Inventory all LLM prompts/callers and classify keep/modify/remove/deterministic.
2. Work order includes block ID, section ID, component ID, component purpose, exact component card, schema shape/field contracts, relevant lesson/card context, lane/output field, plan revision.
3. Writer cannot choose component or emit sibling fields.
4. Keep item/question components in dedicated item/question logic where appropriate.
5. Keep visual/media components in visual lane and derive exclusions from Lectio metadata where possible.
6. Complete validation coverage for every generatable selected component.
7. Validate block immediately and assembled SectionContent/document later.
8. Review hard-coded `_EXTERNAL_FIELDS`; replace with Lectio `writer_excluded`/capabilities if equivalence tests pass.

## Tests
All planner-facing cards resolve; all generatable text fields validate; work order contains only selected contract; malformed comparison-grid fails; extra/missing fields behave according to exact contract; visual does not go through generic text writer; writer cannot change component ID.

## Gate
Canonical plan → exact work orders → exact validated component payloads.
