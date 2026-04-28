from __future__ import annotations

import json
import logging
import sys
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic_ai import Agent

from core.auth.middleware import get_current_user
from core.dependencies import get_student_profile_repository
from core.entities.student_profile import StudentProfile
from core.entities.user import User
from core.events import TraceClosedEvent, TraceRegisteredEvent
from core.llm import build_model, run_llm
from core.ports.student_profile_repository import StudentProfileRepository
from core.rate_limit import limiter
from generation.dependencies import (
    get_document_repository,
    get_generation_engine,
    get_generation_repository,
    get_report_repository,
)
from generation.dtos import GenerationAcceptedResponse
from generation.ports.document_repository import DocumentRepository
from generation.ports.generation_report_repository import GenerationReportRepository
from generation.ports.generation_repository import GenerationRepository
from generation.service import enqueue_generation
from pipeline.contracts import validate_preset_for_template as _legacy_validate_preset_for_template
from pipeline.resources import get_resource_template, validate_brief
from pipeline.types.requests import (
    GenerationMode,
    SectionPlan,
    SectionVisualPolicy,
    count_visual_placements,
    needs_diagram_from_placements,
)
from pipeline.types.teacher_brief import (
    BriefReviewRequest,
    BriefReviewResult,
    BriefReviewWarning,
    BriefValidationRequest,
    BriefValidationResult,
    ClassProfile,
    GRADE_BAND_BY_LEVEL,
    TeacherBrief,
    TopicResolutionRequest,
    TopicResolutionResult,
)
from planning import PlanningService
from planning.llm_config import (
    PLANNING_BRIEF_REVIEW_CALLER,
    PLANNING_SECTION_COMPOSER_CALLER,
    PLANNING_TOPIC_RESOLUTION_CALLER,
    get_planning_slot,
    get_planning_spec,
)
from planning.models import PlanningGenerationSpec, PlanningSectionPlan

import core.events as core_events

router = APIRouter(prefix="/api/v1", tags=["brief"])
logger = logging.getLogger(__name__)


def diag(tag: str, **fields) -> None:
    sys.stderr.write(f"DIAG::{tag}::{json.dumps(fields, default=str)}\n")
    sys.stderr.flush()


def _topic_resolution_system_prompt() -> str:
    return "\n".join(
        [
            "You turn a teacher's raw topic into a tighter planning brief.",
            "Return valid JSON only.",
            "Infer a broad school subject, normalize the main topic, and propose 4 to 8 candidate subtopics.",
            "Keep subtopic titles teacher-facing, short, and commonly taught.",
            "Always calibrate the topic breakdown to the selected grade level and grade band.",
            "When a specific grade is selected, avoid broad grade-range framing in the suggestions.",
            "Use likely_grade_band as a short teacher-facing fit label such as 'Grade 10 fit', 'Good review', 'Challenge option', or 'Prerequisite review'.",
            "Only use broad grade ranges when grade_level is mixed.",
            "Do not suggest material that is clearly too advanced or too basic unless you frame it as review, prerequisite, or challenge.",
            "Prefer age-appropriate subtopics when learner context or class profile is present.",
            "Set needs_clarification=true only when the topic is too vague to narrow responsibly.",
            "Do not invent niche or overly advanced subtopics when common classroom targets fit.",
        ]
    )


def _topic_resolution_user_prompt(payload: TopicResolutionRequest) -> str:
    class_profile = payload.class_profile
    class_profile_summary = (
        "none"
        if class_profile is None
        else (
            f"reading={class_profile.reading_level}, "
            f"language={class_profile.language_support}, "
            f"confidence={class_profile.confidence}, "
            f"prior_knowledge={class_profile.prior_knowledge}, "
            f"pacing={class_profile.pacing}, "
            f"preferences={', '.join(class_profile.learning_preferences) or 'none'}"
        )
    )
    return "\n".join(
        [
            f"Raw topic: {payload.raw_topic}",
            f"Grade level: {payload.grade_level}",
            f"Grade band: {payload.grade_band}",
            f"Learner context: {payload.learner_context or 'none'}",
            f"Class profile: {class_profile_summary}",
            (
                "Grade guidance: "
                "If grade_level is mixed, broad ranges are acceptable. "
                "Otherwise, keep the breakdown anchored to the exact selected grade."
            ),
            "Return:",
            "- subject",
            "- topic",
            "- candidate_subtopics: 4 to 8 items with id, title, description, likely_grade_band",
            "- needs_clarification",
            "- clarification_message when needed",
        ]
    )


