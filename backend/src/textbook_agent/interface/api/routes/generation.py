from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from time import perf_counter

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from pipeline.api import PipelineCommand, PipelineDocument, PipelineSectionManifestItem
from pipeline.contracts import get_contract, validate_preset_for_template
from pipeline.events import (
    CompleteEvent,
    ErrorEvent,
    LLMCallFailedEvent,
    LLMCallStartedEvent,
    LLMCallSucceededEvent,
    SectionReadyEvent,
    SectionStartedEvent,
    event_bus,
)
from pipeline.runtime_diagnostics import clear_node_attempts
from pipeline.run import run_pipeline_streaming
from pipeline.types.requests import SeedDocument
from textbook_agent.application.dtos import (
    EnhanceGenerationRequest,
    GenerationAcceptedResponse,
    GenerationRequest,
)
from textbook_agent.application.services.generation_report_recorder import (
    GenerationReportRecorder,
)
from textbook_agent.domain.entities.generation import Generation
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.ports.document_repository import DocumentRepository
from textbook_agent.domain.ports.generation_report_repository import (
    GenerationReportRepository,
)
from textbook_agent.domain.ports.generation_repository import GenerationRepository
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.ports.user_repository import UserRepository
from textbook_agent.domain.services.generation_failure import classify_generation_failure
from textbook_agent.domain.value_objects import EducationLevel, GenerationMode
from textbook_agent.infrastructure.auth.jwt_handler import JWTHandler
from textbook_agent.interface.api.dependencies import (
    get_document_repository,
    get_generation_repository,
    get_jwt_handler,
    get_report_repository,
    get_settings,
    get_student_profile_repository,
    get_user_repository,
)
from textbook_agent.interface.api.generation_recovery import (
    INTERRUPTED_GENERATION_ERROR,
    INTERRUPTED_GENERATION_ERROR_CODE,
    INTERRUPTED_GENERATION_ERROR_TYPE,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["generation"])


def _history_item(generation: Generation) -> dict:
    return {
        "id": generation.id,
        "subject": generation.subject,
        "status": generation.status,
        "mode": generation.mode,
        "source_generation_id": generation.source_generation_id,
        "error_type": generation.error_type,
        "error_code": generation.error_code,
        "requested_template_id": generation.requested_template_id,
        "resolved_template_id": generation.resolved_template_id,
        "requested_preset_id": generation.requested_preset_id,
        "resolved_preset_id": generation.resolved_preset_id,
        "section_count": generation.section_count,
        "quality_passed": generation.quality_passed,
        "generation_time_seconds": generation.generation_time_seconds,
        "created_at": generation.created_at.isoformat() if generation.created_at else None,
        "completed_at": generation.completed_at.isoformat() if generation.completed_at else None,
    }


def _detail_item(generation: Generation) -> dict:
    _, _, report_url = _generation_urls(generation.id)
    return {
        "id": generation.id,
        "subject": generation.subject,
        "context": generation.context,
        "status": generation.status,
        "mode": generation.mode,
        "source_generation_id": generation.source_generation_id,
        "error": generation.error,
        "error_type": generation.error_type,
        "error_code": generation.error_code,
        "requested_template_id": generation.requested_template_id,
        "resolved_template_id": generation.resolved_template_id,
        "requested_preset_id": generation.requested_preset_id,
        "resolved_preset_id": generation.resolved_preset_id,
        "section_count": generation.section_count,
        "quality_passed": generation.quality_passed,
        "generation_time_seconds": generation.generation_time_seconds,
        "created_at": generation.created_at.isoformat() if generation.created_at else None,
        "completed_at": generation.completed_at.isoformat() if generation.completed_at else None,
        "document_path": generation.document_path,
        "report_url": report_url,
    }


def _grade_band(profile: StudentProfile) -> str:
    mapping = {
        EducationLevel.ELEMENTARY: "primary",
        EducationLevel.MIDDLE_SCHOOL: "secondary",
        EducationLevel.HIGH_SCHOOL: "secondary",
        EducationLevel.UNDERGRADUATE: "advanced",
        EducationLevel.GRADUATE: "advanced",
        EducationLevel.PROFESSIONAL: "advanced",
    }
    return mapping[profile.education_level]


def _generation_urls(generation_id: str) -> tuple[str, str, str]:
    return (
        f"/api/v1/generations/{generation_id}/events",
        f"/api/v1/generations/{generation_id}/document",
        f"/api/v1/generations/{generation_id}/report",
    )


