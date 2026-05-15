from __future__ import annotations

import logging

from learning.models import PackGenerateResponse, PackLearningPlan

logger = logging.getLogger(__name__)


def _pack_context_prefix(
    *,
    plan: PackLearningPlan,
    job_type: str,
    resource_label: str,
    resource_order: int,
    total_resources: int,
    preceding_labels: list[str],
    following_labels: list[str],
    resource_purpose: str,
) -> str:
    lines = [
        f"Pack type: {job_type}",
        f"This resource: {resource_label} (resource {resource_order} of {total_resources})",
        f"Role in pack: {resource_purpose}",
    ]
    if preceding_labels:
        lines.append(f"Resources before this: {', '.join(preceding_labels)}")
        lines.append("Do not re-explain content already covered by preceding resources.")
    if following_labels:
        lines.append(f"Resources after this: {', '.join(following_labels)}")
    lines.extend(["", "Shared learning plan - all resources in this pack use this:"])
    lines.append(f"Objective: {plan.objective}")
    if plan.success_criteria:
        lines.append(f"Success criteria: {'; '.join(plan.success_criteria)}")
    if plan.prerequisite_skills:
        lines.append(f"Prerequisite skills: {'; '.join(plan.prerequisite_skills)}")
    if plan.likely_misconceptions:
        lines.append(f"Watch for: {'; '.join(plan.likely_misconceptions)}")
    if plan.shared_vocabulary:
        lines.append(f"Shared vocabulary: {', '.join(plan.shared_vocabulary)}")
    if plan.shared_examples:
        lines.append(f"Anchor examples: {'; '.join(plan.shared_examples)}")
    lines.append("")
    return "\n".join(lines)


async def start_pack(*args, **kwargs) -> PackGenerateResponse:
    raise RuntimeError("Learning pack generation used the removed V2 pipeline and is disabled until a V3-native runner is added.")
