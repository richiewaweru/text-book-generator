# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog conventions with SemVer release tags.

## [0.1.0] - 2026-03-11

### Added
- Phase 1: Full project scaffolding — DDD backend (FastAPI), SvelteKit frontend, all entity schemas, pipeline node base class, 3 test fixtures, provider factory, HTML renderer skeleton.
- Phase 2: Runtime logic — all 6 pipeline nodes implemented, both LLM providers (Anthropic + OpenAI), HTML renderer with dark-theme CSS, orchestrator with progress callbacks, async generation API, frontend wiring. 64 tests.
- Phase 3: Authentication & profiles — Google OAuth + JWT, persistent student profiles (SQLite), profile CRUD API, onboarding flow, dashboard, CLI removed. 76 tests.
- Phase 3.1: Renamed `LearnerProfile` to `GenerationContext` for clarity. Added `learner_description` free-text field and wired `prior_knowledge` through prompts.
