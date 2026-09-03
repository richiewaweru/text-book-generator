"""Casa flag-cutover acceptance gates (GENERATION_PIPELINE_DEFAULT)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from core.config import Settings
from core.database.models import GenerationModel, UserModel
from generation.pipeline_dispatch import (
    build_control_patch,
    persist_pipeline_identity,
    resolve_generation_pipeline,
    select_default_pipeline,
)
from generation.v3_studio.router import (
    _normalize_chunked_status,
    _run_component_lectio_pipeline,
)
from tests.v3_blueprint.planning.test_intent_plan import SUBJECT_FIXTURES, _intent_plan_for_subject
from v3_blueprint.planning.canonical_plan import build_canonical_execution_plan
from v3_blueprint.planning.models import intent_plan_to_structural_plan
from v3_blueprint.planning.persistence import insert_step, load_chunked_state, persist_chunked_state
from v3_blueprint.planning.work_orders import compile_exact_work_orders
from v3_execution.models import GeneratedComponentBlock


def _settings_env(monkeypatch, **extra: str) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-development-key-for-tests")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "http://127.0.0.1:5173")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./textbook_agent.db")
    for key, value in extra.items():
        monkeypatch.setenv(key, value)


async def _seed_generation(generation_id: str, *, pipeline: str | None = "component_lectio") -> None:
    from core.database.session import async_session_factory

    async with async_session_factory() as session:
        session.add(
            UserModel(
                id=f"user-{generation_id}",
                email=f"{generation_id}@example.com",
                name="Flag Cutover",
            )
        )
        session.add(
            GenerationModel(
                id=generation_id,
                user_id=f"user-{generation_id}",
                subject="Math",
                requested_template_id="guided-concept-path",
                requested_preset_id="default",
                status="running",
            )
        )
        await session.commit()
    patch: dict = {
        "stage": "awaiting_review",
        "execution_started": False,
        "failed_sections": [],
        "structural_plan": {},
        "context": {},
    }
    if pipeline is not None:
        patch.update(build_control_patch(pipeline))  # type: ignore[arg-type]
    await persist_chunked_state(generation_id, patch)


def test_gate1_default_selects_component_lectio(monkeypatch) -> None:
    _settings_env(monkeypatch)
    monkeypatch.delenv("GENERATION_PIPELINE_DEFAULT", raising=False)
    settings = Settings(_env_file=None)
    assert settings.generation_pipeline_default == "component_lectio"
    monkeypatch.setattr("generation.pipeline_dispatch.settings", settings)
    assert select_default_pipeline() == "component_lectio"


def test_gate2_rollback_env_selects_v3_studio(monkeypatch) -> None:
    _settings_env(monkeypatch, GENERATION_PIPELINE_DEFAULT="v3_studio")
    settings = Settings(_env_file=None)
    assert settings.generation_pipeline_default == "v3_studio"
    monkeypatch.setattr("generation.pipeline_dispatch.settings", settings)
    assert select_default_pipeline() == "v3_studio"


@pytest.mark.asyncio
async def test_gate3_pipeline_immutable_after_flag_flip(monkeypatch) -> None:
    _settings_env(monkeypatch, GENERATION_PIPELINE_DEFAULT="component_lectio")
    settings_a = Settings(_env_file=None)
    monkeypatch.setattr("generation.pipeline_dispatch.settings", settings_a)
    gen_a = f"gen-a-{uuid.uuid4().hex[:8]}"
    await _seed_generation(gen_a, pipeline=None)
    await persist_pipeline_identity(gen_a, select_default_pipeline())

    monkeypatch.setenv("GENERATION_PIPELINE_DEFAULT", "v3_studio")
    settings_b = Settings(_env_file=None)
    monkeypatch.setattr("generation.pipeline_dispatch.settings", settings_b)

    state_a = await load_chunked_state(gen_a)
    assert resolve_generation_pipeline(state_a, generation_id=gen_a) == "component_lectio"

    gen_b = f"gen-b-{uuid.uuid4().hex[:8]}"
    await _seed_generation(gen_b, pipeline=None)
    await persist_pipeline_identity(gen_b, select_default_pipeline())
    state_b = await load_chunked_state(gen_b)
    assert resolve_generation_pipeline(state_b, generation_id=gen_b) == "v3_studio"


@pytest.mark.asyncio
async def test_gate4_no_automatic_legacy_fallback_on_lectio_failure(monkeypatch) -> None:
    gen_id = f"gen-fail-{uuid.uuid4().hex[:8]}"
    await _seed_generation(gen_id, pipeline="component_lectio")
    intent = _intent_plan_for_subject(**SUBJECT_FIXTURES[0])
    plan = intent_plan_to_structural_plan(intent)
    await persist_chunked_state(
        gen_id,
        {
            "structural_plan": plan.model_dump(mode="json"),
            "stage": "awaiting_review",
            "context": {
                "signals": {
                    "topic": "ratios",
                    "teacher_goal": "understand ratios",
                    "inferred_lesson_mode": "first_exposure",
                    "lesson_mode_confidence": "high",
                },
                "form": {
                    "grade_level": "Grade 7",
                    "subject": "Math",
                    "duration_minutes": 45,
                    "topic": "ratios",
                    "outcome": "students can compare ratios",
                },
                "resource_spec": {"resource_type": "lesson"},
            },
        },
    )

    studio_calls: list[dict] = []

    async def fake_studio(**kwargs):
        studio_calls.append(kwargs)

    async def boom(**kwargs):
        raise RuntimeError("controlled lectio failure")

    monkeypatch.setattr(
        "generation.v3_studio.router._run_chunked_stage2_pipeline",
        fake_studio,
    )
    monkeypatch.setattr(
        "generation.v3_studio.router.run_component_lectio_execution",
        boom,
    )
    monkeypatch.setattr(
        "generation.v3_studio.router._chunked_emit_event",
        AsyncMock(),
    )

    await _run_component_lectio_pipeline(generation_id=gen_id, user_id=f"user-{gen_id}")
    assert studio_calls == []
    state = await load_chunked_state(gen_id)
    assert state.get("stage") == "assembly_blocked"
    assert resolve_generation_pipeline(state, generation_id=gen_id) == "component_lectio"
    assert "controlled lectio failure" in str(state.get("error") or "")


@pytest.mark.asyncio
async def test_gate5_real_executor_not_mock_writer(monkeypatch) -> None:
    from generation.component_lectio import service as lectio_service
    from generation.component_lectio import pipeline as mock_pipeline

    gen_id = f"gen-real-{uuid.uuid4().hex[:8]}"
    await _seed_generation(gen_id, pipeline="component_lectio")
    intent = _intent_plan_for_subject(**SUBJECT_FIXTURES[0])
    plan = intent_plan_to_structural_plan(intent)

    mock_calls: list[object] = []
    real_calls: list[object] = []

    def tracking_mock_writer(order):
        mock_calls.append(order)
        return mock_pipeline.mock_writer(order)

    async def fake_section_executor(work_order, emit, **kwargs):
        real_calls.append(work_order)
        blocks: list[GeneratedComponentBlock] = []
        for idx, component in enumerate(work_order.section.components):
            blocks.append(
                GeneratedComponentBlock(
                    block_id=f"{work_order.section.id}:{component.component_id}",
                    section_id=work_order.section.id,
                    component_id=component.component_id,
                    section_field=component.component_id,
                    position=idx,
                    data={"headline": "ok", "body": "ok"},
                    source_work_order_id=work_order.work_order_id,
                )
            )
        return blocks

    monkeypatch.setattr(mock_pipeline, "mock_writer", tracking_mock_writer)

    document = await lectio_service.run_component_lectio_execution(
        generation_id=gen_id,
        plan=plan,
        title="Ratios",
        section_executor=fake_section_executor,
    )
    assert real_calls, "expected real section executor to be invoked"
    assert mock_calls == [], "production path must not call mock_writer"
    assert document["schema"] == "LessonDocument"
    assert document["blocks"]


@pytest.mark.asyncio
async def test_gate6_exact_component_identity_preserved() -> None:
    from generation.component_lectio.service import adapt_exact_orders_to_section_work_orders

    intent = _intent_plan_for_subject(**SUBJECT_FIXTURES[0])
    plan = intent_plan_to_structural_plan(intent)
    canonical, filled = build_canonical_execution_plan(plan, generation_id="id-gate6")
    orders = compile_exact_work_orders(canonical, include_visual=False)
    assert orders
    sample = orders[0]
    section_orders = adapt_exact_orders_to_section_work_orders(
        orders,
        plan=filled,
        template_id="guided-concept-path",
    )
    matched = [
        component
        for section in section_orders
        for component in section.section.components
        if component.component_id == sample.locked_component_id
    ]
    assert matched
    assert sample.component_id == sample.locked_component_id
    assert sample.block_id
    assert sample.section_id


@pytest.mark.asyncio
async def test_gate7_durable_checkpoint_reload_from_db() -> None:
    from generation.component_lectio.service import (
        READY_STEP,
        reconstruct_checkpoint_store,
    )

    gen_id = f"gen-ckpt-{uuid.uuid4().hex[:8]}"
    await _seed_generation(gen_id, pipeline="component_lectio")
    await insert_step(
        gen_id,
        part_id="block-1",
        step=READY_STEP,
        payload={
            "block_id": "block-1",
            "plan_revision": 1,
            "plan_hash": "hash-a",
            "payload": {"content": {"ok": True}, "component_id": "hook-hero"},
        },
    )
    # Destroy/recreate store view by constructing a fresh CheckpointStore from DB.
    store = await reconstruct_checkpoint_store(
        gen_id,
        plan_revision=1,
        plan_hash="hash-a",
        desired_work=["block-1", "block-2"],
    )
    assert store.blocks["block-1"].state == "ready"
    assert store.blocks["block-1"].payload["component_id"] == "hook-hero"


@pytest.mark.asyncio
async def test_gate8_resume_skips_ready_blocks() -> None:
    from generation.component_lectio import service as lectio_service

    gen_id = f"gen-resume-{uuid.uuid4().hex[:8]}"
    await _seed_generation(gen_id, pipeline="component_lectio")
    intent = _intent_plan_for_subject(**SUBJECT_FIXTURES[0])
    plan = intent_plan_to_structural_plan(intent)
    canonical, _filled = build_canonical_execution_plan(plan, generation_id=gen_id)
    orders = compile_exact_work_orders(canonical, include_visual=False)
    assert len(orders) >= 2
    ready_ids = {orders[0].block_id, orders[-1].block_id}
    missing = [order for order in orders if order.block_id not in ready_ids]
    assert missing

    for block_id in ready_ids:
        await insert_step(
            gen_id,
            part_id=block_id,
            step=lectio_service.READY_STEP,
            payload={
                "block_id": block_id,
                "plan_revision": canonical.plan_revision,
                "plan_hash": canonical.plan_hash,
                "payload": {"content": {"pre": True}, "component_id": "x"},
            },
        )

    executed_components: list[str] = []

    async def scoped_executor(work_order, emit, **kwargs):
        blocks = []
        for idx, component in enumerate(work_order.section.components):
            executed_components.append(component.component_id)
            blocks.append(
                GeneratedComponentBlock(
                    block_id=f"{work_order.section.id}:{component.component_id}",
                    section_id=work_order.section.id,
                    component_id=component.component_id,
                    section_field=component.component_id,
                    position=idx,
                    data={"headline": "resume", "body": "ok"},
                    source_work_order_id=work_order.work_order_id,
                )
            )
        return blocks

    await lectio_service.run_component_lectio_execution(
        generation_id=gen_id,
        plan=plan,
        title="Resume",
        section_executor=scoped_executor,
    )
    missing_components = {order.component_id for order in missing}
    ready_components = {order.component_id for order in orders if order.block_id in ready_ids}
    assert missing_components.issubset(set(executed_components))
    assert ready_components.isdisjoint(set(executed_components))


@pytest.mark.asyncio
async def test_gate9_pipeline_marker_observable() -> None:
    gen_id = f"gen-obs-{uuid.uuid4().hex[:8]}"
    await _seed_generation(gen_id, pipeline="component_lectio")
    state = await load_chunked_state(gen_id)
    assert state["control"]["pipeline"] == "component_lectio"
    dto = _normalize_chunked_status(gen_id, state, {"status": "running"})
    assert dto.pipeline == "component_lectio"


def test_gate10_historical_unmarked_infers_v3_studio(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="generation.pipeline_dispatch"):
        resolved = resolve_generation_pipeline(
            {"stage": "complete"},
            generation_id="legacy-gen",
        )
    assert resolved == "v3_studio"
    assert any("generation_pipeline_inferred" in record.message for record in caplog.records)


def test_gate12_invalid_pipeline_fails_settings_validation(monkeypatch) -> None:
    _settings_env(monkeypatch, GENERATION_PIPELINE_DEFAULT="banana")
    with pytest.raises(ValidationError, match="GENERATION_PIPELINE_DEFAULT"):
        Settings(_env_file=None)


def test_gate13_studio_package_still_present() -> None:
    studio_root = Path(__file__).resolve().parents[2] / "src" / "generation" / "v3_studio"
    assert studio_root.is_dir()
    assert (studio_root / "router.py").is_file()


def test_gate14_service_does_not_import_mock_pipeline() -> None:
    service_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "generation"
        / "component_lectio"
        / "service.py"
    )
    source = service_path.read_text(encoding="utf-8")
    assert "from generation.component_lectio.pipeline" not in source
    assert "import mock_writer" not in source
    # Docstring may mention the mock path as a prohibition; imports must stay clear.
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        if '"""' in stripped and stripped.count('"""') >= 2:
            continue
        assert "mock_writer(" not in stripped
        assert "run_mocked_component_lectio_pipeline(" not in stripped
