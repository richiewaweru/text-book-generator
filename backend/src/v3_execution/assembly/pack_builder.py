from __future__ import annotations

from v3_blueprint.models import ProductionBlueprint
from v3_execution.models import DraftPack, GeneratedAnswerKeyBlock


class V3PackBuilder:
    def build(
        self,
        *,
        blueprint: ProductionBlueprint,
        generation_id: str,
        blueprint_id: str,
        template_id: str,
        sections: list[dict],
        answer_key: GeneratedAnswerKeyBlock | None,
        warnings: list[str],
        failed_reason: str | None = None,
    ) -> DraftPack:
        lifecycle = "failed" if failed_reason else ("partial" if warnings else "draft_ready")
        if failed_reason:
            warnings = [*warnings, failed_reason]

        return DraftPack(
            generation_id=generation_id,
            blueprint_id=blueprint_id,
            template_id=template_id,
            subject=blueprint.metadata.subject,
            status=lifecycle,  # type: ignore[arg-type]
            sections=sections,
            answer_key=answer_key,
            warnings=warnings,
        )


__all__ = ["V3PackBuilder"]