def _brief_review_system_prompt() -> str:
    return "\n".join(
        [
            "You review a structured teacher brief for pedagogical coherence.",
            "Return valid JSON only.",
            "Warnings are advisory, never blocking.",
            "Look for tensions between subtopic count, depth, supports, resource type, intended outcome, and teacher notes.",
            "Keep warnings concise and practical.",
        ]
    )


def _brief_review_user_prompt(brief: TeacherBrief) -> str:
    return "\n".join(
        [
            f"Subject: {brief.subject}",
            f"Topic: {brief.topic}",
            f"Subtopics: {', '.join(brief.subtopics)}",
            f"Grade level: {brief.grade_level}",
            f"Grade band: {brief.grade_band}",
            (
                "Class profile: "
                f"reading={brief.class_profile.reading_level}, "
                f"language={brief.class_profile.language_support}, "
                f"confidence={brief.class_profile.confidence}, "
                f"prior_knowledge={brief.class_profile.prior_knowledge}, "
                f"pacing={brief.class_profile.pacing}, "
                f"preferences={', '.join(brief.class_profile.learning_preferences) or 'none'}"
            ),
            f"Learner context: {brief.learner_context}",
            f"Intended outcome: {brief.intended_outcome}",
            f"Resource type: {brief.resource_type}",
            f"Supports: {', '.join(brief.supports) if brief.supports else 'none'}",
            f"Depth: {brief.depth}",
            f"Teacher notes: {brief.teacher_notes or 'none'}",
            "Return:",
            "- coherent: boolean",
            "- warnings: [{ message, suggestion }]",
        ]
    )


async def _resolve_topic_with_llm(payload: TopicResolutionRequest) -> TopicResolutionResult:
    trace_id = uuid.uuid4().hex
    spec = get_planning_spec(PLANNING_TOPIC_RESOLUTION_CALLER)
    slot = get_planning_slot(PLANNING_TOPIC_RESOLUTION_CALLER)
    model = build_model(spec)
    agent = Agent(
        model=model,
        output_type=TopicResolutionResult,
        system_prompt=_topic_resolution_system_prompt(),
    )
    result = await run_llm(
        caller=PLANNING_TOPIC_RESOLUTION_CALLER,
        trace_id=trace_id,
        generation_id=trace_id,
        agent=agent,
        model=model,
        user_prompt=_topic_resolution_user_prompt(payload),
        slot=slot,
        spec=spec,
    )
    output = result.output
    if output is None:
        raise RuntimeError("Topic resolution returned no structured output.")
    return output


async def _review_brief_with_llm(brief: TeacherBrief) -> BriefReviewResult:
    trace_id = uuid.uuid4().hex
    spec = get_planning_spec(PLANNING_BRIEF_REVIEW_CALLER)
    slot = get_planning_slot(PLANNING_BRIEF_REVIEW_CALLER)
    model = build_model(spec)
    agent = Agent(
        model=model,
        output_type=BriefReviewResult,
        system_prompt=_brief_review_system_prompt(),
    )
    result = await run_llm(
        caller=PLANNING_BRIEF_REVIEW_CALLER,
        trace_id=trace_id,
        generation_id=trace_id,
        agent=agent,
        model=model,
        user_prompt=_brief_review_user_prompt(brief),
        slot=slot,
        spec=spec,
    )
    output = result.output
    if output is None:
        raise RuntimeError("Brief review returned no structured output.")
    return output


async def _load_profile(
    user: User,
    profile_repo: StudentProfileRepository,
) -> StudentProfile | None:
    return await profile_repo.find_by_user_id(user.id)


