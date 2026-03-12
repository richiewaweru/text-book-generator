"""Integration tests that hit a real LLM API.

These tests are excluded from the default test run. Run them with:
    uv run pytest -m integration

Requires ANTHROPIC_API_KEY to be set in the environment.
"""

import os

import pytest

from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.services.planner import CurriculumPlannerNode
from textbook_agent.domain.services.content_generator import (
    ContentGeneratorNode,
    ContentGeneratorInput,
)
from textbook_agent.infrastructure.providers.anthropic_provider import AnthropicProvider

pytestmark = pytest.mark.integration

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SKIP_REASON = "ANTHROPIC_API_KEY not set"


@pytest.fixture
def provider():
    if not API_KEY:
        pytest.skip(SKIP_REASON)
    return AnthropicProvider(api_key=API_KEY, model="claude-haiku-4-5-20251001")


@pytest.fixture
def simple_profile():
    return GenerationContext(
        subject="introduction to fractions",
        age=12,
        context="I know how to add and subtract whole numbers but fractions confuse me.",
        depth="survey",
        language="plain",
    )


class TestRealPipeline:
    async def test_planner_returns_valid_curriculum(self, provider, simple_profile):
        planner = CurriculumPlannerNode(provider=provider)
        plan = await planner.execute(simple_profile)

        assert plan.subject
        assert len(plan.sections) >= 2
        assert all(spec.id for spec in plan.sections)
        assert all(spec.title for spec in plan.sections)
        assert len(plan.reading_order) == len(plan.sections)

    async def test_content_generator_returns_valid_section(
        self, provider, simple_profile
    ):
        planner = CurriculumPlannerNode(provider=provider)
        plan = await planner.execute(simple_profile)

        first_spec = plan.sections[0]
        content_gen = ContentGeneratorNode(provider=provider)
        content = await content_gen.execute(
            ContentGeneratorInput(section=first_spec, profile=simple_profile)
        )

        assert content.section_id == first_spec.id
        assert len(content.hook) > 10
        assert len(content.plain_explanation) > 10
        assert len(content.formal_definition) > 10
        assert len(content.worked_example) > 10
