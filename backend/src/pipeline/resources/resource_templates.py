from __future__ import annotations

from pydantic import BaseModel, Field

from pipeline.types.teacher_brief import (
    TeacherBriefDepth,
    TeacherBriefOutcome,
    TeacherBriefResourceType,
)


class ResourceDepthLimit(BaseModel):
    min_components: int
    max_components: int
    target_time_minutes: str
    question_count_range: str | None = None


class ResourceVisualPolicy(BaseModel):
    max_visuals_by_depth: dict[TeacherBriefDepth, int]
    allow_diagrams: bool
    allow_images: bool


class ResourceTextPolicy(BaseModel):
    density: str
    max_reading_load: str


class ResourceTemplate(BaseModel):
    id: TeacherBriefResourceType
    label: str
    description: str
    best_for: list[str] = Field(default_factory=list)
    not_for: list[str] = Field(default_factory=list)
    allowed_outcomes: list[TeacherBriefOutcome] = Field(default_factory=list)
    depth_limits: dict[TeacherBriefDepth, ResourceDepthLimit]
    required_obligations: list[str] = Field(default_factory=list)
    recommended_component_roles: list[str] = Field(default_factory=list)
    optional_component_roles: list[str] = Field(default_factory=list)
    forbidden_component_roles: list[str] = Field(default_factory=list)
    visual_policy: ResourceVisualPolicy
    text_policy: ResourceTextPolicy
    validation_rules: list[str] = Field(default_factory=list)


WORKSHEET_RESOURCE = ResourceTemplate(
    id="worksheet",
    label="Worksheet",
    description="A flexible handout with short instruction and student work.",
    best_for=[
        "classwork",
        "guided practice",
        "short independent work",
        "skill reinforcement",
        "mixed explanation and practice",
    ],
    not_for=["long-form instruction", "formal assessment", "multi-section booklet"],
    allowed_outcomes=[
        "understand",
        "practice",
        "review",
        "compare",
        "vocabulary",
        "assess",
    ],
    depth_limits={
        "quick": ResourceDepthLimit(
            min_components=2,
            max_components=3,
            target_time_minutes="5-10",
            question_count_range="2-4",
        ),
        "standard": ResourceDepthLimit(
            min_components=3,
            max_components=5,
            target_time_minutes="15-25",
            question_count_range="4-8",
        ),
        "deep": ResourceDepthLimit(
            min_components=5,
            max_components=7,
            target_time_minutes="30-45",
            question_count_range="8-12",
        ),
    },
    required_obligations=[
        "must include student-facing work",
        "must include either brief instruction, model, or prompt context",
        "must be usable without teacher explanation after distribution",
    ],
    recommended_component_roles=["explain", "model", "practice", "check"],
    optional_component_roles=["visualize", "vocabulary", "reflect", "challenge"],
    forbidden_component_roles=["long_reading_sequence"],
    visual_policy=ResourceVisualPolicy(
        max_visuals_by_depth={"quick": 1, "standard": 1, "deep": 2},
        allow_diagrams=True,
        allow_images=True,
    ),
    text_policy=ResourceTextPolicy(density="low", max_reading_load="moderate"),
    validation_rules=[
        "must not exceed max components for selected depth",
        "must contain at least one student action component",
        "must not become mostly reading unless intended_outcome is understand or review",
        "if intended_outcome is practice, must include practice or question role",
    ],
)

MINI_BOOKLET_RESOURCE = ResourceTemplate(
    id="mini_booklet",
    label="Mini Booklet",
    description="A guided multi-part resource for learning a topic step by step.",
    best_for=[
        "concept introduction",
        "guided independent learning",
        "short reading with checks",
        "multi-part explanation",
        "vocabulary-rich topics",
    ],
    not_for=["quick assessment", "pure drill practice", "single-page exit check"],
    allowed_outcomes=["understand", "review", "vocabulary", "compare", "practice"],
    depth_limits={
        "quick": ResourceDepthLimit(
            min_components=3,
            max_components=4,
            target_time_minutes="10-15",
            question_count_range="2-4",
        ),
        "standard": ResourceDepthLimit(
            min_components=5,
            max_components=7,
            target_time_minutes="25-40",
            question_count_range="4-8",
        ),
        "deep": ResourceDepthLimit(
            min_components=7,
            max_components=9,
            target_time_minutes="45-60",
            question_count_range="6-10",
        ),
    },
    required_obligations=[
        "must include a clear learning path",
        "must include explanation or reading content",
        "must include at least one understanding check",
        "must be understandable without a live teacher explanation",
    ],
    recommended_component_roles=[
        "introduce",
        "vocabulary",
        "explain",
        "visualize",
        "check",
        "reflect",
    ],
    optional_component_roles=["practice", "compare", "timeline", "challenge"],
    forbidden_component_roles=["formal_assessment_only"],
    visual_policy=ResourceVisualPolicy(
        max_visuals_by_depth={"quick": 1, "standard": 2, "deep": 3},
        allow_diagrams=True,
        allow_images=True,
    ),
    text_policy=ResourceTextPolicy(density="medium", max_reading_load="heavy"),
    validation_rules=[
        "must include an instructional sequence, not only questions",
        "must include at least one check for understanding",
        "must not exceed visual limit",
        "if learner_context indicates struggling readers, reduce reading load and increase scaffolding",
    ],
)

