from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent

from textbook_agent.application.dtos.brief import (
    BriefRequest,
    GenerationSpec,
)
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.value_objects import EducationLevel, GenerationMode
from pipeline.types.requests import GenerationMode as PipelineGenerationMode
from pipeline.types.requests import SectionPlan

logger = logging.getLogger(__name__)

_LIVE_PRESET_ID = "blue-classroom"
_DEFAULT_TEMPLATE_ID = "guided-concept-path"


@dataclass(frozen=True)
class TemplateSummary:
    id: str
    name: str
    intent: str
    learner_fit: list[str]


def _grade_band(profile: StudentProfile | None) -> str | None:
    if profile is None:
        return None

    mapping = {
        EducationLevel.ELEMENTARY: "primary",
        EducationLevel.MIDDLE_SCHOOL: "secondary",
        EducationLevel.HIGH_SCHOOL: "secondary",
        EducationLevel.UNDERGRADUATE: "advanced",
        EducationLevel.GRADUATE: "advanced",
        EducationLevel.PROFESSIONAL: "advanced",
    }
    return mapping[profile.education_level]


def _profile_context(profile: StudentProfile | None) -> str:
    if profile is None:
        return "No learner profile was available."

    interests = ", ".join(profile.interests) if profile.interests else "none listed"
    return "\n".join(
        [
            f"Grade band: {_grade_band(profile) or 'unknown'}",
            f"Age: {profile.age}",
            f"Learning style: {profile.learning_style.value}",
            f"Notation: {profile.preferred_notation.value}",
            f"Preferred depth: {profile.preferred_depth.value}",
            f"Interests: {interests}",
            f"Prior knowledge: {profile.prior_knowledge or 'not provided'}",
            f"Goals: {profile.goals or 'not provided'}",
            f"Learner description: {profile.learner_description or 'not provided'}",
        ]
    )


def _template_lines(templates: Sequence[TemplateSummary]) -> str:
    return "\n".join(
        f"- {template.id} | {template.name} | intent: {template.intent} | learnerFit: {', '.join(template.learner_fit) or 'n/a'}"
        for template in templates
    )


def _build_system_prompt(
    *,
    brief: BriefRequest,
    profile: StudentProfile | None,
    templates: Sequence[TemplateSummary],
) -> str:
    return "\n".join(
        [
            "You are the Teacher Studio brief interpreter.",
            f"Current live preset: {_LIVE_PRESET_ID}.",
            "Only choose from the provided live-safe template catalog.",
            "Short-form lessons only. Each section should cover one focused idea.",
            "If the topic would need more than 4 sections to cover adequately, it is too broad - flag this in warning and scope down to what fits in 3-4 sections.",
            "Return only valid JSON matching the schema. No preamble.",
            "Schema fields:",
            "- template_id",
            "- preset_id",
            "- mode",
            "- section_count",
            "- sections [{ section_id, position, title, focus, role, required_components, optional_components, interaction_policy, diagram_policy, enrichment_enabled, continuity_notes }]",
            "- warning",
            "- rationale",
            "- source_brief { intent, audience, extra_context }",
            "Brief:",
            f"- intent: {brief.intent}",
            f"- audience: {brief.audience}",
            f"- extra_context: {brief.extra_context or 'none'}",
            "Profile context:",
            _profile_context(profile),
            "Live-safe templates:",
            _template_lines(templates),
        ]
    )


def _build_user_prompt(brief: BriefRequest) -> str:
    return "\n".join(
        [
            "Plan the brief using the live-safe template catalog.",
            f"Intent: {brief.intent}",
            f"Audience: {brief.audience}",
            f"Extra context: {brief.extra_context or 'none'}",
            "Choose the best template, keep the lesson short-form, and draft 2-4 sections.",
        ]
    )


def _fallback_sections() -> list[SectionPlan]:
    return [
        SectionPlan(
            section_id="section-1",
            position=1,
            title="Core Idea",
            focus="Introduce the central concept in simple terms.",
            role="intro",
        ),
        SectionPlan(
            section_id="section-2",
            position=2,
            title="Worked Example",
            focus="Show the idea in action with one concrete example.",
            role="develop",
            needs_worked_example=True,
            required_components=["worked_example"],
        ),
        SectionPlan(
            section_id="section-3",
            position=3,
            title="Check Understanding",
            focus="Close with a short check that confirms the learner can explain it back.",
            role="practice",
            required_components=["practice", "what_next"],
        ),
    ]


def _fallback_spec(brief: BriefRequest) -> GenerationSpec:
    return GenerationSpec(
        template_id=_DEFAULT_TEMPLATE_ID,
        preset_id=_LIVE_PRESET_ID,
        mode=GenerationMode.BALANCED,
        section_count=3,
        sections=_fallback_sections(),
        warning="Topic is broad. Narrow it to one lesson-sized arc if you want a tighter plan.",
        rationale="guided-concept-path keeps the lesson focused and easy to review.",
        source_brief=brief,
    )


class BriefPlannerService:
    async def plan(
        self,
        brief: BriefRequest,
        *,
        profile: StudentProfile | None,
        templates: Sequence[TemplateSummary],
        model: Any,
        run_llm_fn: Callable[..., Awaitable[Any]],
        generation_id: str = "",
    ) -> GenerationSpec:
        if not templates:
            raise RuntimeError("No live-safe templates were available for the brief planner.")

        system_prompt = _build_system_prompt(brief=brief, profile=profile, templates=templates)
        user_prompt = _build_user_prompt(brief)
        fallback = _fallback_spec(brief)

        agent = Agent(
            model=model,
            output_type=GenerationSpec,
            system_prompt=system_prompt,
        )

        for attempt in range(2):
            try:
                result = await run_llm_fn(
                    generation_id=generation_id,
                    node="brief_planner",
                    agent=agent,
                    model=model,
                    user_prompt=user_prompt,
                    generation_mode=PipelineGenerationMode.DRAFT,
                )
                spec = result.output
                if spec is None:
                    raise ValueError("Missing GenerationSpec output.")
                return spec
            except Exception as exc:
                logger.warning("Brief planning attempt %s failed: %s", attempt + 1, exc)
                if attempt == 1:
                    return fallback

        return fallback
