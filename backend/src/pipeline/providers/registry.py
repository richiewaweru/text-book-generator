"""
pipeline.providers.registry

Central model routing for the pipeline.

Nodes never mention a concrete model name. They ask for a node-scoped model
and this registry resolves it using:
  - NODE_REQUIREMENTS (capability + coarse requirements)
  - a stable ModelRoute derived from those requirements
  - a route-scoped catalog entry (vendor + model name)
  - env overrides

Text/vision models resolve to PydanticAI model objects usable in `Agent(model=...)`.
Non-text capabilities (e.g. image generation) are intentionally not wired yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os

from pydantic_ai.models.anthropic import AnthropicModel

from pipeline.types.requests import GenerationMode


class Capability(str, Enum):
    TEXT = "text"
    VISION = "vision"
    IMAGE_GEN = "image_gen"
    EMBEDDINGS = "embeddings"


@dataclass
class NodeModelRequirements:
    capability: Capability
    quality_class: str = "standard"  # low | standard | high (coarse)
    latency_class: str = "standard"  # fast | standard | slow (coarse)
    cost_class: str = "standard"  # cheap | standard | premium (coarse)


class ModelRoute(str, Enum):
    """
    Stable routing keys used for env overrides and node mapping.

    These are intentionally coarse and human-friendly. They are not tied to a vendor.
    """

    TEXT_FAST = "text_fast"
    TEXT_STANDARD = "text_standard"
    TEXT_CREATIVE = "text_creative"


@dataclass(frozen=True)
class ModelSpec:
    capability: Capability
    provider: str  # 'anthropic' | 'openai' | 'gemini' | ...
    model_name: str
    # Coarse metadata used for humans + future policy; not relied on for correctness.
    quality_class: str = "standard"
    latency_class: str = "standard"
    cost_class: str = "standard"


NODE_REQUIREMENTS: dict[str, NodeModelRequirements] = {
    "curriculum_planner": NodeModelRequirements(
        capability=Capability.TEXT,
        quality_class="standard",
        latency_class="fast",
        cost_class="cheap",
    ),
    "content_generator": NodeModelRequirements(
        capability=Capability.TEXT,
        quality_class="high",
        latency_class="standard",
        cost_class="standard",
    ),
    "diagram_generator": NodeModelRequirements(
        capability=Capability.TEXT,
        quality_class="standard",
        latency_class="fast",
        cost_class="cheap",
    ),
    "interaction_generator": NodeModelRequirements(
        capability=Capability.TEXT,
        quality_class="standard",
        latency_class="standard",
        cost_class="standard",
    ),
    "qc_agent": NodeModelRequirements(
        capability=Capability.TEXT,
        quality_class="standard",
        latency_class="fast",
        cost_class="cheap",
    ),
}

_DEFAULT_ROUTE_CATALOG: dict[ModelRoute, ModelSpec] = {
    ModelRoute.TEXT_FAST: ModelSpec(
        capability=Capability.TEXT,
        provider="anthropic",
        model_name="claude-haiku-4-5-20251001",
        quality_class="standard",
        latency_class="fast",
        cost_class="cheap",
    ),
    ModelRoute.TEXT_STANDARD: ModelSpec(
        capability=Capability.TEXT,
        provider="anthropic",
        model_name="claude-sonnet-4-6",
        quality_class="high",
        latency_class="standard",
        cost_class="standard",
    ),
    ModelRoute.TEXT_CREATIVE: ModelSpec(
        capability=Capability.TEXT,
        provider="anthropic",
        model_name="claude-sonnet-4-6",
        quality_class="high",
        latency_class="standard",
        cost_class="standard",
    ),
}


def _env_override(route: ModelRoute) -> ModelSpec | None:
    """
    Env overrides are route-scoped so model control remains centralized.

    Preferred env vars:
      - MODEL_{ROUTE}_PROVIDER
      - MODEL_{ROUTE}_NAME
    """

    prefix = f"MODEL_{route.name}"
    provider = os.getenv(f"{prefix}_PROVIDER")
    model_name = os.getenv(f"{prefix}_NAME")

    if not provider and not model_name:
        return None

    base = _DEFAULT_ROUTE_CATALOG[route]
    return ModelSpec(
        capability=base.capability,
        provider=provider or base.provider,
        model_name=model_name or base.model_name,
        quality_class=base.quality_class,
        latency_class=base.latency_class,
        cost_class=base.cost_class,
    )


def _resolve_route_spec(route: ModelRoute) -> ModelSpec:
    override = _env_override(route)
    if override:
        return override
    return _DEFAULT_ROUTE_CATALOG[route]


def _requirements_to_route(req: NodeModelRequirements) -> ModelRoute:
    if req.capability != Capability.TEXT:
        raise ValueError(
            f"Capability '{req.capability}' is not wired yet in the pipeline registry."
        )

    # Keep routing stable and simple: prefer latency for FAST, otherwise choose
    # STANDARD vs CREATIVE by intent (quality/cost).
    if req.latency_class == "fast":
        return ModelRoute.TEXT_FAST
    if req.quality_class == "high":
        return ModelRoute.TEXT_STANDARD
    return ModelRoute.TEXT_STANDARD


def _build_text_model(spec: ModelSpec):
    if spec.provider == "anthropic":
        return AnthropicModel(spec.model_name)
    raise NotImplementedError(
        f"Text provider '{spec.provider}' is not wired for PydanticAI yet."
    )


def resolve_text_model(
    *,
    route: ModelRoute,
    overrides: dict | None = None,
):
    """
    Resolve a PydanticAI-compatible model object for text/vision use.

    `overrides` is intended for tests; keys can be ModelRoute or route string.
    """

    if overrides:
        if route in overrides:
            return overrides[route]
        if route.value in overrides:
            return overrides[route.value]

    spec = _resolve_route_spec(route)
    if spec.capability != Capability.TEXT:
        raise ValueError(f"Route '{route.value}' is not a text route.")
    return _build_text_model(spec)


def requirements_for_node(node_name: str, generation_mode: GenerationMode) -> NodeModelRequirements:
    if node_name not in NODE_REQUIREMENTS:
        raise ValueError(
            f"Node '{node_name}' is not registered in NODE_REQUIREMENTS. "
            f"Add it to pipeline.providers.registry."
        )

    req = NODE_REQUIREMENTS[node_name]

    # Mode-based policy adjustments (kept equivalent in spirit to old tier rules)
    if generation_mode == GenerationMode.DRAFT and node_name == "content_generator":
        return NodeModelRequirements(
            capability=req.capability,
            quality_class="standard",
            latency_class="fast",
            cost_class="cheap",
        )

    if generation_mode == GenerationMode.STRICT and req.latency_class == "fast":
        return NodeModelRequirements(
            capability=req.capability,
            quality_class="high",
            latency_class="standard",
            cost_class=req.cost_class,
        )

    return req


def get_node_text_model(
    node_name: str,
    overrides: dict | None = None,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
):
    req = requirements_for_node(node_name, generation_mode)
    route = _requirements_to_route(req)
    return resolve_text_model(route=route, overrides=overrides)


def get_node_text_route(
    node_name: str,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
) -> ModelRoute:
    req = requirements_for_node(node_name, generation_mode)
    return _requirements_to_route(req)


def get_node_text_spec(
    node_name: str,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
) -> ModelSpec:
    """
    Resolve the current model spec (provider + model_name + metadata) for tracing/cost.

    Note: `provider_overrides` affects the returned model object, but this spec is
    computed from the route catalog + env overrides (intended for production).
    """

    route = get_node_text_route(node_name, generation_mode)
    return _resolve_route_spec(route)
