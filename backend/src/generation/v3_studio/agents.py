from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from core.llm.runner import run_llm
from core.llm.runner import RetryPolicy
from v3_blueprint.compiler import BlueprintCompiler
from v3_blueprint.models import ProductionBlueprint
from v3_execution.config import (
    get_v3_model,
    get_v3_slot,
    get_v3_spec,
    lesson_architect_model_settings,
)
from v3_execution.config.timeouts import V3_TIMEOUTS

from generation.v3_studio.dtos import (
    ProductionBlueprintEnvelope,
    V3ClarificationAnswer,
    V3ClarificationQuestion,
    V3InputForm,
    V3SignalSummary,
)
from generation.v3_studio.prompts import ADJUST_SYSTEM, CLARIFY_SYSTEM, SIGNAL_SYSTEM, build_architect_system_prompt

_CALLER = "v3_studio"


class ClarifyEnvelope(BaseModel):
    model_config = {"extra": "forbid"}

    questions: list[V3ClarificationQuestion] = Field(default_factory=list)


def form_to_lens_hints(form: V3InputForm) -> str:
    hints = [f"lesson_mode: {form.lesson_mode}"]
    if form.lesson_mode_other.strip():
        hints.append(f"lesson_mode_detail: {form.lesson_mode_other.strip()}")
    hints.append(f"intended_outcome: {form.intended_outcome}")
    if form.intended_outcome_other.strip():
        hints.append(f"intended_outcome_detail: {form.intended_outcome_other.strip()}")
    hints.append(f"learner_level: {form.learner_level}")
    hints.append(f"reading_level: {form.reading_level}")
    hints.append(f"language_support: {form.language_support}")
    hints.append(f"prior_knowledge_level: {form.prior_knowledge_level}")
    if form.support_needs:
        hints.append(f"support_needs: {', '.join(form.support_needs)}")
    if form.learning_preferences:
        hints.append(f"learning_preferences: {', '.join(form.learning_preferences)}")
    if form.subtopics:
        hints.append(f"subtopics: {', '.join(form.subtopics)}")
    if form.prior_knowledge.strip():
        hints.append(f"prior_knowledge: {form.prior_knowledge.strip()}")
    return "\n".join(hints)


def has_required_structured_fields(form: V3InputForm) -> bool:
    if not form.grade_level.strip():
        return False
    if not form.subject.strip():
        return False
    if not form.topic.strip() or len(form.topic.strip()) < 3:
        return False
    if not (15 <= form.duration_minutes <= 90):
        return False
    if not form.lesson_mode.strip():
        return False
    if not form.learner_level.strip():
        return False
    if not form.reading_level.strip():
        return False
    if not form.language_support.strip():
        return False
    if not form.prior_knowledge_level.strip():
        return False
    if not form.intended_outcome.strip():
        return False
    return True


async def extract_signals(form: V3InputForm, *, trace_id: str | None = None) -> V3SignalSummary:
    node = "v3_signal_extractor"
    tid = trace_id or str(uuid.uuid4())
    model = get_v3_model(node)
    spec = get_v3_spec(node)
    slot = get_v3_slot(node)
    agent = Agent(
        model=model,
        output_type=V3SignalSummary,
        system_prompt=SIGNAL_SYSTEM,
    )
    user = (
        f"Grade level: {form.grade_level}\n"
        f"Subject: {form.subject}\n"
        f"Duration minutes: {form.duration_minutes}\n"
        f"Topic: {form.topic}\n"
        f"Subtopics: {', '.join(form.subtopics) if form.subtopics else '(none)'}\n"
        f"Prior knowledge: {form.prior_knowledge or '(none)'}\n"
        f"Lesson mode: {form.lesson_mode}\n"
        f"Lesson mode other: {form.lesson_mode_other or '(none)'}\n"
        f"Intended outcome: {form.intended_outcome}\n"
        f"Intended outcome other: {form.intended_outcome_other or '(none)'}\n"
        f"Learner level: {form.learner_level}\n"
        f"Reading level: {form.reading_level}\n"
        f"Language support: {form.language_support}\n"
        f"Prior knowledge level: {form.prior_knowledge_level}\n"
        f"Support needs: {', '.join(form.support_needs) if form.support_needs else '(none)'}\n"
        f"Learning preferences: {', '.join(form.learning_preferences) if form.learning_preferences else '(none)'}\n\n"
        f"Additional notes (optional):\n{form.free_text.strip() or '(none)'}"
    )
    result = await run_llm(
        trace_id=tid,
        caller=_CALLER,
        generation_id=None,
        agent=agent,
        user_prompt=user,
        model=model,
        slot=slot,
        spec=spec,
        section_id=None,
        node=node,
        retry_policy=RetryPolicy(call_timeout_seconds=float(V3_TIMEOUTS["signal_extractor"])),
    )
    raw = result.output
    if isinstance(raw, V3SignalSummary):
        return raw
    raise RuntimeError("signal extractor returned unexpected output")