def _pipeline_section_from_planning(
    section: PlanningSectionPlan,
    *,
    generation_mode: GenerationMode,
) -> SectionPlan:
    selected = list(dict.fromkeys(section.selected_components))
    needs_diagram = needs_diagram_from_placements(section)
    needs_worked_example = any(component == "worked-example-card" for component in selected)
    interaction_required = any(component == "simulation-block" for component in selected)
    focus = section.focus_note or section.objective or section.rationale or section.title
    computed_diagram_policy = "required" if needs_diagram else "allowed"
    pipeline_visual_policy = (
        SectionVisualPolicy(
            required=section.visual_policy.required,
            intent=section.visual_policy.intent,
            mode=section.visual_policy.mode,
            goal=section.visual_policy.goal,
            style_notes=section.visual_policy.style_notes,
        )
        if section.visual_policy is not None
        else None
    )
    if not focus:
        focus = f"Section {section.order}"
    diag(
        "PIPELINE_SECTION_FROM_PLANNING",
        source="planning_routes",
        section_id=section.id,
        title=section.title,
        selected_components=selected,
        planning_visual_policy=section.visual_policy.model_dump() if section.visual_policy else None,
        visual_placements_count=count_visual_placements(section),
        computed_needs_diagram=needs_diagram,
        computed_diagram_policy=computed_diagram_policy,
        pipeline_visual_policy=pipeline_visual_policy.model_dump() if pipeline_visual_policy else None,
    )
    return SectionPlan(
        section_id=section.id,
        title=section.title,
        position=section.order,
        focus=focus,
        role=section.role,
        bridges_from=None,
        bridges_to=None,
        needs_diagram=needs_diagram,
        needs_worked_example=needs_worked_example,
        required_components=selected,
        optional_components=[],
        interaction_policy=(
            "disabled"
            if generation_mode == GenerationMode.DRAFT
            else "required" if interaction_required else "allowed"
        ),
        diagram_policy=computed_diagram_policy,
        visual_policy=pipeline_visual_policy,
        continuity_notes=section.rationale,
        terms_to_define=list(section.terms_to_define),
        terms_assumed=list(section.terms_assumed),
        practice_target=section.practice_target,
        visual_placements=list(section.visual_placements),
    )


def _pipeline_sections_from_planning_spec(spec: PlanningGenerationSpec) -> list[SectionPlan]:
    sections = [
        _pipeline_section_from_planning(
            section,
            generation_mode=spec.mode,
        )
        for section in spec.sections
    ]
    for index, section in enumerate(sections):
        if index > 0:
            section.bridges_from = sections[index - 1].title
        if index + 1 < len(sections):
            section.bridges_to = sections[index + 1].title
    return sections


def _derive_learner_fit(profile: ClassProfile) -> str:
    if (
        profile.confidence == "low"
        or profile.reading_level == "below_grade"
        or profile.language_support in {"some_ell", "many_ell"}
    ):
        return "supported"
    if profile.confidence == "high" and profile.reading_level == "above_grade":
        return "advanced"
    return "general"


def _runtime_grade_band(brief: TeacherBrief) -> str:
    detailed_band = GRADE_BAND_BY_LEVEL.get(brief.grade_level, "mixed")
    if detailed_band in {"early_elementary", "upper_elementary"}:
        return "primary"
    if detailed_band in {"college", "adult"}:
        return "advanced"
    return "secondary"


def _context_from_planning_spec(spec: PlanningGenerationSpec) -> str:
    brief = spec.source_brief
    lines = [
        f"Subject: {brief.subject}",
        f"Topic: {brief.topic}",
        f"Subtopics: {', '.join(brief.subtopics)}",
        f"Grade level: {brief.grade_level}",
        f"Grade band: {brief.grade_band}",
        f"Learner summary: {brief.learner_context}",
        (
            "Class profile: "
            f"reading={brief.class_profile.reading_level}, "
            f"language={brief.class_profile.language_support}, "
            f"confidence={brief.class_profile.confidence}, "
            f"prior_knowledge={brief.class_profile.prior_knowledge}, "
            f"pacing={brief.class_profile.pacing}, "
            f"preferences={', '.join(brief.class_profile.learning_preferences) or 'none'}"
        ),
        f"Intended outcome: {brief.intended_outcome}",
        f"Resource type: {brief.resource_type}",
        f"Depth: {brief.depth}",
        f"Supports: {', '.join(brief.supports) if brief.supports else 'none'}",
    ]

    if brief.teacher_notes:
        lines.append(f"Teacher notes: {brief.teacher_notes}")

    lines.append("")
    lines.append("Reviewed resource plan:")

    for section in spec.sections:
        summary = section.focus_note or section.objective or section.rationale
        lines.append(f"Section {section.order}: {section.title} [{section.role}] - {summary}")

    if spec.warning:
        lines.append("")
        lines.append(f"Planning warning: {spec.warning}")

    return "\n".join(lines)


def validate_render_shell(template_id: str, preset_id: str) -> bool:
    return template_id == "guided-concept-path" and preset_id == "blue-classroom"


def validate_preset_for_template(template_id: str, preset_id: str) -> bool:
    _ = _legacy_validate_preset_for_template
    return validate_render_shell(template_id, preset_id)


@router.post("/brief/resolve-topic", response_model=TopicResolutionResult)
@limiter.limit("20/minute")
async def resolve_topic(
    request: Request,
    payload: TopicResolutionRequest,
    current_user: User = Depends(get_current_user),
) -> TopicResolutionResult:
    _ = (request, current_user)
    try:
        resolution = await _resolve_topic_with_llm(payload)
    except Exception as exc:
        logger.exception("Topic resolution failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Topic resolution failed. Please try again.",
        ) from exc

    deduped = []
    seen_titles: set[str] = set()
    for item in resolution.candidate_subtopics:
        key = item.title.strip().lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        deduped.append(item)
        if len(deduped) == 8:
            break

    return resolution.model_copy(update={"candidate_subtopics": deduped})


