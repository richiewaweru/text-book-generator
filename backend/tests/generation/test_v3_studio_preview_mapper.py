from __future__ import annotations

import json
from pathlib import Path

import pytest

from v3_blueprint.models import ProductionBlueprint

from generation.v3_studio.preview_mapper import blueprint_to_preview_dto


def _example_bp(name: str) -> ProductionBlueprint:
    raw = Path(__file__).resolve().parents[2] / "src" / "v3_blueprint" / "examples" / name
    return ProductionBlueprint.model_validate(json.loads(raw.read_text(encoding="utf-8")))


def test_blueprint_to_preview_dto_shape() -> None:
    bp = _example_bp("amara_compound_area.json")
    dto = blueprint_to_preview_dto(blueprint_id="bid-test", blueprint=bp, template_id="diagram-led")
    assert dto.blueprint_id == "bid-test"
    assert dto.title == bp.metadata.title
    assert dto.section_plan
    assert dto.question_plan
    assert all(sec.components for sec in dto.section_plan)
    for sec in dto.section_plan:
        for comp in sec.components:
            assert comp.teacher_label
            assert comp.component_id


@pytest.mark.asyncio
async def test_v3_studio_router_import() -> None:
    from generation.v3_studio.router import v3_studio_router

    assert v3_studio_router.prefix == "/v3"