async def get_clarifications(
    signals: V3SignalSummary,
    form: V3InputForm,
    *,
    trace_id: str | None = None,
) -> list[V3ClarificationQuestion]:
    if has_required_structured_fields(form) and not signals.missing_signals:
        return []

    node = "v3_clarify"
    tid = trace_id or str(uuid.uuid4())
    model = get_v3_model(node)
    spec = get_v3_spec(node)
    slot = get_v3_slot(node)
    agent = Agent(
        model=model,
        output_type=ClarifyEnvelope,
        system_prompt=CLARIFY_SYSTEM,
    )
    user = f"Signals JSON:\n{signals.model_dump_json(indent=2)}\n\nForm:\n{form.model_dump_json(indent=2)}"
    result = await run_llm(
        trace_id=tid,
        caller=_CALLER,
        generation_id=None,
        agent=agent,
        user_prompt=user,
        model=model,
        slot=slot,
        spec=spec,
        section_id=None,
        node=node,
        retry_policy=RetryPolicy(call_timeout_seconds=float(V3_TIMEOUTS["clarification"])),
    )
    raw = result.output
    if hasattr(raw, "questions"):
        qs = list(raw.questions)[:2]  # type: ignore[attr-defined]
        return qs
    if isinstance(raw, ClarifyEnvelope):
        return raw.questions[:2]
    return []


