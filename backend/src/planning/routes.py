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
from pipeline.contracts import get_contract, validate_preset_for_template
from pipeline.resources import get_resource_template, validate_brief
from pipeline.types.requests import (
    GenerationMode,
    SectionPlan,
    SectionVisualPolicy,
    count_visual_placements,
    needs_diagram_from_placements,
)
from pipeline.types.teacher_brief import (
    BriefValidationRequest,
    BriefValidationResult,
    TeacherBrief,
    TopicResolutionRequest,
    TopicResolutionResult,
)
from planning import PlanningService
from planning.llm_config import (
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
            "Prefer age-appropriate subtopics when learner context is present.",
            "Set needs_clarification=true only when the topic is too vague to narrow responsibly.",
            "Do not invent niche or overly advanced subtopics when common classroom targets fit.",
        ]
    )


def _topic_resolution_user_prompt(payload: TopicResolutionRequest) -> str:
    return "\n".join(
        [
            f"Raw topic: {payload.raw_topic}",
            f"Learner context: {payload.learner_context or 'none'}",
            "Return:",
            "- subject",
            "- topic",
            "- candidate_subtopics: 4 to 8 items with id, title, description, likely_grade_band",
            "- needs_clarification",
            "- clarification_message when needed",
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


async def _load_profile(
    user: User,
    profile_repo: StudentProfileRepository,
) -> StudentProfile | None:
    return await profile_repo.find_by_user_id(user.id)


def _pipeline_section_from_planning(
    section: PlanningSectionPlan,
    *,
    always_present: list[str],
    generation_mode: GenerationMode,
) -> SectionPlan:
    selected = list(dict.fromkeys([*always_present, *section.selected_components]))
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
    contract = get_contract(spec.template_id)
    always_present = contract.always_present or contract.required_components
    sections = [
        _pipeline_section_from_planning(
            section,
            always_present=always_present,
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


def _context_from_planning_spec(spec: PlanningGenerationSpec) -> str:
    brief = spec.source_brief
    lines = [
        f"Subject: {brief.subject}",
        f"Topic: {brief.topic}",
        f"Subtopic: {brief.subtopic}",
        f"Audience: {brief.learner_context}",
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
    return await enqueue_generation(
        current_user=current_user,
        profile=profile,
        engine=engine,
        gen_repo=gen_repo,
        document_repo=document_repo,
        report_repo=report_repo,
        subject=committed.source_brief.subtopic,
        context=_context_from_planning_spec(committed),
        mode=committed.mode,
        template_id=committed.template_id,
        preset_id=committed.preset_id,
        section_count=len(committed.sections),
        section_plans=_pipeline_sections_from_planning_spec(committed),
        planning_spec_json=committed.model_dump_json(),
    )
