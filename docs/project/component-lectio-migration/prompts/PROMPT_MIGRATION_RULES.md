# Prompt Migration Rules

## Inventory every LLM call
Record caller/node, prompt, model slot, structured output model, context, metadata, validation, retry/repair, and keep/modify/remove/deterministic disposition.

## Structural/intent planner
Receives lesson objective/context, learner/support info, resolved general lesson spec roles/depth and legal role vocabulary. It should not receive every component schema or invent component IDs. Output focuses on ordered lesson roles and concept-specific purpose.

## Component selector
Promote `component-selector-v1.txt` behavior. Input per role:
- role/slot ID and concept-specific purpose;
- only deterministic legal candidates after spec+template+budget filtering;
- lightweight candidate metadata: component ID, `cognitive_job`, role, section field, capabilities, capacity summary;
- lesson/card context needed for the local choice;
- remaining budgets.
Output: selected IDs, specific purpose, concise reason tied to cognitive job, budget pressure if any.

## Section/component briefing
If separate Stage 2 remains useful, it operates only on selected components and exact cards. If redundant, collapse it into deterministic work-order construction rather than retain an LLM stage ceremonially.

## Writers
Each call receives stable block/section ID, selected component ID, exact purpose, necessary lesson context, exact component card/schema/field contracts/capacity, and approved upstream facts/items. It returns only that component payload.

## Repair
Repair one component only with invalid payload + exact validator errors + exact same contract.

## Items/questions and visuals
Preserve dedicated lanes; generic writers must not reinvent approved items or own visual generation.

## Strict tool
No forced strict-tool API migration now.
