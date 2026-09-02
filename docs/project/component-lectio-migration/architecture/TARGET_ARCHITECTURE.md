# Target Architecture
```text
UNIT PATH
   ↓
LESSON CONTEXT
   ↓
GENERAL LESSON SPEC
   ↓
STRUCTURAL / INTENT PLANNER
   ↓ teacher approval/edit
CONSTRAINED COMPONENT SELECTOR
   ↓
CANONICAL EXECUTION PLAN
   ↓
SELECTED LECTIO CONTRACT LOOKUP
   ↓
WORK ORDERS
   ├── CONTENT EXECUTOR
   ├── ITEM/QUESTION EXECUTOR
   └── VISUAL EXECUTOR
   ↓
VALIDATE / REPAIR / RETRY
   ↓
DURABLE CHECKPOINTS
   ↓
LECTIO LESSONDOCUMENT
   ↓
BUILDER
   ↓
RENDER / PDF
```

This is not a rewrite. It reuses current specs, Lectio exports, planner ideas, executors, immutable steps, streaming/polling and Builder. The main changes are responsibility separation, exact narrowing, durability, local recovery and removal of Studio orchestration/conversion.
