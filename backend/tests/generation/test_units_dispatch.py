from __future__ import annotations

import asyncio

import pytest

from generation import units_dispatch


@pytest.mark.asyncio
async def test_units_dispatch_rejects_historical_unmarked_generation() -> None:
    with pytest.raises(ValueError, match="not admitted"):
        await units_dispatch.dispatch_units_generation(
            generation_id="generation-1", user_id="user-1", state={}
        )


@pytest.mark.asyncio
async def test_units_dispatch_starts_component_pipeline_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    async def fake_pipeline(*, generation_id: str) -> None:
        calls.append((generation_id, "user-2"))

    async def fake_start(generation_id: str, *, display_title: str | None = None) -> None:
        return None

    monkeypatch.setattr(units_dispatch, "launch_component_lectio", fake_pipeline)
    monkeypatch.setattr(units_dispatch, "persist_component_lectio_start", fake_start)
    state = {"control": {"pipeline": "component_lectio"}}
    await units_dispatch.dispatch_units_generation(
        generation_id="generation-2", user_id="user-2", state=state
    )
    await units_dispatch.dispatch_units_generation(
        generation_id="generation-2", user_id="user-2", state=state
    )
    await asyncio.sleep(0)
    assert calls == [("generation-2", "user-2")]
    units_dispatch._tasks.clear()


@pytest.mark.asyncio
async def test_units_wrapper_persists_failure_after_launch_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors: list[str] = []

    async def fail_launch(*, generation_id: str) -> None:
        raise RuntimeError("provider detail must not be logged")

    async def record_failure(generation_id: str, exc: BaseException) -> None:
        errors.append(f"{generation_id}:{type(exc).__name__}")

    monkeypatch.setattr(units_dispatch, "launch_component_lectio", fail_launch)
    monkeypatch.setattr(units_dispatch, "persist_component_lectio_failure", record_failure)
    await units_dispatch._run_units_generation("generation-failed")
    assert errors == ["generation-failed:RuntimeError"]
