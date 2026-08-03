"""
Throwaway spike: generate two booklets from one skeleton with different learner profiles.

No schema changes. No group_id in src/. Delete after the experiment answers:
do two groups off one skeleton produce structurally different booklets, or just reworded ones?
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from resource_specs.loader import get_spec
from v3_blueprint.planning.structural_planner import _call_stage1b
from v3_blueprint.skeleton.baseline import build_baseline_skeleton


def _profile(label: str, **overrides: object) -> V3InputForm:
    base = dict(
        grade_level="Grade 5",
        subject="Mathematics",
        duration_minutes=30,
        resource_type="lesson",
        topic="equivalent fractions",
        outcome="Students can identify equivalent fractions.",
        struggle="",
        learner_level="on_grade",
        reading_level="on_grade",
        language_support="none",
        prior_knowledge_level="some_background",
    )
    base.update(overrides)
    form = V3InputForm(**base)  # type: ignore[arg-type]
    form.free_text = f"spike profile: {label}"
    return form


async def _run(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = get_spec("lesson")
    skeleton = build_baseline_skeleton(spec, "standard", active_supports=[])
    (out_dir / "shared_skeleton.json").write_text(
        skeleton.model_dump_json(indent=2),
        encoding="utf-8",
    )

    profiles = [
        ("language_support", _profile("language_support", language_support="many_ell", reading_level="below_grade")),
        ("extension", _profile("extension", learner_level="above_grade")),
    ]
    signals = V3SignalSummary(
        topic="equivalent fractions",
        teacher_goal="identify equivalent fractions",
        inferred_lesson_mode="first_exposure",
        lesson_mode_confidence="high",
    )
    resource_spec = {
        "resource_type": "lesson",
        "depth": "standard",
        "spec": spec.model_dump(mode="json"),
        "rendered": "",
    }

    for label, form in profiles:
        plan = await _call_stage1b(
            signals,
            form,
            resource_spec,
            skeleton,
            generation_id=f"spike-{label}",
        )
        (out_dir / f"plan_{label}.json").write_text(
            plan.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"wrote plan for {label}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("spike_two_group_out"),
        help="Directory for dumped artifacts",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.out))


if __name__ == "__main__":
    main()