QUICK_EXPLAINER_RESOURCE = ResourceTemplate(
    id="quick_explainer",
    label="Quick Explainer",
    description="A concise explanation of one focused idea.",
    best_for=[
        "concept clarification",
        "short reference",
        "misconception repair",
        "simple explanation",
        "study support",
    ],
    not_for=["long lessons", "large practice sets", "formal assessment"],
    allowed_outcomes=["understand", "review", "vocabulary", "compare"],
    depth_limits={
        "quick": ResourceDepthLimit(
            min_components=1,
            max_components=2,
            target_time_minutes="3-5",
            question_count_range="0-2",
        ),
        "standard": ResourceDepthLimit(
            min_components=2,
            max_components=4,
            target_time_minutes="5-10",
            question_count_range="1-3",
        ),
        "deep": ResourceDepthLimit(
            min_components=3,
            max_components=5,
            target_time_minutes="10-15",
            question_count_range="2-4",
        ),
    },
    required_obligations=[
        "must explain one focused subtopic",
        "must be concise",
        "must include either an example, analogy, or quick check unless depth is quick",
    ],
    recommended_component_roles=["explain", "example", "check"],
    optional_component_roles=["visualize", "vocabulary", "analogy", "misconception"],
    forbidden_component_roles=["large_practice_set", "long_reading_sequence"],
    visual_policy=ResourceVisualPolicy(
        max_visuals_by_depth={"quick": 1, "standard": 1, "deep": 1},
        allow_diagrams=True,
        allow_images=True,
    ),
    text_policy=ResourceTextPolicy(density="low", max_reading_load="light"),
    validation_rules=[
        "must stay focused on one subtopic",
        "must not include more than one major explanation chain",
        "must not become a worksheet unless resource_type is changed",
        "must avoid excessive practice items",
    ],
)

PRACTICE_SET_RESOURCE = ResourceTemplate(
    id="practice_set",
    label="Practice Set",
    description="A focused set of practice items for building fluency or skill confidence.",
    best_for=[
        "skill repetition",
        "fluency building",
        "homework practice",
        "review drills",
        "procedural confidence",
    ],
    not_for=["new concept teaching", "long readings", "formal assessment only"],
    allowed_outcomes=["practice", "review", "vocabulary", "assess"],
    depth_limits={
        "quick": ResourceDepthLimit(
            min_components=1,
            max_components=2,
            target_time_minutes="5-10",
            question_count_range="4-6",
        ),
        "standard": ResourceDepthLimit(
            min_components=2,
            max_components=4,
            target_time_minutes="15-25",
            question_count_range="8-12",
        ),
        "deep": ResourceDepthLimit(
            min_components=3,
            max_components=5,
            target_time_minutes="30-45",
            question_count_range="12-20",
        ),
    },
    required_obligations=[
        "must include multiple student practice items",
        "must stay focused on the selected subtopic",
        "must include enough variation to reveal understanding",
    ],
    recommended_component_roles=["model", "practice", "answer_check"],
    optional_component_roles=["hint", "challenge", "vocabulary", "reflection"],
    forbidden_component_roles=["long_explanation", "long_reading_sequence"],
    visual_policy=ResourceVisualPolicy(
        max_visuals_by_depth={"quick": 0, "standard": 1, "deep": 1},
        allow_diagrams=True,
        allow_images=False,
    ),
    text_policy=ResourceTextPolicy(density="low", max_reading_load="light"),
    validation_rules=[
        "must contain practice role",
        "must prioritize student work over explanation",
        "must not include excessive reading",
        "if supports include worked_examples, include at most one model before practice",
    ],
)

