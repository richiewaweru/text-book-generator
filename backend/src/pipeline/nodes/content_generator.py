"""
content_generator node.

Produces a SectionContent object per section.
Slot assignment is resolved centrally as STANDARD.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import ValidationError
from pydantic_ai import Agent

from pipeline.events import (
    SectionFailedEvent,
    ValidationRepairAttemptedEvent,
    ValidationRepairSucceededEvent,
)
from pipeline.prompts.content import (
    build_content_repair_user_prompt,
    build_content_system_prompt,
    build_content_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.state import (
    FailedSectionRecord,
    NodeFailureDetail,
    PipelineError,
    TextbookPipelineState,
)
from pipeline.types.section_content import SectionContent
from pipeline.llm_runner import run_llm

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_section_attempt(state: TextbookPipelineState, section_id: str | None) -> int:
    if section_id is None:
        return 0
    attempt = state.rerender_count.get(section_id, 0) + 1
    if state.pending_rerender_for(section_id) is not None:
        attempt += 1
    return attempt


def _error_type(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, ValidationError):
        return "validation"
    if "validation" in message or "output validation" in message or "schema" in message:
        return "validation"
    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "429" in message or "rate limit" in message:
        return "provider"
    if any(provider in message for provider in ("anthropic", "openai", "google", "provider")):
        return "provider"
    return "unknown"


def _error_summary(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]["msg"] if exc.errors() else "unknown validation error"
        return f"Schema validation failed: {exc.error_count()} errors. First: {first}"
    return str(exc)


def _looks_like_validation_error(exc: Exception) -> bool:
    return _error_type(exc) == "validation"


def _failure_detail(
    *,
    section_id: str,
    error: Exception,
    retry_attempt: int,
    will_retry: bool,
) -> NodeFailureDetail:
    return NodeFailureDetail(
        node="content_generator",
        section_id=section_id,
        timestamp=_now_iso(),
        error_type=_error_type(error),
        error_message=_error_summary(error),
        retry_attempt=retry_attempt,
        will_retry=will_retry,
    )


def _failed_section_record(
    *,
    state: TextbookPipelineState,
    section_id: str,
    detail: NodeFailureDetail,
    can_retry: bool,
) -> FailedSectionRecord:
    plan = state.current_section_plan
    title = plan.title if plan is not None else section_id
    position = plan.position if plan is not None else 0
    return FailedSectionRecord(
        section_id=section_id,
        title=title,
        position=position,
        focus=plan.focus if plan is not None else None,
        bridges_from=plan.bridges_from if plan is not None else None,
        bridges_to=plan.bridges_to if plan is not None else None,
        needs_diagram=plan.needs_diagram if plan is not None else False,
        needs_worked_example=plan.needs_worked_example if plan is not None else False,
        failed_at_node="content_generator",
        error_type=detail.error_type,
        error_summary=detail.error_message,
        attempt_count=_current_section_attempt(state, section_id),
        can_retry=can_retry,
        missing_components=list(state.contract.required_components),
        failure_detail=detail,
    )


def _seed_section(state: TextbookPipelineState, section_id: str | None) -> SectionContent | None:
    """Return the matching seeded section so rerenders can preserve intent."""

    if section_id is None or state.request.seed_document is None:
        return None
    for section in state.request.seed_document.sections:
        if section.section_id == section_id:
            return section
    return None


async def content_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Generate or rerender one section's core teaching content."""

    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    plan = state.current_section_plan

    rerender_request = state.pending_rerender_for(sid)
    rerender_reason = rerender_request.reason if rerender_request else None

    is_rerender = rerender_reason is not None
    seed_section = _seed_section(state, sid)
    seed_note = state.request.seed_document.note if state.request.seed_document else None

    model = get_node_text_model(
        "content_generator",
        model_overrides=model_overrides,
        generation_mode=state.request.mode,
    )
    agent = Agent(
        model=model,
        output_type=SectionContent,
        system_prompt=build_content_system_prompt(
            template_id=state.contract.id,
            template_name=state.contract.name,
            template_family=state.contract.family,
        ),
    )

    generated = dict(state.generated_sections)
    failed_sections = dict(state.failed_sections)
    errors = []
    node_failures: list[NodeFailureDetail] = []
    failed_record: FailedSectionRecord | None = None
    base_prompt = build_content_user_prompt(
        section_plan=plan,
        subject=state.request.subject,
        context=state.request.context,
        grade_band=state.request.grade_band,
        learner_fit=state.request.learner_fit,
        template_id=state.contract.id,
        rerender_reason=rerender_reason,
        seed_section=seed_section,
        seed_note=seed_note,
    )

    try:
        result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="content_generator",
            agent=agent,
            model=model,
            user_prompt=base_prompt,
            section_id=sid,
            generation_mode=state.request.mode,
        )
        generated[sid] = result.output
    except Exception as exc:
        if sid is None:
            raise

        if _looks_like_validation_error(exc):
            initial_detail = _failure_detail(
                section_id=sid,
                error=exc,
                retry_attempt=0,
                will_retry=True,
            )
            node_failures.append(initial_detail)
            publish_runtime_event(
                state.request.generation_id or "",
                ValidationRepairAttemptedEvent(
                    generation_id=state.request.generation_id or "",
                    section_id=sid,
                    error_summary=initial_detail.error_message,
                ),
            )
            logger.warning(
                "content_generator validation failed; attempting one repair section=%s error=%s",
                sid,
                initial_detail.error_message,
            )
            try:
                repair_result = await run_llm(
                    generation_id=state.request.generation_id or "",
                    node="content_generator_repair",
                    agent=agent,
                    model=model,
                    user_prompt=build_content_repair_user_prompt(
                        section_plan=plan,
                        subject=state.request.subject,
                        context=state.request.context,
                        grade_band=state.request.grade_band,
                        learner_fit=state.request.learner_fit,
                        template_id=state.contract.id,
                        validation_summary=initial_detail.error_message,
                        rerender_reason=rerender_reason,
                        seed_section=seed_section,
                        seed_note=seed_note,
                    ),
                    section_id=sid,
                    generation_mode=state.request.mode,
                )
                generated[sid] = repair_result.output
                publish_runtime_event(
                    state.request.generation_id or "",
                    ValidationRepairSucceededEvent(
                        generation_id=state.request.generation_id or "",
                        section_id=sid,
                    ),
                )
            except Exception as repair_exc:
                final_detail = _failure_detail(
                    section_id=sid,
                    error=repair_exc,
                    retry_attempt=1,
                    will_retry=False,
                )
                node_failures.append(final_detail)
                failed_record = _failed_section_record(
                    state=state,
                    section_id=sid,
                    detail=final_detail,
                    can_retry=True,
                )
                failed_sections[sid] = failed_record
                publish_runtime_event(
                    state.request.generation_id or "",
                    SectionFailedEvent(
                        generation_id=state.request.generation_id or "",
                        section_id=sid,
                        title=failed_record.title,
                        position=failed_record.position,
                        failed_at_node=failed_record.failed_at_node,
                        error_type=failed_record.error_type,
                        error_summary=failed_record.error_summary,
                        focus=failed_record.focus,
                        bridges_from=failed_record.bridges_from,
                        bridges_to=failed_record.bridges_to,
                        needs_diagram=failed_record.needs_diagram,
                        needs_worked_example=failed_record.needs_worked_example,
                        attempt_count=failed_record.attempt_count,
                        can_retry=failed_record.can_retry,
                        missing_components=failed_record.missing_components,
                        failure_detail=failed_record.failure_detail,
                    ),
                )
                errors.append(
                    PipelineError(
                        node="content_generator",
                        section_id=sid,
                        message=final_detail.error_message,
                        recoverable=True,
                    )
                )
        else:
            detail = _failure_detail(
                section_id=sid,
                error=exc,
                retry_attempt=0,
                will_retry=False,
            )
            node_failures.append(detail)
            failed_record = _failed_section_record(
                state=state,
                section_id=sid,
                detail=detail,
                can_retry=True,
            )
            failed_sections[sid] = failed_record
            publish_runtime_event(
                state.request.generation_id or "",
                SectionFailedEvent(
                    generation_id=state.request.generation_id or "",
                    section_id=sid,
                    title=failed_record.title,
                    position=failed_record.position,
                    failed_at_node=failed_record.failed_at_node,
                    error_type=failed_record.error_type,
                    error_summary=failed_record.error_summary,
                    focus=failed_record.focus,
                    bridges_from=failed_record.bridges_from,
                    bridges_to=failed_record.bridges_to,
                    needs_diagram=failed_record.needs_diagram,
                    needs_worked_example=failed_record.needs_worked_example,
                    attempt_count=failed_record.attempt_count,
                    can_retry=failed_record.can_retry,
                    missing_components=failed_record.missing_components,
                    failure_detail=failed_record.failure_detail,
                ),
            )
            errors.append(
                PipelineError(
                    node="content_generator",
                    section_id=sid,
                    message=f"LLM call failed: {exc}",
                    recoverable=True,
                )
            )

    new_rerender_count = dict(state.rerender_count)
    if is_rerender and sid:
        new_rerender_count[sid] = state.rerender_count.get(sid, 0) + 1

    output: dict = {
        "generated_sections": generated,
        "rerender_count": new_rerender_count,
        "completed_nodes": ["content_generator"],
    }
    if node_failures:
        output["node_failures"] = node_failures
    if failed_sections:
        output["failed_sections"] = failed_sections
    if errors:
        output["errors"] = errors

    return output
