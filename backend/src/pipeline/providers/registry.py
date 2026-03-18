"""
pipeline.providers.registry

Model tier assignment and provider injection.

Every node gets its model from this registry. To change which model
a node uses, change its tier here. Node code never mentions a model
name directly.

To inject a test model:
    from pydantic_ai.models.test import TestModel
    get_model(ModelTier.STANDARD, {ModelTier.STANDARD: TestModel()})
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os

from pipeline.providers.anthropic import build_anthropic_provider
from pipeline.providers.base import BaseLLMProvider
from pipeline.providers.gemini import build_gemini_provider
from pipeline.providers.openai import build_openai_provider


class ModelTier(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    CREATIVE = "creative"


@dataclass
class ProviderConfig:
    provider: str  # 'anthropic' | 'openai' | 'gemini'
    model_name: str


def _provider_from_name(name: str):
    if name == "anthropic":
        return build_anthropic_provider
    if name == "openai":
        return build_openai_provider
    if name == "gemini":
        return build_gemini_provider
    raise ValueError(f"Unknown provider '{name}'")


NODE_TIERS: dict[str, ModelTier] = {
    "curriculum_planner": ModelTier.FAST,
    "content_generator": ModelTier.STANDARD,
    "diagram_generator": ModelTier.FAST,
    "interaction_generator": ModelTier.CREATIVE,
    "qc_agent": ModelTier.FAST,
}

_DEFAULT_TIER_CONFIG: dict[ModelTier, ProviderConfig] = {
    ModelTier.FAST: ProviderConfig(
        provider="anthropic",
        model_name="claude-haiku-4-5-20251001",
    ),
    ModelTier.STANDARD: ProviderConfig(
        provider="anthropic",
        model_name="claude-sonnet-4-6",
    ),
    ModelTier.CREATIVE: ProviderConfig(
        provider="anthropic",
        model_name="claude-sonnet-4-6",
    ),
}


def _env_override(tier: ModelTier) -> ProviderConfig | None:
    prefix = f"LLM_TIER_{tier.name}"
    provider = os.getenv(f"{prefix}_PROVIDER")
    model_name = os.getenv(f"{prefix}_MODEL")
    if not provider and not model_name:
        return None
    base = _DEFAULT_TIER_CONFIG[tier]
    return ProviderConfig(
        provider=provider or base.provider,
        model_name=model_name or base.model_name,
    )


def _resolve_tier_config(tier: ModelTier) -> ProviderConfig:
    override = _env_override(tier)
    if override:
        return override
    return _DEFAULT_TIER_CONFIG[tier]


def get_model(tier: ModelTier, overrides: dict | None = None) -> BaseLLMProvider:
    if overrides and tier in overrides:
        return overrides[tier]
    cfg = _resolve_tier_config(tier)
    factory = _provider_from_name(cfg.provider)
    return factory(cfg.model_name)


def get_node_model(node_name: str, overrides: dict | None = None):
    if node_name not in NODE_TIERS:
        raise ValueError(
            f"Node '{node_name}' is not registered in NODE_TIERS. "
            f"Add it to pipeline.providers.registry."
        )
    return get_model(NODE_TIERS[node_name], overrides)