def _initial_document(
    generation: Generation,
    *,
    section_manifest: list[PipelineSectionManifestItem] | None = None,
    sections: list | None = None,
    status_value: str = "pending",
) -> PipelineDocument:
    now = datetime.now(timezone.utc)
    return PipelineDocument(
        generation_id=generation.id,
        subject=generation.subject,
        context=generation.context,
        mode=generation.mode.value,
        template_id=generation.requested_template_id,
        preset_id=generation.requested_preset_id,
        source_generation_id=generation.source_generation_id,
        status=status_value,
        section_manifest=section_manifest or [],
        sections=sections or [],
        created_at=generation.created_at,
        updated_at=now,
    )


def _sort_sections_by_manifest(
    sections: list,
    section_manifest: list[PipelineSectionManifestItem],
) -> list:
    if not section_manifest:
        return sections

    positions = {item.section_id: item.position for item in section_manifest}
    fallback_position = len(positions) + 1
    return sorted(
        sections,
        key=lambda section: (
            positions.get(section.section_id, fallback_position),
            section.section_id,
        ),
    )


def _replace_or_append_manifest_item(
    document: PipelineDocument,
    section_id: str,
    title: str,
    position: int,
) -> PipelineDocument:
    manifest = list(document.section_manifest)
    next_item = PipelineSectionManifestItem(
        section_id=section_id,
        title=title,
        position=position,
    )
    for index, existing in enumerate(manifest):
        if existing.section_id == section_id:
            manifest[index] = next_item
            break
    else:
        manifest.append(next_item)

    manifest.sort(key=lambda item: (item.position, item.section_id))
    return document.model_copy(
        update={
            "section_manifest": manifest,
            "updated_at": datetime.now(timezone.utc),
            "status": "running",
        }
    )


def _replace_or_append_section(document: PipelineDocument, section) -> PipelineDocument:
    sections = list(document.sections)
    for index, existing in enumerate(sections):
        if existing.section_id == section.section_id:
            sections[index] = section
            break
    else:
        sections.append(section)
    return document.model_copy(
        update={
            "sections": _sort_sections_by_manifest(sections, document.section_manifest),
            "updated_at": datetime.now(timezone.utc),
            "status": "running",
        }
    )