@router.post("/brief/validate", response_model=BriefValidationResult)
async def validate_teacher_brief(
    payload: BriefValidationRequest,
    current_user: User = Depends(get_current_user),
) -> BriefValidationResult:
    _ = current_user
    template = get_resource_template(payload.brief.resource_type)
    return validate_brief(payload.brief, template)


@router.post("/brief/review", response_model=BriefReviewResult)
async def review_teacher_brief(
    payload: BriefReviewRequest,
    current_user: User = Depends(get_current_user),
) -> BriefReviewResult:
    _ = current_user
    try:
        review = await _review_brief_with_llm(payload.brief)
    except Exception:
        logger.exception("TeacherBrief pedagogical review failed")
        warnings: list[BriefReviewWarning] = []
        if len(payload.brief.subtopics) >= 3 and payload.brief.depth == "quick":
            warnings.append(
                BriefReviewWarning(
                    message="Several subtopics with quick depth will likely force very shallow coverage.",
                    suggestion="Use standard depth or reduce the selected subtopics.",
                )
            )
        if payload.brief.resource_type in {"quiz", "exit_ticket"} and any(
            support in payload.brief.supports for support in {"worked_examples", "step_by_step"}
        ):
            warnings.append(
                BriefReviewWarning(
                    message="Scaffold-heavy supports can make this resource feel more like teaching than checking.",
                    suggestion="Switch resource type or remove the extra scaffolds.",
                )
            )
        return BriefReviewResult(coherent=len(warnings) == 0, warnings=warnings)

    return review


@router.post("/brief/plan", response_model=PlanningGenerationSpec)
@limiter.limit("20/minute")
async def plan_from_brief(
    request: Request,
    brief: TeacherBrief,
    current_user: User = Depends(get_current_user),
) -> PlanningGenerationSpec:
    _ = request
    trace_id = uuid.uuid4().hex
    service = PlanningService()

    async def run_planning_llm(**kwargs):
        caller = kwargs.get("caller", PLANNING_SECTION_COMPOSER_CALLER)
        return await run_llm(
            slot=get_planning_slot(caller),
            spec=get_planning_spec(caller),
            **kwargs,
        )

    try:
        core_events.event_bus.publish(
            trace_id,
            TraceRegisteredEvent(
                trace_id=trace_id,
                user_id=current_user.id,
                source="planning",
            ),
        )
        model = build_model(get_planning_spec(PLANNING_SECTION_COMPOSER_CALLER))
        return await service.plan(
            brief,
            model=model,
            run_llm_fn=run_planning_llm,
            generation_id=trace_id,
        )
    except Exception:
        logger.exception("TeacherBrief planning failed; returning deterministic fallback")
        return service.fallback(brief, generation_id=trace_id)
    finally:
        core_events.event_bus.publish(
            trace_id,
            TraceClosedEvent(trace_id=trace_id, source="planning"),
        )


@router.post("/brief/commit", response_model=GenerationAcceptedResponse)
async def commit_brief(
    spec: PlanningGenerationSpec,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
    engine=Depends(get_generation_engine),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    report_repo: GenerationReportRepository = Depends(get_report_repository),
) -> GenerationAcceptedResponse:
    if not validate_preset_for_template(spec.template_id, spec.preset_id):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid template/preset combination: {spec.template_id}/{spec.preset_id}",
        )

    profile = await _load_profile(current_user, profile_repo)
    committed = spec.model_copy(update={"status": "committed"})
    runtime_grade_band = _runtime_grade_band(committed.source_brief)
    learner_fit = _derive_learner_fit(committed.source_brief.class_profile)
    return await enqueue_generation(
        current_user=current_user,
        profile=profile,
        engine=engine,
        gen_repo=gen_repo,
        document_repo=document_repo,
        report_repo=report_repo,
        subject=committed.source_brief.subtopics[0],
        context=_context_from_planning_spec(committed),
        mode=committed.mode,
        template_id=committed.template_id,
        preset_id=committed.preset_id,
        section_count=len(committed.sections),
        section_plans=_pipeline_sections_from_planning_spec(committed),
        planning_spec_json=committed.model_dump_json(),
        grade_band=runtime_grade_band,
        learner_fit=learner_fit,
    )
