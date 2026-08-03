from __future__ import annotations

from v3_blueprint.planning.models import (
    ComponentSlot,
    LessonIntent,
    LessonSkeleton,
    SectionPlan,
    SkeletonComponent,
    SkeletonSection,
    StructuralPlan,
    VoiceSpec,
    AnchorSpec,
)
from v3_blueprint.planning.validators import (
    validate_lesson_skeleton,
    validate_skeleton_conformance,
)


def _skeleton() -> LessonSkeleton:
    return LessonSkeleton(
        lesson_mode="first_exposure",
        sections=[
            SkeletonSection(
                id="orient",
                title="Orient",
                role="orient",
                visual_required=False,
                components=[SkeletonComponent(slug="hook-hero")],
            )
        ],
    )


def test_validate_lesson_skeleton_unknown_slug() -> None:
    skeleton = _skeleton()
    skeleton.sections[0].components[0] = SkeletonComponent(slug="not-a-real-slug")
    errors = validate_lesson_skeleton(skeleton, None)
    assert any("unknown slug" in e for e in errors)


def test_conformance_detects_reorder() -> None:
    skeleton = LessonSkeleton(
        lesson_mode="first_exposure",
        sections=[
            SkeletonSection(
                id="a",
                title="A",
                role="orient",
                visual_required=False,
                components=[SkeletonComponent(slug="hook-hero")],
            ),
            SkeletonSection(
                id="b",
                title="B",
                role="build",
                visual_required=False,
                components=[SkeletonComponent(slug="key-fact")],
            ),
        ],
    )
    plan = StructuralPlan(
        lesson_mode="first_exposure",
        lesson_intent=LessonIntent(goal="g" * 10, structure_rationale="r" * 10),
        anchor=AnchorSpec(example="anchor example here", reuse_scope="everywhere in lesson"),
        voice=VoiceSpec(register_name="simple", tone="encouraging"),
        prior_knowledge=[],
        sections=[
            SectionPlan(
                id="b",
                title="B",
                role="build",
                visual_required=False,
                transition_note=None,
                components=[ComponentSlot(slug="key-fact", purpose="p")],
            ),
            SectionPlan(
                id="a",
                title="A",
                role="orient",
                visual_required=False,
                transition_note="after",
                components=[ComponentSlot(slug="hook-hero", purpose="p")],
            ),
        ],
        question_plan=[],
        answer_key_style="brief_explanations",
    )
    errors = validate_skeleton_conformance(skeleton, plan)
    assert errors