async def _stream_user_from_token(
    request: Request,
    jwt_handler: JWTHandler,
    user_repo: UserRepository,
) -> User:
    token = request.query_params.get("token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing stream token",
        )

    try:
        payload = jwt_handler.decode_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await user_repo.find_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def _sse_payload(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


def _log_trace_event(generation_id: str, event) -> None:
    if isinstance(event, LLMCallStartedEvent):
        logger.info(
            "LLM trace generation=%s event=started node=%s section=%s attempt=%s family=%s model=%s endpoint=%s",
            generation_id,
            event.node,
            event.section_id or "-",
            event.attempt,
            event.family or "-",
            event.model_name or "-",
            event.endpoint_host or "-",
        )
        return

    if isinstance(event, LLMCallSucceededEvent):
        logger.info(
            "LLM trace generation=%s event=succeeded node=%s section=%s attempt=%s latency_ms=%s tokens_in=%s tokens_out=%s cost_usd=%s family=%s model=%s endpoint=%s",
            generation_id,
            event.node,
            event.section_id or "-",
            event.attempt,
            f"{event.latency_ms:.0f}" if event.latency_ms is not None else "-",
            event.tokens_in if event.tokens_in is not None else "-",
            event.tokens_out if event.tokens_out is not None else "-",
            f"{event.cost_usd:.6f}" if event.cost_usd is not None else "-",
            event.family or "-",
            event.model_name or "-",
            event.endpoint_host or "-",
        )
        return

    if isinstance(event, LLMCallFailedEvent):
        logger.warning(
            "LLM trace generation=%s event=failed node=%s section=%s attempt=%s retryable=%s latency_ms=%s family=%s model=%s endpoint=%s error=%s",
            generation_id,
            event.node,
            event.section_id or "-",
            event.attempt,
            event.retryable,
            f"{event.latency_ms:.0f}" if event.latency_ms is not None else "-",
            event.family or "-",
            event.model_name or "-",
            event.endpoint_host or "-",
            event.error,
        )


_GENERATION_JOB_TIMEOUT_SECONDS = 300.0
_RECORDER_WAIT_TIMEOUT_SECONDS = 5.0
_RECORDER_FINALIZE_TIMEOUT_SECONDS = 5.0
_REPORT_SNAPSHOT_TIMEOUT_SECONDS = 5.0
_SSE_KEEPALIVE_TIMEOUT_SECONDS = 15.0
_GENERATION_TIMEOUT_ERROR_CODE = "generation_timeout"
_ORPHANED_GENERATION_ERROR_CODE = "orphaned_generation"
_ORPHANED_GENERATION_ERROR_MESSAGE = "Pipeline ended without completion."


def _complete_event(generation_id: str) -> CompleteEvent:
    _, document_url, report_url = _generation_urls(generation_id)
    return CompleteEvent(
        generation_id=generation_id,
        document_url=document_url,
        report_url=report_url,
    )


def _error_event(generation_id: str, message: str) -> ErrorEvent:
    _, _, report_url = _generation_urls(generation_id)
    return ErrorEvent(
        generation_id=generation_id,
        message=message,
        report_url=report_url,
    )


def _failed_document_snapshot(
    document: PipelineDocument,
    *,
    error_message: str,
    completed_at: datetime,
) -> PipelineDocument:
    return document.model_copy(
        update={
            "status": "failed",
            "quality_passed": False,
            "error": error_message,
            "updated_at": completed_at,
            "completed_at": completed_at,
        }
    )


async def _persist_failed_generation_state(
    *,
    generation: Generation,
    gen_repo: GenerationRepository,
    document_repo: DocumentRepository,
    document: PipelineDocument,
    error_message: str,
    error_type: str,
    error_code: str | None,
    generation_time_seconds: float | None,
) -> PipelineDocument:
    completed_at = datetime.now(timezone.utc)
    failed_document = _failed_document_snapshot(
        document,
        error_message=error_message,
        completed_at=completed_at,
    )
    document_path = await document_repo.save_document(failed_document)
    await gen_repo.update_status(
        generation.id,
        status="failed",
        document_path=document_path,
        error=error_message,
        error_type=error_type,
        error_code=error_code,
        quality_passed=False,
        generation_time_seconds=generation_time_seconds,
    )
    return failed_document


async def _save_report_snapshot_with_timeout(
    *,
    report_repo: GenerationReportRepository,
    generation_id: str,
    report,
    phase: str,
) -> bool:
    try:
        await asyncio.wait_for(
            report_repo.save_report(report),
            timeout=_REPORT_SNAPSHOT_TIMEOUT_SECONDS,
        )
        return True
    except Exception:
        logger.exception(
            "Generation %s failed to persist %s report snapshot",
            generation_id,
            phase,
        )
        return False


def _log_recorder_degradation(
    *,
    generation_id: str,
    recorder: GenerationReportRecorder,
    phase: str,
) -> None:
    if not recorder.diagnostics_degraded:
        return
    logger.warning(
        "Generation %s diagnostics degraded during %s consumer_dead=%s dropped_events=%s consumer_error=%s",
        generation_id,
        phase,
        recorder.consumer_dead,
        recorder.dropped_event_count,
        str(recorder.consumer_error) if recorder.consumer_error is not None else "-",
    )


async def _run_generation_job(
    generation: Generation,
    command: PipelineCommand,
    gen_repo: GenerationRepository,
    document_repo: DocumentRepository,
    report_repo: GenerationReportRepository,
    initial_document: PipelineDocument,
) -> None:
    recorder = GenerationReportRecorder(generation=generation, repository=report_repo)
    document = initial_document.model_copy(
        update={"status": "running", "updated_at": datetime.now(timezone.utc)}
    )
    started = perf_counter()

    async def on_event(event) -> None:
        nonlocal document
        if isinstance(event, SectionStartedEvent):
            document = _replace_or_append_manifest_item(
                document,
                section_id=event.section_id,
                title=event.title,
                position=event.position,
            )
            await document_repo.save_document(document)
        if isinstance(event, SectionReadyEvent):
            document = _replace_or_append_section(document, event.section)
            await document_repo.save_document(document)
        event_bus.publish(generation.id, event)

    async def finalize_failure(
        *,
        error_message: str,
        error_type: str,
        error_code: str | None,
        generation_time_seconds: float | None,
    ) -> None:
        nonlocal document
        document = await _persist_failed_generation_state(
            generation=generation,
            gen_repo=gen_repo,
            document_repo=document_repo,
            document=document,
            error_message=error_message,
            error_type=error_type,
            error_code=error_code,
            generation_time_seconds=generation_time_seconds,
        )
        event_bus.publish(
            generation.id,
            _error_event(generation.id, error_message),
        )
        await recorder.wait_for_idle(timeout=_RECORDER_WAIT_TIMEOUT_SECONDS)
        _log_recorder_degradation(
            generation_id=generation.id,
            recorder=recorder,
            phase="failure_wait",
        )
        try:
            await asyncio.wait_for(
                recorder.finalize_failure(
                    error=error_message,
                    generation_time_seconds=generation_time_seconds,
                ),
                timeout=_RECORDER_FINALIZE_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception(
                "Generation %s failed to finalize diagnostics report after error",
                generation.id,
            )
            snapshot = recorder.build_failure_snapshot(
                error=error_message,
                generation_time_seconds=generation_time_seconds,
            )
            await _save_report_snapshot_with_timeout(
                report_repo=report_repo,
                generation_id=generation.id,
                report=snapshot,
                phase="failure_fallback",
            )
        recorder.log_final_summary()

    async def finalize_success(
        *,
        generation_time_seconds: float | None,
    ) -> None:
        await recorder.wait_for_idle(timeout=_RECORDER_WAIT_TIMEOUT_SECONDS)
        _log_recorder_degradation(
            generation_id=generation.id,
            recorder=recorder,
            phase="success_wait",
        )
        try:
            await asyncio.wait_for(
                recorder.finalize_success(
                    document=document,
                    generation_time_seconds=generation_time_seconds,
                ),
                timeout=_RECORDER_FINALIZE_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception(
                "Generation %s failed to finalize diagnostics report after completion",
                generation.id,
            )
            snapshot = recorder.build_success_snapshot(
                document=document,
                generation_time_seconds=generation_time_seconds,
            )
            await _save_report_snapshot_with_timeout(
                report_repo=report_repo,
                generation_id=generation.id,
                report=snapshot,
                phase="success_fallback",
            )
        recorder.log_final_summary()

    try:
        await recorder.start()
        document_path = await document_repo.save_document(document)
        await gen_repo.update_status(
            generation.id,
            status="running",
            document_path=document_path,
        )

        result = await asyncio.wait_for(
            run_pipeline_streaming(command, on_event=on_event),
            timeout=_GENERATION_JOB_TIMEOUT_SECONDS,
        )
        completed_at = datetime.now(timezone.utc)
        document = result.document.model_copy(
            update={
                "created_at": initial_document.created_at,
                "updated_at": completed_at,
                "completed_at": completed_at,
                "status": "completed",
            }
        )
        document_path = await document_repo.save_document(document)
        await gen_repo.update_status(
            generation.id,
            status="completed",
            document_path=document_path,
            resolved_template_id=document.template_id,
            resolved_preset_id=document.preset_id,
            quality_passed=document.quality_passed,
            generation_time_seconds=result.generation_time_seconds,
        )
        event_bus.publish(generation.id, _complete_event(generation.id))
        await finalize_success(generation_time_seconds=result.generation_time_seconds)
    except asyncio.TimeoutError:
        logger.error(
            "Generation %s timed out after %.0fs",
            generation.id,
            _GENERATION_JOB_TIMEOUT_SECONDS,
        )
        try:
            await finalize_failure(
                error_message=(
                    f"Generation timed out after {int(_GENERATION_JOB_TIMEOUT_SECONDS)} seconds."
                ),
                error_type="runtime_error",
                error_code=_GENERATION_TIMEOUT_ERROR_CODE,
                generation_time_seconds=perf_counter() - started,
            )
        except Exception:
            logger.exception(
                "Generation %s failed while finalizing timeout state",
                generation.id,
            )
    except asyncio.CancelledError:
        logger.warning("Generation %s was interrupted before completion", generation.id)
        try:
            await finalize_failure(
                error_message=INTERRUPTED_GENERATION_ERROR,
                error_type=INTERRUPTED_GENERATION_ERROR_TYPE,
                error_code=INTERRUPTED_GENERATION_ERROR_CODE,
                generation_time_seconds=perf_counter() - started,
            )
        except Exception:
            logger.exception(
                "Generation %s failed while finalizing interrupted state",
                generation.id,
            )
    except Exception as exc:
        logger.exception("Generation %s failed", generation.id)
        classification = classify_generation_failure(exc)
        try:
            await finalize_failure(
                error_message=str(exc),
                error_type=classification.error_type,
                error_code=classification.error_code,
                generation_time_seconds=perf_counter() - started,
            )
        except Exception:
            logger.exception(
                "Generation %s failed while finalizing exception state",
                generation.id,
            )
    finally:
        try:
            await recorder.stop()
        except Exception:
            logger.exception(
                "Generation %s failed while stopping the diagnostics recorder",
                generation.id,
            )
        clear_node_attempts(generation.id)
        try:
            await report_repo.cleanup_tmp(generation.id)
        except Exception:
            logger.exception(
                "Generation %s failed while cleaning report temp files",
                generation.id,
            )
        try:
            current = await gen_repo.find_by_id(generation.id)
            if current is not None and current.status in {"pending", "running"}:
                logger.error(
                    "Generation %s ended without completion; forcing orphan failure",
                    generation.id,
                )
                document = await _persist_failed_generation_state(
                    generation=generation,
                    gen_repo=gen_repo,
                    document_repo=document_repo,
                    document=document,
                    error_message=_ORPHANED_GENERATION_ERROR_MESSAGE,
                    error_type="runtime_error",
                    error_code=_ORPHANED_GENERATION_ERROR_CODE,
                    generation_time_seconds=perf_counter() - started,
                )
                await _save_report_snapshot_with_timeout(
                    report_repo=report_repo,
                    generation_id=generation.id,
                    report=recorder.build_failure_snapshot(
                        error=_ORPHANED_GENERATION_ERROR_MESSAGE,
                        generation_time_seconds=perf_counter() - started,
                    ),
                    phase="orphaned_fallback",
                )
                event_bus.publish(
                    generation.id,
                    _error_event(generation.id, _ORPHANED_GENERATION_ERROR_MESSAGE),
                )
                await report_repo.cleanup_tmp(generation.id)
        except Exception:
            logger.exception("Generation %s failed during orphan cleanup", generation.id)


def _validate_template_and_preset(template_id: str, preset_id: str) -> None:
    try:
        get_contract(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not validate_preset_for_template(template_id, preset_id):
        raise HTTPException(
            status_code=400,
            detail=f"Preset '{preset_id}' is not allowed for template '{template_id}'",
        )


@router.post("/generations", status_code=202, response_model=GenerationAcceptedResponse)
async def create_generation(
    req: GenerationRequest,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    report_repo: GenerationReportRepository = Depends(get_report_repository),
):
    _validate_template_and_preset(req.template_id, req.preset_id)
    profile = await profile_repo.find_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=409, detail="Complete your profile first")

    generation_id = str(uuid.uuid4())
    generation = Generation(
        id=generation_id,
        user_id=current_user.id,
        subject=req.subject,
        context=req.context,
        mode=req.mode,
        requested_template_id=req.template_id,
        requested_preset_id=req.preset_id,
        section_count=req.section_count,
    )
    initial_document = _initial_document(generation)
    document_path = await document_repo.save_document(initial_document)
    generation.document_path = document_path
    await gen_repo.create(generation)

    command = PipelineCommand(
        generation_id=generation_id,
        subject=req.subject,
        context=req.context,
        grade_band=_grade_band(profile),
        template_id=req.template_id,
        preset_id=req.preset_id,
        learner_fit="general",
        section_count=req.section_count,
        mode=req.mode.value,
    )

    asyncio.create_task(
        _run_generation_job(
            generation,
            command,
            gen_repo,
            document_repo,
            report_repo,
            initial_document,
        )
    )

    events_url, document_url, report_url = _generation_urls(generation_id)
    return GenerationAcceptedResponse(
        generation_id=generation_id,
        status="pending",
        mode=req.mode,
        events_url=events_url,
        document_url=document_url,
        report_url=report_url,
    )


@router.post(
    "/generations/{generation_id}/enhance",
    status_code=202,
    response_model=GenerationAcceptedResponse,
)
async def enhance_generation(
    generation_id: str,
    req: EnhanceGenerationRequest = Body(...),
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    report_repo: GenerationReportRepository = Depends(get_report_repository),
):
    if req.mode == GenerationMode.DRAFT:
        raise HTTPException(status_code=409, detail="Enhancement target must be balanced or strict")

    source_generation = await gen_repo.find_by_id(generation_id)
    if source_generation is None or source_generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if source_generation.mode != GenerationMode.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft generations can be enhanced")
    if source_generation.status != "completed" or not source_generation.document_path:
        raise HTTPException(status_code=409, detail="Draft is not ready for enhancement")

    source_document = await document_repo.load_document(source_generation.document_path)
    child_generation_id = str(uuid.uuid4())
    generation = Generation(
        id=child_generation_id,
        user_id=current_user.id,
        subject=source_generation.subject,
        context=source_generation.context,
        mode=req.mode,
        document_path=None,
        requested_template_id=source_generation.resolved_template_id
        or source_generation.requested_template_id,
        requested_preset_id=source_generation.resolved_preset_id
        or source_generation.requested_preset_id,
        section_count=source_generation.section_count,
        source_generation_id=generation_id,
    )
    initial_document = _initial_document(
        generation,
        section_manifest=list(source_document.section_manifest),
        sections=list(source_document.sections),
        status_value="running",
    )
    document_path = await document_repo.save_document(initial_document)
    generation.document_path = document_path
    await gen_repo.create(generation)

    command = PipelineCommand(
        generation_id=child_generation_id,
        subject=generation.subject,
        context=generation.context,
        grade_band=source_document.sections[0].header.grade_band
        if source_document.sections
        else "secondary",
        template_id=generation.requested_template_id,
        preset_id=generation.requested_preset_id,
        learner_fit="general",
        section_count=max(len(source_document.sections), 1),
        mode=req.mode.value,
        source_generation_id=generation_id,
        seed_document=SeedDocument(sections=source_document.sections, note=req.note),
    )

    asyncio.create_task(
        _run_generation_job(
            generation,
            command,
            gen_repo,
            document_repo,
            report_repo,
            initial_document,
        )
    )

    events_url, document_url, report_url = _generation_urls(child_generation_id)
    return GenerationAcceptedResponse(
        generation_id=child_generation_id,
        status="pending",
        mode=req.mode,
        source_generation_id=generation_id,
        events_url=events_url,
        document_url=document_url,
        report_url=report_url,
    )


@router.get("/generations")
async def list_generations(
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    limit: int = get_settings().default_pagination_limit,
    offset: int = 0,
):
    generations = await gen_repo.list_by_user(current_user.id, limit=limit, offset=offset)
    return [_history_item(generation) for generation in generations]


@router.get("/generations/{generation_id}")
async def get_generation_detail(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    return _detail_item(generation)


@router.get("/generations/{generation_id}/document")
async def get_generation_document(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if not generation.document_path:
        raise HTTPException(status_code=404, detail="Document not found")
    document = await document_repo.load_document(generation.document_path)
    return document.model_dump(mode="json", exclude_none=True)


@router.get("/generations/{generation_id}/report")
async def get_generation_report(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    report_repo: GenerationReportRepository = Depends(get_report_repository),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    try:
        report = await report_repo.load_report(generation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc
    return report.model_dump(mode="json", exclude_none=True)


@router.get("/generations/{generation_id}/events")
async def get_generation_events(
    generation_id: str,
    request: Request,
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    user_repo: UserRepository = Depends(get_user_repository),
):
    current_user = await _stream_user_from_token(request, jwt_handler, user_repo)
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")

    async def stream() -> AsyncIterator[str]:
        queue = event_bus.subscribe(generation_id)
        try:
            current = await gen_repo.find_by_id(generation_id)
            while not queue.empty():
                event = queue.get_nowait()
                yield _sse_payload(event)
                if event.get("type") in {"complete", "error"}:
                    return

            if current is not None and current.status == "completed":
                yield _sse_payload(_complete_event(generation_id).model_dump(mode="json", exclude_none=True))
                return
            if current is not None and current.status == "failed":
                yield _sse_payload(
                    _error_event(
                        generation_id,
                        current.error or "Generation failed",
                    ).model_dump(mode="json", exclude_none=True)
                )
                return

            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=_SSE_KEEPALIVE_TIMEOUT_SECONDS,
                    )
                except TimeoutError:
                    current = await gen_repo.find_by_id(generation_id)
                    if current is not None and current.status == "completed":
                        yield _sse_payload(
                            _complete_event(generation_id).model_dump(mode="json", exclude_none=True)
                        )
                        return
                    if current is not None and current.status == "failed":
                        yield _sse_payload(
                            _error_event(
                                generation_id,
                                current.error or "Generation failed",
                            ).model_dump(mode="json", exclude_none=True)
                        )
                        return
                    yield ": keep-alive\n\n"
                    continue

                yield _sse_payload(event)
                if event["type"] in {"complete", "error"}:
                    break
        finally:
            event_bus.unsubscribe(generation_id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
