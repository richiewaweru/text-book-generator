"""Integration tests that hit real LLM APIs.

These tests are excluded from the default test run. Run them with:
    uv run pytest -m integration

Requires one or both of:
    ANTHROPIC_API_KEY
    OPENAI_API_KEY
"""

import os

import pytest

from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.services.content_generator import (
    ContentGeneratorInput,
    ContentGeneratorNode,
)
from textbook_agent.domain.services.diagram_generator import (
    DiagramGeneratorInput,
    DiagramGeneratorNode,
)
from textbook_agent.domain.services.planner import CurriculumPlannerNode
from textbook_agent.infrastructure.providers.anthropic_provider import AnthropicProvider
from textbook_agent.infrastructure.providers.openai_provider import OpenAIProvider

pytestmark = pytest.mark.integration


def _build_provider(provider_name: str):
    if provider_name == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")
        model = os.environ.get("ANTHROPIC_SMOKE_MODEL", "claude-sonnet-4-20250514")
        return AnthropicProvider(api_key=api_key, model=model)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    model = os.environ.get("OPENAI_SMOKE_MODEL", "gpt-5-mini")
    return OpenAIProvider(api_key=api_key, model=model)


@pytest.fixture
def simple_profile():
    return GenerationContext(
        subject="introduction to fractions",
        age=12,
        context="I know how to add and subtract whole numbers but fractions confuse me.",
        depth="survey",
        language="plain",
    )


@pytest.mark.parametrize("provider_name", ["anthropic", "openai"])
class TestRealPipeline:
    async def test_planner_returns_valid_curriculum(self, provider_name, simple_profile):
        provider = _build_provider(provider_name)
        planner = CurriculumPlannerNode(provider=provider)
        plan = await planner.execute(simple_profile)

        assert plan.subject
        assert len(plan.sections) >= 2
        assert all(spec.id for spec in plan.sections)
        assert all(spec.title for spec in plan.sections)
        assert len(plan.reading_order) == len(plan.sections)

    async def test_content_generator_returns_rulebook_fields(
        self,
        provider_name,
        simple_profile,
    ):
        provider = _build_provider(provider_name)
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
        assert len(content.prerequisites_block) > 10
        assert len(content.interview_anchor) > 10
        assert len(content.think_prompt) > 10
        assert len(content.practice_problems) == 3
        assert {problem.difficulty for problem in content.practice_problems} == {
            "warm",
            "medium",
            "cold",
        }
        assert all(problem.statement for problem in content.practice_problems)
        assert all(problem.hint for problem in content.practice_problems)

    async def test_diagram_generator_returns_rulebook_svg(
        self,
        provider_name,
        simple_profile,
    ):
        provider = _build_provider(provider_name)
        planner = CurriculumPlannerNode(provider=provider)
        plan = await planner.execute(simple_profile)

        diagram_spec = next(
            (spec for spec in plan.sections if spec.needs_diagram),
            plan.sections[0],
        )
        content_gen = ContentGeneratorNode(provider=provider)
        content = await content_gen.execute(
            ContentGeneratorInput(section=diagram_spec, profile=simple_profile)
        )
        diagram_gen = DiagramGeneratorNode(provider=provider)
        diagram = await diagram_gen.execute(
            DiagramGeneratorInput(section=diagram_spec, content=content)
        )

        assert diagram.section_id == diagram_spec.id
        assert "<svg" in diagram.svg_markup
        assert "width=" in diagram.svg_markup
        assert "height=" in diagram.svg_markup
        assert "viewBox=" in diagram.svg_markup
        assert len(diagram.caption) > 10
