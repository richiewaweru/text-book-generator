from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from core.health import routes as health_routes
from core.health.routes import DependencyStatus, GenerationSummary


class _FakeInspector:
    def __init__(self, present: bool) -> None:
        self.present = present

    def has_table(self, name: str) -> bool:
        assert name == "unit_capability_declarations"
        return self.present


class _FakeConnection:
    def __init__(self, present: bool) -> None:
        self.present = present

    async def run_sync(self, callback):
        return callback(self)


class _FakeSession:
    def __init__(self, present: bool) -> None:
        self.connection_value = _FakeConnection(present)

    async def connection(self) -> _FakeConnection:
        return self.connection_value


@pytest.mark.parametrize("present", [True, False])
async def test_component_lectio_schema_check_reports_table_presence(monkeypatch, present: bool) -> None:
    session = _FakeSession(present)

    @asynccontextmanager
    async def fake_session_factory():
        yield session

    monkeypatch.setattr(health_routes, "async_session_factory", fake_session_factory)
    monkeypatch.setattr(health_routes, "inspect", lambda _: _FakeInspector(present))

    result = await health_routes._check_component_lectio_schema()

    assert result.name == "component_lectio_schema"
    assert result.status == ("ok" if present else "unavailable")
    if not present:
        assert "unit_capability_declarations" in (result.detail or "")


async def test_ready_is_unavailable_when_component_lectio_schema_is_missing(monkeypatch) -> None:
    async def ok_database() -> DependencyStatus:
        return DependencyStatus(name="postgres", status="ok")

    async def missing_schema() -> DependencyStatus:
        return DependencyStatus(
            name="component_lectio_schema",
            status="unavailable",
            detail="Required table unit_capability_declarations is missing",
        )

    async def ok_dependency() -> DependencyStatus:
        return DependencyStatus(name="test", status="ok")

    async def summary() -> GenerationSummary:
        return GenerationSummary(running=0, pending=0, failed_last_hour=0, completed_last_hour=0)

    monkeypatch.setattr(health_routes, "_check_database", ok_database)
    monkeypatch.setattr(health_routes, "_check_component_lectio_schema", missing_schema)
    monkeypatch.setattr(health_routes, "_check_event_bus", ok_dependency)
    monkeypatch.setattr(health_routes, "_check_playwright_runtime", ok_dependency)
    monkeypatch.setattr(health_routes, "_check_pdf_temp_dir", ok_dependency)
    monkeypatch.setattr(health_routes, "_get_generation_summary", summary)

    payload = await health_routes._build_readiness_payload(
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    )

    assert payload.status == "unavailable"
    schema = next(
        dependency
        for dependency in payload.dependencies
        if dependency.name == "component_lectio_schema"
    )
    assert schema.status == "unavailable"
