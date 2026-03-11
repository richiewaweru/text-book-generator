# Architecture - v0.1.0

## Overview

The Textbook Generation Agent is a full-stack application with a Python/FastAPI backend and SvelteKit frontend. The backend uses Domain-Driven Design (DDD) with four layers. The core domain is a 6-node pipeline that transforms a learner profile into a personalized textbook.

## System Diagram

```
┌─────────────────────────────────┐     ┌─────────────────────┐
│       SvelteKit Frontend        │────▶│   FastAPI Backend    │
│  (Profile Form, Viewer, Status) │◀────│   (REST API)        │
└─────────────────────────────────┘     └────────┬────────────┘
                                                  │
                                        ┌────────▼────────────┐
                                        │  Application Layer   │
                                        │  (Use Cases, Agent)  │
                                        └────────┬────────────┘
                                                  │
                                        ┌────────▼────────────┐
                                        │   Domain Layer       │
                                        │  (Pipeline Nodes,    │
                                        │   Schemas, Prompts)  │
                                        └────────▲────────────┘
                                                  │ implements ports
                                        ┌────────┴────────────┐
                                        │ Infrastructure Layer │
                                        │ (LLM Providers,     │
                                        │  Storage, Renderer)  │
                                        └─────────────────────┘
```

## DDD Layer Architecture

### Interface Layer (`interface/`)

**Purpose**: Delivery mechanisms. Receives external input and delegates to the application layer.

- `api/` - FastAPI routes, app factory, dependency injection
- `cli/` - Command-line interface entry point

**Depends on**: Application layer only.

### Application Layer (`application/`)

**Purpose**: Orchestration and use case coordination. Translates between interface and domain.

- `use_cases/` - `GenerateTextbookUseCase`, `CheckQualityUseCase`
- `orchestrator.py` - `TextbookAgent` wires the 6-node pipeline
- `dtos/` - Request/response objects for layer boundaries

**Depends on**: Domain layer (entities, ports).

### Domain Layer (`domain/`)

**Purpose**: Core business logic. Zero framework dependencies (only `pydantic` for schema validation).

- `entities/` - Pydantic models: `LearnerProfile`, `CurriculumPlan`, `SectionContent`, etc.
- `value_objects/` - `Depth`, `NotationLanguage`, `SectionDepth` enums
- `services/` - The 6 pipeline nodes that ARE the business logic
- `prompts/` - Pedagogical rules and prompt construction (domain knowledge)
- `ports/` - Abstract interfaces (`BaseProvider`, `TextbookRepository`, `FileStoragePort`)
- `exceptions.py` - Domain-specific errors

**Depends on**: Nothing external. This is the innermost layer.

### Infrastructure Layer (`infrastructure/`)

**Purpose**: Adapters for external systems. Implements domain ports.

- `providers/` - `AnthropicProvider`, `OpenAIProvider`, `ProviderFactory`
- `storage/` - `FileSystemStorage` (reads profiles, writes outputs)
- `repositories/` - `FileTextbookRepository` (persists textbooks)
- `renderer/` - `HTMLRenderer` (pure Python, no LLM) + CSS design system
- `config/` - `Settings` (Pydantic Settings from `.env`)

**Depends on**: Domain ports (implements them).

## Dependency Rule

```
Interface → Application → Domain ← Infrastructure
```

Domain NEVER imports from any other layer. Infrastructure implements domain ports via dependency inversion.

## The 6-Node Pipeline

```
LearnerProfile
     ↓
[Node 1] CurriculumPlanner    → CurriculumPlan
     ↓
[Node 2] ContentGenerator     → list[SectionContent]     (per section)
     ↓
[Node 3] DiagramGenerator     → list[SectionDiagram]     (per section needing visual)
     ↓
[Node 4] CodeGenerator        → list[SectionCode]        (per section needing code)
     ↓
[Node 5] Assembler            → RawTextbook               (pure Python, no LLM)
     ↓
[Node 6] QualityChecker       → QualityReport             (LLM validates)
     ↓
  PASS → HTMLRenderer → final output
  FAIL → re-run flagged nodes → check again
```

Every node inherits from `PipelineNode[TInput, TOutput]` with:
- Typed input/output schemas enforced by Pydantic
- Retry logic (default 2 retries)
- Validation before and after execution

## Provider Architecture

All LLM calls go through the abstract `BaseProvider` port:

```python
class BaseProvider(ABC):
    def complete(self, system_prompt, user_prompt, response_schema, ...) -> Any: ...
    def name(self) -> str: ...
```

Swapping Claude for GPT-4 is a config change. The domain never knows which provider is active.

## Bounded Context

There is one bounded context: **Textbook Generation**. The pipeline is the aggregate root. All entities serve the pipeline's data flow.

## Frontend

SvelteKit with TypeScript. Three core components:
- `ProfileForm` - Learner profile input
- `GenerationProgress` - Real-time pipeline status
- `TextbookViewer` - Renders the HTML textbook output

Communicates with backend via REST API (`/api/v1/generate`, `/api/v1/status/{id}`).
