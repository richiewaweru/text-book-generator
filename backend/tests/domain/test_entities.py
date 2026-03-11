import pytest
from pydantic import ValidationError

from textbook_agent.domain.entities import (
    LearnerProfile,
    CurriculumPlan,
    SectionSpec,
    SectionContent,
    SectionDiagram,
    SectionCode,
    QualityIssue,
    QualityReport,
)
from textbook_agent.domain.value_objects import Depth, NotationLanguage, SectionDepth


class TestLearnerProfile:
    def test_valid_profile(self, beginner_profile):
        assert beginner_profile.subject == "algebra"
        assert beginner_profile.age == 14
        assert beginner_profile.depth == Depth.SURVEY
        assert beginner_profile.language == NotationLanguage.PLAIN

    def test_all_fixtures_load(self, beginner_profile, intermediate_profile, advanced_profile):
        assert beginner_profile.depth == Depth.SURVEY
        assert intermediate_profile.depth == Depth.STANDARD
        assert advanced_profile.depth == Depth.DEEP

    def test_rejects_invalid_age_low(self):
        with pytest.raises(ValidationError):
            LearnerProfile(
                subject="math", age=5, context="test", depth="standard", language="plain"
            )

    def test_rejects_invalid_age_high(self):
        with pytest.raises(ValidationError):
            LearnerProfile(
                subject="math", age=100, context="test", depth="standard", language="plain"
            )

    def test_rejects_invalid_depth(self):
        with pytest.raises(ValidationError):
            LearnerProfile(
                subject="math", age=15, context="test", depth="invalid", language="plain"
            )


class TestSectionSpec:
    def test_valid_section_spec(self):
        spec = SectionSpec(
            id="section_01",
            title="Introduction to Variables",
            learning_objective="Understand what a variable represents",
            prerequisite_ids=[],
            needs_diagram=True,
            needs_code=False,
            is_core=True,
            estimated_depth=SectionDepth.LIGHT,
        )
        assert spec.id == "section_01"
        assert spec.is_core is True


class TestCurriculumPlan:
    def test_valid_plan(self):
        plan = CurriculumPlan(
            subject="algebra",
            total_sections=1,
            sections=[
                SectionSpec(
                    id="section_01",
                    title="Variables",
                    learning_objective="Learn variables",
                    estimated_depth=SectionDepth.LIGHT,
                )
            ],
            reading_order=["section_01"],
        )
        assert plan.total_sections == 1
        assert len(plan.sections) == 1


class TestSectionContent:
    def test_valid_content(self):
        content = SectionContent(
            section_id="section_01",
            hook="Imagine you have a mystery box...",
            plain_explanation="A variable is a name for a value.",
            formal_definition="A variable x represents an unknown quantity.",
            worked_example="If x + 3 = 7, then x = 4.",
            common_misconception="Variables are not always 'x'.",
            connection_forward="Next we'll see how variables combine in expressions.",
        )
        assert content.section_id == "section_01"


class TestSectionDiagram:
    def test_valid_diagram(self):
        diagram = SectionDiagram(
            section_id="section_01",
            svg_markup="<svg></svg>",
            caption="A number line showing variable placement",
            diagram_type="number_line",
        )
        assert diagram.diagram_type == "number_line"


class TestSectionCode:
    def test_valid_code(self):
        code = SectionCode(
            section_id="section_01",
            language="python",
            code="x = 7\nprint(x)",
            explanation="Assigns 7 to x and prints it",
            expected_output="7",
        )
        assert code.language == "python"


class TestQualityReport:
    def test_passing_report(self):
        report = QualityReport(passed=True)
        assert report.passed is True
        assert len(report.issues) == 0

    def test_failing_report(self):
        report = QualityReport(
            passed=False,
            issues=[
                QualityIssue(
                    section_id="section_03",
                    issue_type="missing_prerequisite",
                    description="References integration before it is introduced",
                    severity="error",
                )
            ],
        )
        assert report.passed is False
        assert len(report.issues) == 1