def _validate_blueprint(bp: ProductionBlueprint) -> None:
    """
    Validate the architect-produced blueprint and raise structured errors.
    """
    from pydantic import ValidationError

    try:
        compiler_result = BlueprintCompiler().compile_all(bp)
    except ValidationError as exc:
        field_errors = [f"  {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        raise RuntimeError(
            f"Blueprint structure invalid ({len(field_errors)} error(s)):\n"
            + "\n".join(field_errors)
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Blueprint compiler raised unexpected error: {exc}") from exc

    if isinstance(compiler_result, list) and compiler_result:
        formatted = "\n".join(f"  - {e}" for e in compiler_result)
        raise RuntimeError(
            f"Blueprint failed domain validation:\n{formatted}\n"
            "Check component slugs, section_field uniqueness, and question_plan."
        )


def _render_resource_spec(
    inferred_resource_type: str | None,
    duration_minutes: int,
) -> str:
    """
    Render the resource spec for the inferred resource type into a prompt-ready string.

    Falls back to 'lesson' if the resource type is unknown or has no spec.
    Infers depth from duration: under 20 min → quick, over 45 min → deep, else standard.
    active_roles and active_supports are left empty — the architect decides those.
    """
    from resource_specs.loader import get_spec, list_spec_ids
    from resource_specs.renderer import render_spec_for_prompt

    resource_type = (inferred_resource_type or "lesson").lower().strip().replace(" ", "_")

    available = list_spec_ids()
    if resource_type not in available:
        resource_type = "lesson"

    depth = "quick" if duration_minutes < 20 else "deep" if duration_minutes > 45 else "standard"

    try:
        spec = get_spec(resource_type)
        return render_spec_for_prompt(
            spec,
            depth=depth,
            active_roles=[],
            active_supports=[],
        )
    except Exception:
        return (
            f"Resource type: {resource_type}\n"
            "(No detailed spec available for this type — use judgment based on resource intent.)"
        )


async def generate_production_blueprint(
    *,
    signals: V3SignalSummary,
    form: V3InputForm,
    clarification_answers: list[V3ClarificationAnswer] | None,
    trace_id: str | None = None,
) -> ProductionBlueprint:
    node = "v3_lesson_architect"
    tid = trace_id or str(uuid.uuid4())
    model = get_v3_model(node)
    spec = get_v3_spec(node)
    slot = get_v3_slot(node)
    agent = Agent(
        model=model,
        output_type=ProductionBlueprintEnvelope,
        system_prompt=build_architect_system_prompt(),
    )
    clar = clarification_answers or []
    clar_txt = "\n".join(f"Q: {c.question}\nA: {c.answer}" for c in clar)
    resource_spec_block = _render_resource_spec(
        inferred_resource_type=signals.inferred_resource_type,
        duration_minutes=form.duration_minutes,
    )

    user = (
        f"Signals:\n{signals.model_dump_json(indent=2)}\n\n"
        f"Form:\n{form.model_dump_json(indent=2)}\n\n"
        f"Clarifications:\n{clar_txt or '(none)'}\n\n"
        f"RESOURCE SPEC — treat structural rules as hard constraints:\n"
        f"{resource_spec_block}"
    )
    result = await run_llm(
        trace_id=tid,
        caller=_CALLER,
        generation_id=None,
        agent=agent,
        user_prompt=user,
        model=model,
        slot=slot,
        spec=spec,
        section_id=None,
        node=node,
        model_settings=lesson_architect_model_settings(),
        retry_policy=RetryPolicy(call_timeout_seconds=float(V3_TIMEOUTS["lesson_architect"])),
    )
    raw = result.output
    envelope = raw if isinstance(raw, ProductionBlueprintEnvelope) else None
    if envelope is None and hasattr(raw, "blueprint"):
        envelope = ProductionBlueprintEnvelope(blueprint=raw.blueprint)  # type: ignore[arg-type]
    if envelope is None:
        raise RuntimeError("lesson architect returned unexpected output")
    bp = envelope.blueprint
    bp.metadata.subject = form.subject.strip() or bp.metadata.subject
    _validate_blueprint(bp)
    return bp


async def adjust_production_blueprint(
    blueprint: ProductionBlueprint,
    adjustment: str,
    *,
    trace_id: str | None = None,
) -> ProductionBlueprint:
    node = "v3_blueprint_adjust"
    tid = trace_id or str(uuid.uuid4())
    model = get_v3_model(node)
    spec = get_v3_spec(node)
    slot = get_v3_slot(node)
    agent = Agent(
        model=model,
        output_type=ProductionBlueprintEnvelope,
        system_prompt=ADJUST_SYSTEM,
    )
    user = (
        "Current blueprint JSON:\n"
        f"{blueprint.model_dump_json(indent=2)}\n\n"
        f"Teacher adjustment:\n{adjustment.strip()}"
    )
    result = await run_llm(
        trace_id=tid,
        caller=_CALLER,
        generation_id=None,
        agent=agent,
        user_prompt=user,
        model=model,
        slot=slot,
        spec=spec,
        section_id=None,
        node=node,
    )
    raw = result.output
    envelope = raw if isinstance(raw, ProductionBlueprintEnvelope) else None
    if envelope is None and hasattr(raw, "blueprint"):
        envelope = ProductionBlueprintEnvelope(blueprint=raw.blueprint)  # type: ignore[arg-type]
    if envelope is None:
        raise RuntimeError("blueprint adjust returned unexpected output")
    bp = envelope.blueprint
    _validate_blueprint(bp)
    return bp


__all__ = [
    "adjust_production_blueprint",
    "extract_signals",
    "generate_production_blueprint",
    "get_clarifications",
]
