from __future__ import annotations

import os
from contextlib import contextmanager

from pydantic_ai.models.test import TestModel

from pipeline.media.providers.registry import get_image_client, load_image_provider_spec
from pipeline.providers.registry import (
    ModelFamily,
    ModelSlot,
    describe_text_model,
    get_node_text_model,
    get_node_text_spec,
    get_node_text_slot,
    load_profiles,
)
from pipeline.types.requests import GenerationMode


@contextmanager
def _env(**kwargs: str | None):
    old = {k: os.environ.get(k) for k in kwargs}
    try:
        for key, value in kwargs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_load_profiles_uses_default_profiles():
    profiles = load_profiles()

    assert set(profiles) == {ModelSlot.FAST, ModelSlot.STANDARD}
    assert profiles[ModelSlot.FAST].family == ModelFamily.ANTHROPIC
    assert profiles[ModelSlot.FAST].model_name == "claude-haiku-4-5-20251001"
    assert profiles[ModelSlot.STANDARD].model_name == "claude-sonnet-4-6"


def test_load_profiles_varies_defaults_by_generation_mode():
    draft_profiles = load_profiles(GenerationMode.DRAFT)
    strict_profiles = load_profiles(GenerationMode.STRICT)

    assert draft_profiles[ModelSlot.FAST].model_name == "claude-haiku-4-5-20251001"
    assert draft_profiles[ModelSlot.STANDARD].model_name == "claude-haiku-4-5-20251001"
    assert strict_profiles[ModelSlot.FAST].model_name == "claude-sonnet-4-6"
    assert strict_profiles[ModelSlot.STANDARD].model_name == "claude-sonnet-4-6"


def test_slot_env_override_wins_over_code_defaults():
    with _env(
        PIPELINE_FAST_PROVIDER="openai_compatible",
        PIPELINE_FAST_MODEL_NAME="llama3-8b-8192",
        PIPELINE_FAST_BASE_URL="https://api.groq.com/openai/v1",
        PIPELINE_FAST_API_KEY_ENV="GROQ_API_KEY",
        GROQ_API_KEY="sk-test",
    ):
        spec = load_profiles()[ModelSlot.FAST]

    assert spec.family == ModelFamily.OPENAI_COMPATIBLE
    assert spec.model_name == "llama3-8b-8192"
    assert spec.base_url == "https://api.groq.com/openai/v1"
    assert spec.api_key_env == "GROQ_API_KEY"


def test_legacy_model_text_env_vars_no_longer_affect_profiles():
    with _env(
        MODEL_TEXT_FAST_PROVIDER="openai_compatible",
        MODEL_TEXT_FAST_NAME="llama3-8b-8192",
    ):
        spec = load_profiles()[ModelSlot.FAST]

    assert spec.family == ModelFamily.ANTHROPIC
    assert spec.model_name == "claude-haiku-4-5-20251001"


def test_pipeline_name_alias_no_longer_affects_profiles():
    with _env(
        PIPELINE_FAST_NAME="llama3-8b-8192",
    ):
        spec = load_profiles()[ModelSlot.FAST]

    assert spec.family == ModelFamily.ANTHROPIC
    assert spec.model_name == "claude-haiku-4-5-20251001"


def test_get_node_text_slot_maps_llm_nodes():
    assert get_node_text_slot("curriculum_planner") == ModelSlot.FAST
    assert get_node_text_slot("content_generator") == ModelSlot.STANDARD
    assert get_node_text_slot("diagram_generator") == ModelSlot.FAST
    assert get_node_text_slot("qc_agent") == ModelSlot.FAST


def test_get_node_text_model_returns_slot_override_for_tests():
    model = get_node_text_model(
        "qc_agent",
        model_overrides={ModelSlot.FAST: TestModel()},
    )
    assert isinstance(model, TestModel)


def test_get_node_text_model_respects_generation_mode_defaults():
    draft_spec = get_node_text_spec(
        "content_generator",
        generation_mode=GenerationMode.DRAFT,
    )
    strict_spec = get_node_text_spec(
        "content_generator",
        generation_mode=GenerationMode.STRICT,
    )

    assert draft_spec.model_name == "claude-haiku-4-5-20251001"
    assert strict_spec.model_name == "claude-sonnet-4-6"


def test_openai_compatible_resolves_without_new_family_code():
    with _env(
        PIPELINE_FAST_PROVIDER="openai_compatible",
        PIPELINE_FAST_MODEL_NAME="llama3-8b-8192",
        PIPELINE_FAST_BASE_URL="https://api.groq.com/openai/v1",
        PIPELINE_FAST_API_KEY_ENV="GROQ_API_KEY",
        GROQ_API_KEY="sk-test",
    ):
        model = get_node_text_model("curriculum_planner")

    spec = describe_text_model(model)
    assert model.__class__.__name__ == "OpenAIChatModel"
    assert spec is not None
    assert spec.family == ModelFamily.OPENAI_COMPATIBLE
    assert spec.model_name == "llama3-8b-8192"
    assert spec.base_url is not None
    assert spec.base_url.startswith("https://api.groq.com/openai/v1")


def test_google_family_uses_google_model():
    with _env(
        PIPELINE_STANDARD_PROVIDER="google",
        PIPELINE_STANDARD_MODEL_NAME="gemini-2.5-flash",
        GOOGLE_API_KEY="sk-test",
    ):
        model = get_node_text_model("content_generator")

    spec = describe_text_model(model)
    assert model.__class__.__name__ == "GoogleModel"
    assert spec is not None
    assert spec.family == ModelFamily.GOOGLE
    assert spec.model_name == "gemini-2.5-flash"


def test_image_provider_defaults_to_gemini():
    with _env(
        PIPELINE_IMAGE_PROVIDER=None,
        PIPELINE_IMAGE_MODEL_NAME=None,
        PIPELINE_IMAGE_BASE_URL=None,
        PIPELINE_IMAGE_API_KEY_ENV=None,
    ):
        spec = load_image_provider_spec()

    assert spec.provider == "gemini"


def test_image_provider_selects_openai():
    with _env(
        PIPELINE_IMAGE_PROVIDER="openai",
        PIPELINE_IMAGE_MODEL_NAME="gpt-image-1",
        OPENAI_API_KEY="sk-test",
    ):
        client = get_image_client()

    assert client.__class__.__name__ == "OpenAIImageClient"


def test_image_provider_selects_xai_with_explicit_base_url():
    with _env(
        PIPELINE_IMAGE_PROVIDER="xai",
        PIPELINE_IMAGE_MODEL_NAME="grok-image",
        PIPELINE_IMAGE_BASE_URL="https://api.x.ai/v1",
        PIPELINE_IMAGE_API_KEY_ENV="XAI_API_KEY",
        XAI_API_KEY="sk-test",
    ):
        spec = load_image_provider_spec()
        client = get_image_client()

    assert spec.provider == "xai"
    assert spec.base_url == "https://api.x.ai/v1"
    assert client.__class__.__name__ == "XAIImageClient"


def test_xai_requires_explicit_base_url():
    with _env(
        PIPELINE_IMAGE_PROVIDER="xai",
        PIPELINE_IMAGE_BASE_URL=None,
        PIPELINE_IMAGE_API_KEY_ENV="XAI_API_KEY",
        XAI_API_KEY="sk-test",
    ):
        try:
            load_image_provider_spec()
        except RuntimeError as exc:
            assert "PIPELINE_IMAGE_BASE_URL is required" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError for missing xAI base URL")
