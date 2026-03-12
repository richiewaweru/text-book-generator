# Schemas

Current schema source of truth lives in `backend/src/textbook_agent/domain/entities/` and `backend/src/textbook_agent/application/dtos/`.

## Core Entities

### `SectionContent`
- `section_id`
- `hook`
- `prerequisites_block`
- `plain_explanation`
- `formal_definition`
- `worked_example`
- `common_misconception`
- `practice_problems`
- `interview_anchor`
- `think_prompt`
- `connection_forward`

### `PracticeProblem`
- `difficulty`: `warm | medium | cold`
- `statement`
- `hint`

### `QualityIssue`
- `section_id`
- `issue_type`
- `description`
- `severity`
- `check_source`: `mechanical | llm`

### `QualityReport`
- `passed`
- `issues`
- `checked_at`

## Generation DTOs

### `GenerationRequest`
- `subject`
- `context`
- optional `depth`
- optional `language`
- optional `provider`

### `GenerationStatus`
- `id`
- `status`
- optional `progress`
- optional `result`
- optional `error`
- optional `error_type`

`GenerationStatus.result` is a public summary, not the internal artifact path.

## Viewer Contract

- The public viewer identity is the generation ID.
- Public HTML fetch is generation-owned and authenticated.
- Stored output paths remain internal implementation details.
