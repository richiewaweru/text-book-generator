import json
from pathlib import Path
from typing import Any

import pytest

from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.entities.practice_problem import PracticeProblem
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan, SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.value_objects import SectionDepth
from textbook_agent.domain.ports.llm_provider import BaseProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Canned fixture data used by MockProvider
# ---------------------------------------------------------------------------

SAMPLE_SECTION_SPEC = SectionSpec(
    id="section_01",
    title="Introduction to Variables",
    learning_objective="Understand what a variable represents",
    prerequisite_ids=[],
    needs_diagram=True,
    needs_code=True,
    is_core=True,
    estimated_depth=SectionDepth.LIGHT,
)

SAMPLE_PLAN = CurriculumPlan(
    subject="algebra",
    total_sections=1,
    sections=[SAMPLE_SECTION_SPEC],
    reading_order=["section_01"],
)

SAMPLE_CONTENT = SectionContent(
    section_id="section_01",
    hook="Imagine you have a mystery box that can hold any number.",
    prerequisites_block="You should already be comfortable reading simple equations like 3 + 4 = 7.",
    plain_explanation="A variable is a name we give to a value we don't know yet.",
    formal_definition="A variable \\(x\\) is a symbol representing an element of a given set.",
    worked_example="If \\(x + 3 = 7\\), then \\(x = 4\\) because \\(4 + 3 = 7\\).",
    common_misconception="Variables are not always the letter x — any letter works.",
    practice_problems=[
        PracticeProblem(
            difficulty="warm",
            statement="If y + 2 = 5, what value must y have?",
            hint="Undo the +2 by doing the opposite operation.",
        ),
        PracticeProblem(
            difficulty="medium",
            statement="Write a variable equation for a box that holds an unknown number plus 6 and totals 10.",
            hint="Let one letter stand for the unknown amount first.",
        ),
        PracticeProblem(
            difficulty="cold",
            statement="Explain why m = 3 and 3 = m say the same thing about the variable m.",
            hint="Focus on what statement each equation makes about the relationship.",
        ),
    ],
    interview_anchor="If I changed the letter from x to n, what meaning would stay the same?",
    think_prompt="Pause and predict: what changes when the value changes, and what stays fixed?",
    connection_forward="Next we will see how variables combine in expressions.",
)

SAMPLE_DIAGRAM = SectionDiagram(
    section_id="section_01",
    svg_markup='<svg xmlns="http://www.w3.org/2000/svg" width="200" height="50" viewBox="0 0 200 50"><text x="10" y="30">x = ?</text></svg>',
    caption="A number line showing where x might live.",
    diagram_type="number_line",
)

SAMPLE_CODE = SectionCode(
    section_id="section_01",
    language="python",
    code="x = 7\nprint(x)",
    explanation="Assigns 7 to x and prints it.",
    expected_output="7",
)

SAMPLE_QUALITY_REPORT = QualityReport(passed=True, issues=[])


# Mapping from Pydantic model *type* to a canned instance
_MOCK_RESPONSES: dict[type, Any] = {
    CurriculumPlan: SAMPLE_PLAN,
    SectionContent: SAMPLE_CONTENT,
    SectionDiagram: SAMPLE_DIAGRAM,
    SectionCode: SAMPLE_CODE,
    QualityReport: SAMPLE_QUALITY_REPORT,
}


class MockProvider(BaseProvider):
    """Test-only provider that returns pre-fabricated Pydantic instances.

    Supports an optional *fail_n_times* counter: the first N calls raise
    ``RuntimeError`` so retry logic in ``PipelineNode.execute()`` can be
    verified.
    """

    def __init__(self, fail_n_times: int = 0) -> None:
        self._fail_n_times = fail_n_times
        self._call_count = 0

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> Any:
        self._call_count += 1
        if self._call_count <= self._fail_n_times:
            raise RuntimeError(f"MockProvider deliberate failure #{self._call_count}")

        if response_schema not in _MOCK_RESPONSES:
            raise ValueError(
                f"MockProvider has no canned response for {response_schema.__name__}"
            )
        return _MOCK_RESPONSES[response_schema]

    def name(self) -> str:
        return "mock-provider"

    @property
    def call_count(self) -> int:
        return self._call_count


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def beginner_profile() -> GenerationContext:
    data = json.loads((FIXTURES_DIR / "stem_beginner.json").read_text())
    return GenerationContext.model_validate(data)


@pytest.fixture
def intermediate_profile() -> GenerationContext:
    data = json.loads((FIXTURES_DIR / "stem_intermediate.json").read_text())
    return GenerationContext.model_validate(data)


@pytest.fixture
def advanced_profile() -> GenerationContext:
    data = json.loads((FIXTURES_DIR / "stem_advanced.json").read_text())
    return GenerationContext.model_validate(data)


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def sample_plan() -> CurriculumPlan:
    return SAMPLE_PLAN


@pytest.fixture
def sample_content() -> SectionContent:
    return SAMPLE_CONTENT


@pytest.fixture
def sample_diagram() -> SectionDiagram:
    return SAMPLE_DIAGRAM


@pytest.fixture
def sample_code() -> SectionCode:
    return SAMPLE_CODE
