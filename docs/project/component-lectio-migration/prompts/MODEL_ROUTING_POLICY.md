# Model Routing Policy
Route by actual planning node / Lectio component responsibility, not page content type.

Central configuration owns model tier selection; writers do not hard-code providers/models.

Direction:
- structural/intent planning: reasoning tier;
- constrained component selection: current proven fast/standard tier;
- conceptually dense explanations/worked examples/process reasoning: standard unless tests prove fast quality;
- simple structured content: fast only after tests;
- repair: fast or same writer tier;
- questions/items: existing dedicated route;
- visuals: existing visual provider;
- IDs/order/candidate filtering/budgets/dependencies/retries: deterministic code.

Do not optimize routing until functional correctness is green. Phase 08 may tune with evidence.
