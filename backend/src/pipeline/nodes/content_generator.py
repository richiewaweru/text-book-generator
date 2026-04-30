"""Manifest-driven section content generation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.llm.logging import NodeLogger
from langchain_core.runnables.config import RunnableConfig
from pydantic import ValidationError
from pydantic_ai import Agent

from core.config import settings as app_settings
from pipeline.contracts import build_section_generation_manifest
from pipeline.events import (
    SectionFailedEvent,
    ValidationRepairAttemptedEvent,
    ValidationRepairSucceededEvent,
)
from pipeline.llm_runner import run_llm
from pipeline.prompts.content import (
    build_content_repair_user_prompt,
    build_section_system_prompt,
    build_section_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.runtime_context import retry_policy_for_node
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.runtime_policy import resolve_runtime_policy_bundle
from pipeline.state import (
    FailedSectionRecord,
    NodeFailureDetail,
    PipelineError,
    TextbookPipelineState,
)
from pipeline.types.generation_manifest import SectionGenerationManifest
from pipeline.types.requests import count_visual_placements, needs_diagram_from_placements
from pipeline.types.section_content import (
    SectionContent,
)

logger = logging.getLogger(__name__)


def _node_logger(state: TextbookPipelineState, section_id: str | None) -> NodeLogger:
    return NodeLogger(
        generation_id=state.request.generation_id or "",
        section_id=section_id,
        node_name="content_generator",
    )


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


def _detailed_validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    """Extract structured field-level errors for targeted repair prompts."""
    return [
        {
            "field": " -> ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]


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
        needs_diagram=needs_diagram_from_placements(plan),
        visual_placements_count=count_visual_placements(plan),
        needs_worked_example=plan.needs_worked_example if plan is not None else False,
        failed_at_node="content_generator",
        error_type=detail.error_type,
        error_summary=detail.error_message,
        attempt_count=_current_section_attempt(state, section_id),
        can_retry=can_retry,
        missing_components=list(plan.required_components) if plan is not None else [],
        failure_detail=detail,
    )


def _publish_section_failed(
    state: TextbookPipelineState,
    sid: str,
    failed_record: FailedSectionRecord,
) -> None:
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
            visual_placements_count=failed_record.visual_placements_count,
            needs_worked_example=failed_record.needs_worked_example,
            attempt_count=failed_record.attempt_count,
            can_retry=failed_record.can_retry,
            missing_components=failed_record.missing_components,
            failure_detail=failed_record.failure_detail,
        ),
    )


def _record_failure(
    *,
    state: TextbookPipelineState,
    sid: str,
    exc: Exception,
    node_failures: list[NodeFailureDetail],
    failed_sections: dict,
    errors: list,
    retry_attempt: int = 0,
) -> None:
    """Record a non-validation failure into the shared accumulators."""
    detail = _failure_detail(
        section_id=sid,
        error=exc,
        retry_attempt=retry_attempt,
        will_retry=False,
    )
    node_failures.append(detail)
    failed_record = _failed_section_record(
        state=state, section_id=sid, detail=detail, can_retry=True
    )
    failed_sections[sid] = failed_record
    _publish_section_failed(state, sid, failed_record)
    errors.append(
        PipelineError(
            node="content_generator",
            section_id=sid,
            message=f"LLM call failed: {exc}",
            recoverable=True,
        )
    )


def _retry_policy(
    state: TextbookPipelineState,
    *,
    config: RunnableConfig | None,
    node: str,
):
    return retry_policy_for_node(config, node) or resolve_runtime_policy_bundle(
        app_settings,
        state.request.mode,
    ).retries.for_node(node)


async def _generate_monolithic(
    *,
    state: TextbookPipelineState,
    sid: str,
    model,
    model_overrides: dict | None,
    config: RunnableConfig | None,
    plan,
    rerender_reason: str | None,
    generated: dict,
    failed_sections: dict,
    errors: list,
    node_failures: list[NodeFailureDetail],
    manifest: SectionGenerationManifest,
) -> None:
    """Generate one section from the approved manifest."""
    _ = model_overrides
    agent = Agent(
        model=model,
        output_type=SectionContent,
        system_prompt=build_section_system_prompt(manifest),
    )
    base_prompt = build_section_user_prompt(
        plan=plan,
        subject=state.request.subject,
        context=state.request.context,
        grade_band=state.request.grade_band,
        learner_fit=state.request.learner_fit,
        manifest=manifest,
        rerender_reason=rerender_reason,
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
            retry_policy=_retry_policy(
                state,
                config=config,
                node="content_generator",
            ),
        )
        generated[sid] = result.output
    except Exception as exc:
        if _looks_like_validation_error(exc):
            _handle_validation_repair(
                state=state,
                sid=sid,
                exc=exc,
                agent=agent,
                model=model,
                plan=plan,
                manifest=manifest,
                rerender_reason=rerender_reason,
                generated=generated,
                failed_sections=failed_sections,
                errors=errors,
                node_failures=node_failures,
            )
        else:
            _record_failure(
                state=state,
                sid=sid,
                exc=exc,
                node_failures=node_failures,
                failed_sections=failed_sections,
                errors=errors,
            )


def _handle_validation_repair(
    *,
    state: TextbookPipelineState,
    sid: str,
    exc: Exception,
    agent,
    model,
    plan,
    manifest,
    rerender_reason,
    generated: dict,
    failed_sections: dict,
    errors: list,
    node_failures: list[NodeFailureDetail],
) -> None:
    """Prepare a repair request for the caller to await."""
    raise _RepairNeeded(
        exc=exc,
        agent=agent,
        model=model,
        plan=plan,
        manifest=manifest,
        rerender_reason=rerender_reason,
    )


class _RepairNeeded(Exception):
    """Internal sentinel - never escapes content_generator."""

    def __init__(self, *, exc, agent, model, plan, manifest, rerender_reason):
        self.original_exc = exc
        self.agent = agent
        self.model = model
        self.plan = plan
        self.manifest = manifest
        self.rerender_reason = rerender_reason


async def _attempt_repair(
    *,
    state: TextbookPipelineState,
    sid: str,
    repair: _RepairNeeded,
    config: RunnableConfig | None,
    generated: dict,
    failed_sections: dict,
    errors: list,
    node_failures: list[NodeFailureDetail],
) -> None:
    exc = repair.original_exc
    node_logger = _node_logger(state, sid)
    initial_detail = _failure_detail(
        section_id=sid, error=exc, retry_attempt=0, will_retry=True
    )
    node_failures.append(initial_detail)
    detailed_errors = (
        _detailed_validation_errors(exc)
        if isinstance(exc, ValidationError)
        else []
    )
    publish_runtime_event(
        state.request.generation_id or "",
        ValidationRepairAttemptedEvent(
            generation_id=state.request.generation_id or "",
            section_id=sid,
            error_summary=initial_detail.error_message,
        ),
    )
    node_logger.warning(
        "content_generator validation failed; attempting repair section=%s error=%s",
        sid,
        initial_detail.error_message,
    )
    try:
        repair_result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="content_generator_repair",
            agent=repair.agent,
            model=repair.model,
            user_prompt=build_content_repair_user_prompt(
                section_plan=repair.plan,
                subject=state.request.subject,
                context=state.request.context,
                grade_band=state.request.grade_band,
                learner_fit=state.request.learner_fit,
                manifest=repair.manifest,
                validation_summary=initial_detail.error_message,
                validation_errors=detailed_errors,
                rerender_reason=repair.rerender_reason,
            ),
            section_id=sid,
            generation_mode=state.request.mode,
            retry_policy=_retry_policy(
                state,
                config=config,
                node="content_generator_repair",
            ),
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
            section_id=sid, error=repair_exc, retry_attempt=1, will_retry=False
        )
        node_failures.append(final_detail)
        failed_record = _failed_section_record(
            state=state, section_id=sid, detail=final_detail, can_retry=True
        )
        failed_sections[sid] = failed_record
        _publish_section_failed(state, sid, failed_record)
        errors.append(
            PipelineError(
                node="content_generator",
                section_id=sid,
                message=final_detail.error_message,
                recoverable=True,
            )
        )


async def content_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """Generate or rerender one section's core teaching content."""

    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    plan = state.current_section_plan

    rerender_request = state.pending_rerender_for(sid)
    rerender_reason = rerender_request.reason if rerender_request else None
    is_rerender = rerender_reason is not None

    model = get_node_text_model(
        "content_generator",
        model_overrides=model_overrides,
        generation_mode=state.request.mode,
    )

    generated = dict(state.generated_sections)
    failed_sections = dict(state.failed_sections)
    errors: list[PipelineError] = []
    node_failures: list[NodeFailureDetail] = []
    manifest = build_section_generation_manifest(
        template_id=state.contract.id,
        section_plan=plan,
    )

    try:
        await _generate_monolithic(
            state=state,
            sid=sid,
            model=model,
            model_overrides=model_overrides,
            config=config,
            plan=plan,
            rerender_reason=rerender_reason,
            generated=generated,
            failed_sections=failed_sections,
            errors=errors,
            node_failures=node_failures,
            manifest=manifest,
        )
    except _RepairNeeded as repair:
        await _attempt_repair(
            state=state,
            sid=sid,
            repair=repair,
            config=config,
            generated=generated,
            failed_sections=failed_sections,
            errors=errors,
            node_failures=node_failures,
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