EXIT_TICKET_RESOURCE = ResourceTemplate(
    id="exit_ticket",
    label="Exit Ticket",
    description="A very short check for understanding at the end of a lesson.",
    best_for=[
        "formative assessment",
        "end-of-lesson check",
        "misconception detection",
        "quick reflection",
    ],
    not_for=["new instruction", "extended practice", "deep explanation", "long assessment"],
    allowed_outcomes=["assess", "review", "practice"],
    depth_limits={
        "quick": ResourceDepthLimit(
            min_components=1,
            max_components=1,
            target_time_minutes="2-5",
            question_count_range="1-2",
        ),
        "standard": ResourceDepthLimit(
            min_components=1,
            max_components=2,
            target_time_minutes="5-8",
            question_count_range="2-3",
        ),
        "deep": ResourceDepthLimit(
            min_components=2,
            max_components=3,
            target_time_minutes="8-12",
            question_count_range="3-4",
        ),
    },
    required_obligations=[
        "must be short",
        "must reveal whether the student understood the selected subtopic",
        "must include at least one response item",
    ],
    recommended_component_roles=["check", "reflect"],
    optional_component_roles=["challenge", "self_assess"],
    forbidden_component_roles=[
        "long_explanation",
        "long_reading_sequence",
        "worked_example_sequence",
    ],
    visual_policy=ResourceVisualPolicy(
        max_visuals_by_depth={"quick": 0, "standard": 0, "deep": 1},
        allow_diagrams=True,
        allow_images=False,
    ),
    text_policy=ResourceTextPolicy(density="low", max_reading_load="light"),
    validation_rules=[
        "must not include teaching sequence",
        "must not exceed max question count for depth",
        "must fit on a small handout or screen",
        "if supports include worked_examples, warn and omit unless resource type changes",
    ],
)

QUIZ_RESOURCE = ResourceTemplate(
    id="quiz",
    label="Quiz",
    description="A focused assessment with questions that measure understanding or skill mastery.",
    best_for=["formal assessment", "mastery check", "review quiz", "mixed question assessment"],
    not_for=["new instruction", "guided practice", "long explanation", "student reference"],
    allowed_outcomes=["assess", "review", "vocabulary", "practice"],
    depth_limits={
        "quick": ResourceDepthLimit(
            min_components=1,
            max_components=2,
            target_time_minutes="5-10",
            question_count_range="3-5",
        ),
        "standard": ResourceDepthLimit(
            min_components=2,
            max_components=3,
            target_time_minutes="10-20",
            question_count_range="6-10",
        ),
        "deep": ResourceDepthLimit(
            min_components=3,
            max_components=5,
            target_time_minutes="20-35",
            question_count_range="10-15",
        ),
    },
    required_obligations=[
        "must include assessable questions",
        "must align all questions to selected subtopic",
        "must produce evidence of understanding",
        "should include answer key unless disabled",
    ],
    recommended_component_roles=["question_set", "short_response", "answer_key"],
    optional_component_roles=["rubric", "visual_prompt", "vocabulary"],
    forbidden_component_roles=[
        "long_explanation",
        "worked_example_sequence",
        "guided_teaching_sequence",
    ],
    visual_policy=ResourceVisualPolicy(
        max_visuals_by_depth={"quick": 0, "standard": 1, "deep": 1},
        allow_diagrams=True,
        allow_images=True,
    ),
    text_policy=ResourceTextPolicy(density="low", max_reading_load="moderate"),
    validation_rules=[
        "must contain question_set or equivalent assessment role",
        "must not teach before assessing unless resource type changes",
        "must include answer key when requested by teacher or default assessment setting",
        "question count must match selected depth",
    ],
)

RESOURCE_TEMPLATES = [
    WORKSHEET_RESOURCE,
    MINI_BOOKLET_RESOURCE,
    QUICK_EXPLAINER_RESOURCE,
    PRACTICE_SET_RESOURCE,
    EXIT_TICKET_RESOURCE,
    QUIZ_RESOURCE,
]

RESOURCE_TEMPLATE_REGISTRY: dict[TeacherBriefResourceType, ResourceTemplate] = {
    template.id: template for template in RESOURCE_TEMPLATES
}


def get_resource_template(resource_type: TeacherBriefResourceType) -> ResourceTemplate:
    return RESOURCE_TEMPLATE_REGISTRY[resource_type]


def get_resource_template_v2(resource_type: str):
    try:
        from resource_specs.loader import get_spec

        return get_spec(resource_type)
    except Exception:
        return get_resource_template(resource_type)
