import pytest

from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan, SectionSpec
from textbook_agent.domain.entities.practice_problem import PracticeProblem
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.prompts.base_prompt import (
    BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
    BASE_PEDAGOGICAL_RULES,
    PROMPT_BUNDLE_VERSION,
)
from textbook_agent.domain.prompts.formatting_rules import FORMATTING_RULES
from textbook_agent.domain.prompts.planner_prompts import build_planner_prompt
from textbook_agent.domain.prompts.content_prompts import build_content_prompt
from textbook_agent.domain.prompts.diagram_prompts import build_diagram_prompt
from textbook_agent.domain.prompts.code_prompts import build_code_prompt
from textbook_agent.domain.prompts.quality_prompts import build_quality_prompt
from textbook_agent.domain.value_objects import SectionDepth


@pytest.fixture
def section_spec() -> SectionSpec:
    return SectionSpec(
        id="section_01",
        title="Introduction to Variables",
        learning_objective="Understand what a variable represents",
        estimated_depth=SectionDepth.LIGHT,
        needs_diagram=True,
        needs_code=True,
    )


@pytest.fixture
def section_content() -> SectionContent:
    return SectionContent(
        section_id="section_01",
        hook="Imagine a mystery box.",
        prerequisites_block="Remember that an equation balances two equal quantities.",
        plain_explanation="A variable is a name for a value.",
        formal_definition="A variable x represents an unknown.",
        worked_example="If x + 3 = 7, then x = 4.",
        common_misconception="Variables are not always x.",
        practice_problems=[
            PracticeProblem(
                difficulty="warm",
                statement="Solve y + 1 = 4.",
                hint="Undo the +1.",
            ),
            PracticeProblem(
                difficulty="medium",
                statement="Write an equation for a mystery number plus 5 equals 9.",
                hint="Start by naming the unknown.",
            ),
            PracticeProblem(
                difficulty="cold",
                statement="Explain why x = 2 and 2 = x mean the same thing.",
                hint="Read both equations aloud.",
            ),
        ],
        interview_anchor="How would you justify using a variable here in an interview?",
        think_prompt="Pause and predict what changes when the value changes.",
        connection_forward="Next: expressions.",
    )


def _minimal_plan() -> CurriculumPlan:
    return CurriculumPlan(
        subject="algebra",
        total_sections=1,
        sections=[
            SectionSpec(
                id="section_01",
                title="Variables",
                learning_objective="Learn variables",
                estimated_depth=SectionDepth.LIGHT,
            )
        ],
        reading_order=["section_01"],
    )


class TestBuildPlannerPrompt:
    def test_contains_shared_rulebook_bundle(self, beginner_profile):
        prompt = build_planner_prompt(beginner_profile)
        assert BASE_PEDAGOGICAL_RULES.strip() in prompt
        assert FORMATTING_RULES.strip() in prompt
        assert f"[PROMPT_BUNDLE_VERSION:{PROMPT_BUNDLE_VERSION}]" in prompt
        assert "[PROMPT_ID:curriculum_planner]" in prompt

    def test_contains_subject(self, beginner_profile):
        prompt = build_planner_prompt(beginner_profile)
        assert beginner_profile.subject in prompt

    def test_contains_schema_instruction(self, beginner_profile):
        prompt = build_planner_prompt(beginner_profile)
        assert "CurriculumPlan" in prompt
        assert "practice problems" in prompt

    def test_does_not_raise(self, beginner_profile):
        build_planner_prompt(beginner_profile)


class TestBuildContentPrompt:
    def test_contains_shared_rulebook_bundle(self, beginner_profile, section_spec):
        prompt = build_content_prompt(section_spec, beginner_profile)
        assert BASE_PEDAGOGICAL_AND_FORMATTING_RULES.strip() in prompt
        assert "[PROMPT_ID:content_generator]" in prompt

    def test_contains_section_title(self, beginner_profile, section_spec):
        prompt = build_content_prompt(section_spec, beginner_profile)
        assert section_spec.title in prompt

    def test_contains_schema_instruction(self, beginner_profile, section_spec):
        prompt = build_content_prompt(section_spec, beginner_profile)
        assert "SectionContent" in prompt
        assert "practice_problems" in prompt
        assert "warm, medium, and cold" in prompt

    def test_does_not_raise(self, beginner_profile, section_spec):
        build_content_prompt(section_spec, beginner_profile)


class TestBuildDiagramPrompt:
    def test_contains_shared_rulebook_bundle(self, section_spec, section_content):
        prompt = build_diagram_prompt(section_spec, section_content)
        assert BASE_PEDAGOGICAL_AND_FORMATTING_RULES.strip() in prompt
        assert "[PROMPT_ID:diagram_generator]" in prompt

    def test_contains_section_title(self, section_spec, section_content):
        prompt = build_diagram_prompt(section_spec, section_content)
        assert section_spec.title in prompt

    def test_contains_schema_instruction(self, section_spec, section_content):
        prompt = build_diagram_prompt(section_spec, section_content)
        assert "SectionDiagram" in prompt
        assert "viewBox" in prompt
        assert "IBM Plex Mono" in prompt

    def test_does_not_raise(self, section_spec, section_content):
        build_diagram_prompt(section_spec, section_content)


class TestBuildCodePrompt:
    def test_contains_shared_rulebook_bundle(self, section_spec, section_content):
        prompt = build_code_prompt(section_spec, section_content)
        assert BASE_PEDAGOGICAL_AND_FORMATTING_RULES.strip() in prompt
        assert "[PROMPT_ID:code_generator]" in prompt

    def test_contains_section_title(self, section_spec, section_content):
        prompt = build_code_prompt(section_spec, section_content)
        assert section_spec.title in prompt

    def test_contains_schema_instruction(self, section_spec, section_content):
        prompt = build_code_prompt(section_spec, section_content)
        assert "SectionCode" in prompt
        assert "80 characters or fewer" in prompt
        assert "commented-out code" in prompt

    def test_does_not_raise(self, section_spec, section_content):
        build_code_prompt(section_spec, section_content)


class TestBuildQualityPrompt:
    def test_contains_shared_rulebook_bundle(self, beginner_profile):
        plan = _minimal_plan()
        textbook = RawTextbook(
            subject="algebra",
            profile=beginner_profile,
            plan=plan,
            sections=[],
        )
        prompt = build_quality_prompt(textbook, plan)
        assert BASE_PEDAGOGICAL_AND_FORMATTING_RULES.strip() in prompt
        assert "[PROMPT_ID:quality_checker]" in prompt

    def test_contains_schema_instruction(self, beginner_profile):
        plan = _minimal_plan()
        textbook = RawTextbook(
            subject="algebra",
            profile=beginner_profile,
            plan=plan,
            sections=[],
        )
        prompt = build_quality_prompt(textbook, plan)
        assert "QualityReport" in prompt
        assert "structure completeness" in prompt
