"""Tests for pipeline.llm_runner retry policy, effective model spec, and event bus guards."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.exceptions import ModelHTTPError, UserError
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from pipeline.events import (
    LLMCallFailedEvent,
    LLMCallStartedEvent,
    LLMCallSucceededEvent,
)
from pipeline.llm_runner import RetryPolicy, run_llm
from pipeline.providers.registry import ModelFamily, describe_text_model
from pipeline.types.requests import GenerationMode


def test_describe_text_model_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    model = AnthropicModel("custom-haiku-override")
    spec = describe_text_model(model)
    assert spec is not None
    assert spec.family == ModelFamily.ANTHROPIC
    assert spec.model_name == "custom-haiku-override"


def test_describe_text_model_test_model() -> None:
    spec = describe_text_model(TestModel())
    assert spec is not None
    assert spec.family == ModelFamily.TEST
    assert spec.model_name == "TestModel"


def test_describe_text_model_google() -> None:
    model = GoogleModel("gemini-2.5-flash", provider=GoogleProvider(api_key="sk-test"))
    spec = describe_text_model(model)
    assert spec is not None
    assert spec.family == ModelFamily.GOOGLE
    assert spec.model_name == "gemini-2.5-flash"


def test_describe_text_model_openai_compatible() -> None:
    model = OpenAIChatModel(
        "llama3-8b-8192",
        provider=OpenAIProvider(
            base_url="https://api.groq.com/openai/v1",
            api_key="sk-test",
        ),
    )
    spec = describe_text_model(model)
    assert spec is not None
    assert spec.family == ModelFamily.OPENAI_COMPATIBLE
    assert spec.model_name == "llama3-8b-8192"
    assert spec.base_url is not None
    assert spec.base_url.startswith("https://api.groq.com/openai/v1")


async def test_retry_transient_model_http_error_then_success() -> None:
    published: list[tuple[str, object]] = []

    def capture(generation_id: str, event: object) -> None:
        published.append((generation_id, event))

    ok = SimpleNamespace(usage=SimpleNamespace(input_tokens=10, output_tokens=20))
    agent = MagicMock()
    agent.run = AsyncMock(
        side_effect=[
            ModelHTTPError(429, "m", None),
            ok,
        ],
    )

    with patch("pipeline.llm_runner.event_bus") as bus:
        bus.publish = MagicMock(side_effect=capture)
        result = await run_llm(
            generation_id="gen-retry",
            node="curriculum_planner",
            agent=agent,
            user_prompt="hi",
            retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
            generation_mode=GenerationMode.BALANCED,
        )

    assert result is ok
    assert agent.run.call_count == 2

    failed = [event for _, event in published if isinstance(event, LLMCallFailedEvent)]
    assert len(failed) == 1
    assert failed[0].retryable is True
    succeeded = [event for _, event in published if isinstance(event, LLMCallSucceededEvent)]
    assert len(succeeded) == 1


async def test_no_retry_on_user_error() -> None:
    published: list[tuple[str, object]] = []

    def capture(generation_id: str, event: object) -> None:
        published.append((generation_id, event))

    agent = MagicMock()
    agent.run = AsyncMock(side_effect=UserError("bad prompt"))

    with patch("pipeline.llm_runner.event_bus") as bus:
        bus.publish = MagicMock(side_effect=capture)
        with pytest.raises(UserError):
            await run_llm(
                generation_id="gen-ue",
                node="curriculum_planner",
                agent=agent,
                user_prompt="hi",
                retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
                generation_mode=GenerationMode.BALANCED,
            )

    assert agent.run.call_count == 1
    failed = [event for _, event in published if isinstance(event, LLMCallFailedEvent)]
    assert len(failed) == 1
    assert failed[0].retryable is False


async def test_no_retry_on_non_transient_http_error() -> None:
    agent = MagicMock()
    agent.run = AsyncMock(side_effect=ModelHTTPError(401, "m", None))

    with patch("pipeline.llm_runner.event_bus.publish"):
        with pytest.raises(ModelHTTPError):
            await run_llm(
                generation_id="gen-401",
                node="curriculum_planner",
                agent=agent,
                user_prompt="hi",
                retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
                generation_mode=GenerationMode.BALANCED,
            )

    assert agent.run.call_count == 1


async def test_effective_spec_uses_test_model_in_events_and_zero_cost() -> None:
    published: list[object] = []

    def capture(_generation_id: str, event: object) -> None:
        published.append(event)

    model = TestModel()
    ok = SimpleNamespace(usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=1_000_000))
    agent = MagicMock()
    agent.run = AsyncMock(return_value=ok)

    with patch("pipeline.llm_runner.event_bus") as bus:
        bus.publish = MagicMock(side_effect=capture)
        await run_llm(
            generation_id="gen-test",
            node="curriculum_planner",
            agent=agent,
            model=model,
            user_prompt="hi",
            generation_mode=GenerationMode.BALANCED,
        )

    started = [event for event in published if isinstance(event, LLMCallStartedEvent)]
    assert started
    assert started[0].slot == "fast"
    assert started[0].family == "test"
    assert started[0].model_name == "TestModel"

    succeeded = [event for event in published if isinstance(event, LLMCallSucceededEvent)]
    assert succeeded
    assert succeeded[0].slot == "fast"
    assert succeeded[0].family == "test"
    assert succeeded[0].model_name == "TestModel"
    assert succeeded[0].cost_usd == 0.0


async def test_unknown_openai_compatible_pricing_emits_none_and_endpoint_host() -> None:
    published: list[object] = []

    def capture(_generation_id: str, event: object) -> None:
        published.append(event)

    model = OpenAIChatModel(
        "llama3-8b-8192",
        provider=OpenAIProvider(
            base_url="https://api.groq.com/openai/v1",
            api_key="sk-test",
        ),
    )
    ok = SimpleNamespace(usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=1_000_000))
    agent = MagicMock()
    agent.run = AsyncMock(return_value=ok)

    with patch("pipeline.llm_runner.event_bus") as bus:
        bus.publish = MagicMock(side_effect=capture)
        await run_llm(
            generation_id="gen-groq",
            node="curriculum_planner",
            agent=agent,
            model=model,
            user_prompt="hi",
            generation_mode=GenerationMode.BALANCED,
        )

    succeeded = [event for event in published if isinstance(event, LLMCallSucceededEvent)]
    assert succeeded
    assert succeeded[0].slot == "fast"
    assert succeeded[0].family == "openai_compatible"
    assert succeeded[0].model_name == "llama3-8b-8192"
    assert succeeded[0].endpoint_host == "api.groq.com"
    assert succeeded[0].cost_usd is None


async def test_skips_event_bus_when_generation_id_blank() -> None:
    agent = MagicMock()
    agent.run = AsyncMock(
        return_value=SimpleNamespace(usage=SimpleNamespace(input_tokens=1, output_tokens=2)),
    )

    with patch("pipeline.llm_runner.event_bus.publish") as publish:
        await run_llm(
            generation_id="",
            node="curriculum_planner",
            agent=agent,
            user_prompt="hi",
            generation_mode=GenerationMode.BALANCED,
        )
        publish.assert_not_called()

    with patch("pipeline.llm_runner.event_bus.publish") as publish:
        await run_llm(
            generation_id="   ",
            node="curriculum_planner",
            agent=agent,
            user_prompt="hi",
            generation_mode=GenerationMode.BALANCED,
        )
        publish.assert_not_called()
