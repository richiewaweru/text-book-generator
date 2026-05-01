from __future__ import annotations

import os

from core.llm import ModelFamily, ModelSlot, ModelSpec

PLANNING_SECTION_COMPOSER_CALLER = "section_composer"
PLANNING_SECTION_COMPOSER_SLOT = ModelSlot.STANDARD
PLANNING_ENRICHMENT_CALLER = "planning_enrichment"
PLANNING_ENRICHMENT_SLOT = ModelSlot.STANDARD
PLANNING_VISUAL_ROUTER_CALLER = "visual_router"
PLANNING_VISUAL_ROUTER_SLOT = ModelSlot.STANDARD
PLANNING_TOPIC_RESOLUTION_CALLER = "topic_resolution"
PLANNING_TOPIC_RESOLUTION_SLOT = ModelSlot.FAST
PLANNING_BRIEF_REVIEW_CALLER = "brief_review"
PLANNING_BRIEF_REVIEW_SLOT = ModelSlot.FAST
LEARNING_JOB_INTERPRETER_CALLER = "learning_job_interpreter"
LEARNING_JOB_INTERPRETER_SLOT = ModelSlot.FAST
PACK_LEARNING_PLANNER_CALLER = "pack_learning_planner"
PACK_LEARNING_PLANNER_SLOT = ModelSlot.FAST

PLANNING_MODEL_SPECS: dict[str, tuple[ModelSlot, ModelSpec]] = {
    PLANNING_SECTION_COMPOSER_CALLER: (
        PLANNING_SECTION_COMPOSER_SLOT,
        ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
    ),
    PLANNING_ENRICHMENT_CALLER: (
        PLANNING_ENRICHMENT_SLOT,
        ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
    ),
    PLANNING_VISUAL_ROUTER_CALLER: (
        PLANNING_VISUAL_ROUTER_SLOT,
        ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
    ),
    PLANNING_TOPIC_RESOLUTION_CALLER: (
        PLANNING_TOPIC_RESOLUTION_SLOT,
        ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
    ),
    PLANNING_BRIEF_REVIEW_CALLER: (
        PLANNING_BRIEF_REVIEW_SLOT,
        ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
    ),
    LEARNING_JOB_INTERPRETER_CALLER: (
        LEARNING_JOB_INTERPRETER_SLOT,
        ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
    ),
    PACK_LEARNING_PLANNER_CALLER: (
        PACK_LEARNING_PLANNER_SLOT,
        ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
    ),
}


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return None


def _env_override(caller: str, *, base: ModelSpec) -> ModelSpec | None:
    prefix = f"PLANNING_{caller.upper()}"
    family_raw = _first_env(f"{prefix}_PROVIDER")
    model_name = _first_env(f"{prefix}_MODEL_NAME")
    base_url = _first_env(f"{prefix}_BASE_URL")
    api_key_env = _first_env(f"{prefix}_API_KEY_ENV")

    if not any((family_raw, model_name, base_url, api_key_env)):
        return None

    if family_raw is None:
        family = base.family
    elif family_raw.strip().lower() in {"google", "gemini"}:
        family = ModelFamily.GOOGLE
    elif family_raw.strip().lower() in {"openai_compatible", "openai-compatible", "openai"}:
        family = ModelFamily.OPENAI_COMPATIBLE
    elif family_raw.strip().lower() == "anthropic":
        family = ModelFamily.ANTHROPIC
    elif family_raw.strip().lower() == "test":
        family = ModelFamily.TEST
    else:
        raise ValueError(
            f"Unsupported model family '{family_raw}'. "
            "Expected one of: anthropic, google, openai_compatible, test."
        )

    return ModelSpec(
        family=family,
        model_name=model_name or base.model_name,
        base_url=base_url if base_url is not None else base.base_url,
        api_key_env=api_key_env if api_key_env is not None else base.api_key_env,
    )


def get_planning_slot(caller: str) -> ModelSlot:
    try:
        slot, _ = PLANNING_MODEL_SPECS[caller]
        return slot
    except KeyError as exc:
        raise ValueError(f"Planning caller '{caller}' is not registered.") from exc


def get_planning_spec(caller: str) -> ModelSpec:
    try:
        _, base = PLANNING_MODEL_SPECS[caller]
    except KeyError as exc:
        raise ValueError(f"Planning caller '{caller}' is not registered.") from exc
    override = _env_override(caller, base=base)
    return override or base
