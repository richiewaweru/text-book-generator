from __future__ import annotations

import os

from core.llm import ModelFamily, ModelSlot, ModelSpec

PLANNING_SECTION_COMPOSER_CALLER = "section_composer"
LEARNING_JOB_INTERPRETER_CALLER = "learning_job_interpreter"
PACK_LEARNING_PLANNER_CALLER = "pack_learning_planner"

_MODEL_SPECS: dict[str, tuple[ModelSlot, ModelSpec]] = {
    PLANNING_SECTION_COMPOSER_CALLER: (
        ModelSlot.STANDARD,
        ModelSpec(family=ModelFamily.ANTHROPIC, model_name="claude-sonnet-4-6"),
    ),
    LEARNING_JOB_INTERPRETER_CALLER: (
        ModelSlot.FAST,
        ModelSpec(family=ModelFamily.ANTHROPIC, model_name="claude-haiku-4-5-20251001"),
    ),
    PACK_LEARNING_PLANNER_CALLER: (
        ModelSlot.FAST,
        ModelSpec(family=ModelFamily.ANTHROPIC, model_name="claude-haiku-4-5-20251001"),
    ),
}


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return None


def _env_override(caller: str, *, base: ModelSpec) -> ModelSpec | None:
    prefix = f"LEARNING_{caller.upper()}"
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
        raise ValueError(f"Unsupported model family '{family_raw}'.")
    return ModelSpec(
        family=family,
        model_name=model_name or base.model_name,
        base_url=base_url if base_url is not None else base.base_url,
        api_key_env=api_key_env if api_key_env is not None else base.api_key_env,
    )


def get_planning_slot(caller: str) -> ModelSlot:
    try:
        slot, _ = _MODEL_SPECS[caller]
        return slot
    except KeyError as exc:
        raise ValueError(f"Learning caller '{caller}' is not registered.") from exc


def get_planning_spec(caller: str) -> ModelSpec:
    try:
        _, base = _MODEL_SPECS[caller]
    except KeyError as exc:
        raise ValueError(f"Learning caller '{caller}' is not registered.") from exc
    return _env_override(caller, base=base) or base
