from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app import app
from core.database.models import GenerationModel, UserModel
from generation.recovery import reconcile_stale_generations


async def test_retired_routes_return_sanitized_410_without_reading_data() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        v3_response = await client.get("/api/v1/v3/generations/secret-id")
        units_response = await client.post("/api/v1/legacy-units/secret-id", json={"x": 1})

    assert v3_response.status_code == 410
    assert units_response.status_code == 410
    assert v3_response.json() == {
        "detail": {
            "code": "legacy_pipeline_retired",
            "message": "The Legacy Studio pipeline has been retired. Use the Units workflow.",
        }
    }
    assert units_response.json() == {
        "detail": {
            "code": "legacy_pipeline_retired",
            "message": "Legacy Units have been retired. Use the Units workflow.",
        }
    }


async def test_startup_recovery_reconciles_all_stale_rows_without_pipeline_imports(
    db_session_factory,
) -> None:
    async with db_session_factory() as session:
        session.add(UserModel(id="recovery-user", email="recovery@example.invalid", name="Recovery"))
        session.add_all(
            [
                GenerationModel(
                    id="recovery-complete",
                    user_id="recovery-user",
                    subject="Math",
                    context="completed snapshot",
                    status="running",
                    requested_template_id="guided-concept-path",
                    requested_preset_id="component-lectio",
                    chunked_state_json={"stage": "complete", "execution_started": True},
                    document_json={"version": 1, "id": "recovery-complete", "sections": []},
                ),
                GenerationModel(
                    id="recovery-interrupted",
                    user_id="recovery-user",
                    subject="Math",
                    context="partial snapshot",
                    status="running",
                    requested_template_id="guided-concept-path",
                    requested_preset_id="component-lectio",
                    chunked_state_json={"stage": "component_lectio_running"},
                    document_json={
                        "version": 1,
                        "id": "recovery-interrupted",
                        "progress": {"sections": {"intro": "ready"}},
                    },
                ),
            ]
        )
        await session.commit()

    assert await reconcile_stale_generations(db_session_factory) == 2

    async with db_session_factory() as session:
        complete = await session.get(GenerationModel, "recovery-complete")
        interrupted = await session.get(GenerationModel, "recovery-interrupted")

    assert complete is not None
    assert complete.status == "completed"
    assert complete.error_code is None
    assert complete.chunked_state_json["stage"] == "complete"
    assert interrupted is not None
    assert interrupted.status == "failed"
    assert interrupted.error_code == "generation_interrupted_by_restart"
    assert interrupted.chunked_state_json["stage"] == "assembly_blocked"

