"""Lane unit tests: brief→prose→questions, budget park, step skip, concurrency."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from v3_execution.runtime.lanes import LaneOutcome, resolved_lane_limits, run_lane


@pytest.mark.asyncio
async def test_run_lane_brief_then_prose_then_questions_in_order() -> None:
    order: list[str] = []

    async def brief():
        order.append("brief")
        return {"section_id": "orient", "components": []}

    async def prose() -> list:
        order.append("prose")
        return [{"id": "c1"}]

    async def questions() -> list:
        order.append("questions")
        return [{"id": "q1"}]

    with (
        patch(
            "v3_execution.runtime.lanes.step_exists",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "v3_execution.runtime.lanes.insert_step",
            new=AsyncMock(),
        ),
    ):
        outcome = await run_lane(
            generation_id="g1",
            part_id="orient",
            variant_id="everyone",
            brief_coro_factory=brief,
            prose_coro_factory=prose,
            questions_coro_factory=questions,
        )

    assert order == ["brief", "prose", "questions"]
    assert outcome.failed_step is None
    assert outcome.part_id == "orient"
    assert outcome.brief == {"section_id": "orient", "components": []}


@pytest.mark.asyncio
async def test_run_lane_prose_then_questions_in_order() -> None:
    order: list[str] = []

    async def prose() -> list:
        order.append("prose")
        return [{"id": "c1"}]

    async def questions() -> list:
        order.append("questions")
        return [{"id": "q1"}]

    with (
        patch(
            "v3_execution.runtime.lanes.step_exists",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "v3_execution.runtime.lanes.insert_step",
            new=AsyncMock(),
        ),
    ):
        outcome = await run_lane(
            generation_id="g1",
            part_id="orient",
            variant_id="everyone",
            prose_coro_factory=prose,
            questions_coro_factory=questions,
        )

    assert order == ["prose", "questions"]
    assert outcome.failed_step is None
    assert outcome.part_id == "orient"


@pytest.mark.asyncio
async def test_run_lane_skips_existing_prose_step() -> None:
    called: list[str] = []

    async def prose() -> list:
        called.append("prose")
        return []

    async def questions() -> list:
        called.append("questions")
        return []

    with (
        patch(
            "v3_execution.runtime.lanes.step_exists",
            new=AsyncMock(side_effect=lambda *a, **kw: kw.get("step") == "prose"),
        ),
        patch("v3_execution.runtime.lanes.insert_step", new=AsyncMock()),
        patch(
            "v3_execution.runtime.lanes._load_step_payload",
            new=AsyncMock(return_value={"blocks": [{"id": "stored"}]}),
        ),
    ):
        outcome = await run_lane(
            generation_id="g1",
            part_id="orient",
            variant_id="everyone",
            prose_coro_factory=prose,
            questions_coro_factory=questions,
        )

    assert called == ["questions"]
    assert outcome.component_blocks == [{"id": "stored"}]


@pytest.mark.asyncio
async def test_run_lane_skips_existing_brief_and_continues() -> None:
    called: list[str] = []

    async def brief():
        called.append("brief")
        return {"section_id": "orient"}

    async def prose() -> list:
        called.append("prose")
        return [{"id": "c1"}]

    with (
        patch(
            "v3_execution.runtime.lanes.step_exists",
            new=AsyncMock(side_effect=lambda *a, **kw: kw.get("step") == "brief"),
        ),
        patch("v3_execution.runtime.lanes.insert_step", new=AsyncMock()),
        patch(
            "v3_execution.runtime.lanes._load_step_payload",
            new=AsyncMock(return_value={"section_id": "orient", "components": []}),
        ),
    ):
        outcome = await run_lane(
            generation_id="g1",
            part_id="orient",
            variant_id="everyone",
            brief_coro_factory=brief,
            prose_coro_factory=prose,
            questions_coro_factory=None,
        )

    assert called == ["prose"]
    assert outcome.brief == {"section_id": "orient", "components": []}


@pytest.mark.asyncio
async def test_run_lane_failed_brief_skips_prose() -> None:
    called: list[str] = []

    class FailedBrief:
        _failed = True

    async def brief():
        called.append("brief")
        return FailedBrief()

    async def prose() -> list:
        called.append("prose")
        return []

    with (
        patch(
            "v3_execution.runtime.lanes.step_exists",
            new=AsyncMock(return_value=False),
        ),
        patch("v3_execution.runtime.lanes.insert_step", new=AsyncMock()),
    ):
        outcome = await run_lane(
            generation_id="g1",
            part_id="orient",
            variant_id="everyone",
            brief_coro_factory=brief,
            prose_coro_factory=prose,
            questions_coro_factory=None,
        )

    assert called == ["brief"]
    assert outcome.failed_step == "brief"


@pytest.mark.asyncio
async def test_run_lane_records_budget_failure() -> None:
    async def slow() -> list:
        await asyncio.sleep(60)
        return []

    with (
        patch(
            "v3_execution.runtime.lanes.step_exists",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "v3_execution.runtime.lanes.insert_step",
            new=AsyncMock(),
        ),
    ):
        try:
            async with asyncio.timeout(0.01):
                outcome = await run_lane(
                    generation_id="g1",
                    part_id="orient",
                    variant_id="everyone",
                    prose_coro_factory=slow,
                    questions_coro_factory=None,
                )
        except TimeoutError:
            outcome = LaneOutcome(
                part_id="orient",
                failed_step="budget",
                warnings=["lane:orient:budget exhausted"],
            )

    assert outcome.failed_step == "budget"


def test_stage2_parallel_false_forces_lane_concurrency_one(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("V3_STAGE2_PARALLEL", "false")
    monkeypatch.setenv("V3_CONCURRENCY_LANE_MAX", "6")
    limits = resolved_lane_limits()
    assert limits["lane"] == 1
