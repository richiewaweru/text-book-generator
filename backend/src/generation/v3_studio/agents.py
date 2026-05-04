from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from core.llm.runner import run_llm
from v3_blueprint.compiler import BlueprintCompiler
from v3_blueprint.models import ProductionBlueprint
from v3_execution.config import (
    get_v3_model,
    get_v3_slot,
    get_v3_spec,
    lesson_architect_model_settings,
)

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
        f"Year group: {form.year_group}\n"
        f"Subject: {form.subject}\n"
        f"Duration minutes: {form.duration_minutes}\n\n"
        f"Teacher intent:\n{form.free_text.strip()}"
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
    if isinstance(raw, V3SignalSummary):
        return raw
    raise RuntimeError("signal extractor returned unexpected output")


async def get_clarifications(
    signals: V3SignalSummary,
    form: V3InputForm,
    *,
    trace_id: str | None = None,
) -> list[V3ClarificationQuestion]:
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
    )
    raw = result.output
    if hasattr(raw, "questions"):
        qs = list(raw.questions)[:2]  # type: ignore[attr-defined]
        return qs
    if isinstance(raw, ClarifyEnvelope):
        return raw.questions[:2]
    return []


def _validate_blueprint(bp: ProductionBlueprint) -> None:
    BlueprintCompiler().compile_all(bp)


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
    user = (
        f"Signals:\n{signals.model_dump_json(indent=2)}\n\n"
        f"Form:\n{form.model_dump_json(indent=2)}\n\n"
        f"Clarifications:\n{clar_txt or '(none)'}"
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
