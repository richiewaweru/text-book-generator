from __future__ import annotations

import os
from contextlib import contextmanager

from pipeline.providers.registry import (
    ModelRoute,
    _DEFAULT_ROUTE_CATALOG,
    _resolve_route_spec,
    get_node_text_model,
)
from pydantic_ai.models.test import TestModel


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


def test_default_route_spec_used_when_no_env_override():
    spec = _resolve_route_spec(ModelRoute.TEXT_FAST)
    assert spec.provider == _DEFAULT_ROUTE_CATALOG[ModelRoute.TEXT_FAST].provider
    assert spec.model_name == _DEFAULT_ROUTE_CATALOG[ModelRoute.TEXT_FAST].model_name


def test_env_override_can_change_provider_and_model():
    prefix = "MODEL_TEXT_FAST"
    with _env(
        **{
            f"{prefix}_PROVIDER": "openai",
            f"{prefix}_NAME": "gpt-5.1-mini",
        }
    ):
        spec = _resolve_route_spec(ModelRoute.TEXT_FAST)
        assert spec.provider == "openai"
        assert spec.model_name == "gpt-5.1-mini"


def test_get_node_text_model_returns_pydanticai_model():
    # Avoid requiring real API keys: inject a deterministic TestModel.
    model = get_node_text_model("qc_agent", {ModelRoute.TEXT_FAST: TestModel()})
    assert model is not None

