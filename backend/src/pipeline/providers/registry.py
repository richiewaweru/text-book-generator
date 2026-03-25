"""
Central command center for pipeline text model selection.

The pipeline speaks in terms of node intent, not vendor-specific clients:

- nodes map to slots (`fast`, `standard`, `creative`)
- code defaults define a `ModelSpec` profile for each generation mode
- slot-scoped env overrides can replace those defaults
- transport families turn a `ModelSpec` into the concrete PydanticAI model

This keeps the control plane easy to debug while letting OpenAI-compatible
providers share one code path through `openai_compatible`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from typing import Any
from urllib.parse import urlparse

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel

from pipeline.types.requests import GenerationMode


class ModelSlot(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    CREATIVE = "creative"


class ModelFamily(str, Enum):
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI_COMPATIBLE = "openai_compatible"
    TEST = "test"


@dataclass(frozen=True)
class ModelSpec:
    """Resolved transport configuration for one text-model slot."""

    family: ModelFamily
    model_name: str
    base_url: str | None = None
    api_key_env: str | None = None


NODE_MODEL_SLOTS: dict[str, ModelSlot] = {
    "curriculum_planner": ModelSlot.FAST,
    "content_generator": ModelSlot.STANDARD,
    "content_generator_repair": ModelSlot.STANDARD,
    "diagram_generator": ModelSlot.FAST,
    "qc_agent": ModelSlot.FAST,
    "field_regenerator": ModelSlot.FAST,
}

_DEFAULT_PROFILES_BY_MODE: dict[GenerationMode, dict[ModelSlot, ModelSpec]] = {
    GenerationMode.DRAFT: {
        ModelSlot.FAST: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
        ModelSlot.STANDARD: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
        ModelSlot.CREATIVE: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
    },
    GenerationMode.BALANCED: {
        ModelSlot.FAST: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-haiku-4-5-20251001",
        ),
        ModelSlot.STANDARD: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
        ModelSlot.CREATIVE: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
    },
    GenerationMode.STRICT: {
        ModelSlot.FAST: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
        ModelSlot.STANDARD: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
        ModelSlot.CREATIVE: ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name="claude-sonnet-4-6",
        ),
    },
}

_OPENAI_COMPATIBLE_SYSTEMS = {
    "openai",
    "openai-chat",
    "openai-responses",
    "alibaba",
    "azure",
    "cerebras",
    "deepseek",
    "fireworks",
    "github",
    "grok",
    "heroku",
    "litellm",
    "moonshotai",
    "nebius",
    "ollama",
    "openrouter",
    "ovhcloud",
    "sambanova",
    "together",
    "vercel",
}


def _normalize_family(raw: str) -> ModelFamily:
    value = raw.strip().lower()
    if value == "anthropic":
        return ModelFamily.ANTHROPIC
    if value in {"google", "gemini"}:
        return ModelFamily.GOOGLE
    if value in {"openai_compatible", "openai-compatible", "openai"}:
        return ModelFamily.OPENAI_COMPATIBLE
    if value == "test":
        return ModelFamily.TEST
    raise ValueError(
        f"Unsupported model family '{raw}'. "
        "Expected one of: anthropic, google, openai_compatible."
    )


def _slot_prefix(slot: ModelSlot) -> str:
    """Return the canonical env prefix for a slot."""

    return f"PIPELINE_{slot.name}"


def _first_env(*names: str) -> str | None:
    """Return the first non-empty env var value from the provided names."""

    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return None


def _env_override(slot: ModelSlot, *, base: ModelSpec) -> ModelSpec | None:
    """
    Load a slot override from the canonical `PIPELINE_{SLOT}_*` env contract.

    The override is sparse: any provided field replaces the code default for
    that slot, while omitted fields continue to inherit from `base`.
    """

    prefix = _slot_prefix(slot)

    family_raw = _first_env(f"{prefix}_PROVIDER")
    model_name = _first_env(f"{prefix}_MODEL_NAME")
    base_url = _first_env(f"{prefix}_BASE_URL")
    api_key_env = _first_env(f"{prefix}_API_KEY_ENV")

    if not any((family_raw, model_name, base_url, api_key_env)):
        return None

    family = _normalize_family(family_raw) if family_raw is not None else base.family
    return ModelSpec(
        family=family,
        model_name=model_name or base.model_name,
        base_url=base_url if base_url is not None else base.base_url,
        api_key_env=api_key_env if api_key_env is not None else base.api_key_env,
    )


def load_profiles(
    generation_mode: GenerationMode = GenerationMode.BALANCED,
) -> dict[ModelSlot, ModelSpec]:
    """Merge code defaults with any slot-scoped env overrides for one mode."""

    base_profiles = _DEFAULT_PROFILES_BY_MODE[generation_mode]
    profiles = dict(base_profiles)
    for slot, spec in base_profiles.items():
        override = _env_override(slot, base=spec)
        if override is not None:
            profiles[slot] = override
    return profiles


def get_node_text_slot(node_name: str) -> ModelSlot:
    """Return the slot registered for an LLM-backed node."""

    if node_name not in NODE_MODEL_SLOTS:
        raise ValueError(
            f"Node '{node_name}' is not registered in NODE_MODEL_SLOTS. "
            f"Add it to pipeline.providers.registry."
        )
    return NODE_MODEL_SLOTS[node_name]


def _read_api_key(spec: ModelSpec) -> str | None:
    """Resolve the configured API key env var for a model spec, if any."""

    if spec.api_key_env is None:
        return None
    api_key = os.getenv(spec.api_key_env)
    if not api_key:
        raise ValueError(
            f"Model spec for '{spec.model_name}' expects env var "
            f"'{spec.api_key_env}', but it is not set."
        )
    return api_key


def _build_anthropic_model(spec: ModelSpec):
    """Build the Anthropic transport, optionally with explicit provider config."""

    api_key = _read_api_key(spec)
    if api_key is None and spec.base_url is None:
        return AnthropicModel(spec.model_name)

    from pydantic_ai.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key=api_key, base_url=spec.base_url)
    return AnthropicModel(spec.model_name, provider=provider)


def _build_google_model(spec: ModelSpec):
    """Build the Google transport, optionally with explicit provider config."""

    api_key = _read_api_key(spec)
    if api_key is None and spec.base_url is None:
        return GoogleModel(spec.model_name)

    from pydantic_ai.providers.google import GoogleProvider

    provider = GoogleProvider(api_key=api_key, base_url=spec.base_url)
    return GoogleModel(spec.model_name, provider=provider)


def _build_openai_compatible_model(spec: ModelSpec):
    """
    Build the OpenAI-compatible transport for hosted or self-hosted endpoints.

    The configured `base_url` tells PydanticAI which OpenAI-shaped API to talk
    to; the transport family stays the same whether the endpoint is OpenAI,
    Groq, Together, Ollama, or another compatible vendor.
    """

    from pydantic_ai.providers.openai import OpenAIProvider

    api_key = _read_api_key(spec)
    if spec.base_url is not None:
        # When routing to a custom compatible endpoint, default to a placeholder
        # unless a provider-specific key env was declared explicitly.
        provider = OpenAIProvider(
            base_url=spec.base_url,
            api_key=api_key or "api-key-not-set",
        )
    elif api_key is not None:
        provider = OpenAIProvider(api_key=api_key)
    else:
        provider = OpenAIProvider()

    return OpenAIChatModel(spec.model_name, provider=provider)


def _build_text_model(spec: ModelSpec):
    """Resolve a `ModelSpec` into the concrete PydanticAI model object."""

    if spec.family == ModelFamily.ANTHROPIC:
        return _build_anthropic_model(spec)
    if spec.family == ModelFamily.GOOGLE:
        return _build_google_model(spec)
    if spec.family == ModelFamily.OPENAI_COMPATIBLE:
        return _build_openai_compatible_model(spec)
    if spec.family == ModelFamily.TEST:
        return TestModel()
    raise NotImplementedError(
        f"Text family '{spec.family.value}' is not wired for pipeline use."
    )


def resolve_text_model(
    *,
    slot: ModelSlot,
    spec: ModelSpec,
    model_overrides: dict | None = None,
):
    """
    Resolve a PydanticAI-compatible text model for a slot.

    `model_overrides` is test-oriented and keyed by `ModelSlot` or slot string.
    """

    if model_overrides:
        if slot in model_overrides:
            return model_overrides[slot]
        if slot.value in model_overrides:
            return model_overrides[slot.value]

    return _build_text_model(spec)


def get_node_text_model(
    node_name: str,
    model_overrides: dict | None = None,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
):
    """Resolve the concrete PydanticAI model used by a given node."""

    slot = get_node_text_slot(node_name)
    spec = load_profiles(generation_mode)[slot]
    return resolve_text_model(
        slot=slot,
        spec=spec,
        model_overrides=model_overrides,
    )


def get_node_text_spec(
    node_name: str,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
) -> ModelSpec:
    """Return the merged `ModelSpec` for the slot assigned to a node."""

    slot = get_node_text_slot(node_name)
    return load_profiles(generation_mode)[slot]


def endpoint_host(base_url: str | None) -> str | None:
    """Extract the host portion of a configured endpoint for diagnostics/costs."""

    if not base_url:
        return None
    parsed = urlparse(base_url)
    return parsed.netloc or None


def describe_text_model(model: Any) -> ModelSpec | None:
    """
    Best-effort identity of the concrete PydanticAI model object for tracing/cost.

    Returns None if the model type is unknown; callers should fall back to the
    catalog/env-resolved spec.
    """

    cls = getattr(model, "__class__", type(model))
    module = getattr(cls, "__module__", "")
    name = getattr(cls, "__name__", "unknown")
    runtime_name = getattr(model, "model_name", None)
    runtime_system = getattr(model, "system", None)
    runtime_base_url = getattr(model, "base_url", None)
    base_url = str(runtime_base_url) if runtime_base_url is not None else None
    model_name = str(runtime_name) if runtime_name is not None else name

    if module.startswith("pydantic_ai.models.test") or isinstance(model, TestModel):
        return ModelSpec(
            family=ModelFamily.TEST,
            model_name=name,
        )

    if isinstance(model, AnthropicModel) or runtime_system == "anthropic":
        return ModelSpec(
            family=ModelFamily.ANTHROPIC,
            model_name=model_name,
            base_url=base_url,
        )

    if (
        isinstance(model, GoogleModel)
        or name == "GeminiModel"
        or runtime_system in {"google", "google-gla", "google-vertex"}
        or module.startswith("pydantic_ai.models.google")
        or module.startswith("pydantic_ai.models.gemini")
    ):
        return ModelSpec(
            family=ModelFamily.GOOGLE,
            model_name=model_name,
            base_url=base_url,
        )

    # PydanticAI uses several system names for OpenAI-shaped transports. This
    # mapping is intentionally best-effort so SSE/cost logic can stay generic.
    if (
        isinstance(model, OpenAIChatModel)
        or runtime_system in _OPENAI_COMPATIBLE_SYSTEMS
        or module.startswith("pydantic_ai.models.openai")
    ):
        return ModelSpec(
            family=ModelFamily.OPENAI_COMPATIBLE,
            model_name=model_name,
            base_url=base_url,
        )

    return None


def effective_text_spec(*, catalog_spec: ModelSpec, model: Any | None) -> ModelSpec:
    """
    Prefer the runtime model identity when it can be described reliably.

    Nodes pass the concrete `model` object to `run_llm` so tracing and cost use
    the same client that was handed to `Agent(...)`, including test doubles and
    env-selected OpenAI-compatible endpoints.
    """

    if model is None:
        return catalog_spec
    described = describe_text_model(model)
    return described if described is not None else catalog_spec
