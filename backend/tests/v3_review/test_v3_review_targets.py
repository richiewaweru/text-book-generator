from __future__ import annotations

from v3_review.models import ReviewIssue
from v3_review.targets import build_repair_targets


def test_visual_target_parsing_uses_section_and_no_visual_id() -> None:
    issues = [
        ReviewIssue(
            severity="blocking",
            category="missing_planned_content",
            message="missing visual",
            generated_ref="understand",
            suggested_repair_executor="visual_executor",
            repair_target_id="visual:understand",
        )
    ]

    targets = build_repair_targets(issues)

    assert len(targets) == 1
    assert targets[0].section_id == "understand"
    assert targets[0].visual_id is None
