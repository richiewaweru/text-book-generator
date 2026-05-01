from __future__ import annotations

from learning.models import PackLearningPlan
from learning.pack_runner import _pack_context_prefix


def test_pack_context_prefix_includes_position_and_shared_plan() -> None:
    result = _pack_context_prefix(
        plan=PackLearningPlan(
            objective="Students can calculate slope.",
            success_criteria=["Identifies rise and run"],
            prerequisite_skills=[],
            likely_misconceptions=["Confuses rise over run"],
            shared_vocabulary=["slope", "rise", "run"],
            shared_examples=["A ramp rising 3 over 4"],
        ),
        job_type="reteach",
        resource_label="Guided practice",
        resource_order=2,
        total_resources=3,
        preceding_labels=["Targeted re-explanation"],
        following_labels=["Misconception check"],
        resource_purpose="Practice the specific gap.",
    )
    assert "resource 2 of 3" in result
    assert "Do not re-explain" in result
    assert "slope" in result
    assert "A ramp rising 3 over 4" in result

