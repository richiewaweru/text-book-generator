from __future__ import annotations

import os
from contextlib import contextmanager

from pipeline.providers.registry import (
    ModelTier,
    _DEFAULT_TIER_CONFIG,
    _resolve_tier_config,
    get_model,
)


@contextmanager
def _env(**kwargs: str):
    old = {k: os.environ.get(k) for k in kwargs}
    try:
        os.environ.update({k: v for k, v in kwargs.items() if v is not None})
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_default_tier_config_used_when_no_env_override():
    cfg = _resolve_tier_config(ModelTier.FAST)
    assert cfg.provider == _DEFAULT_TIER_CONFIG[ModelTier.FAST].provider
    assert cfg.model_name == _DEFAULT_TIER_CONFIG[ModelTier.FAST].model_name


def test_env_override_can_change_provider_and_model():
    prefix = "LLM_TIER_FAST"
    with _env(
        **{
            f"{prefix}_PROVIDER": "openai",
            f"{prefix}_MODEL": "gpt-5.1-mini",
        }
    ):
        cfg = _resolve_tier_config(ModelTier.FAST)
        assert cfg.provider == "openai"
        assert cfg.model_name == "gpt-5.1-mini"


def test_get_model_returns_provider_instance():
    provider = get_model(ModelTier.STANDARD)
    # we can't assert exact type without tying tests to Anthropic implementation,
    # but we can at least ensure the object has the expected interface.
    assert hasattr(provider, "generate")

