import pytest
from pydantic import ValidationError

from textbook_agent.domain.entities import (
    Generation,
    GenerationContext,
    PracticeProblem,
    CurriculumPlan,
    SectionSpec,
    SectionContent,
    SectionDiagram,
    SectionCode,
    QualityIssue,
    QualityReport,
)
from textbook_agent.domain.value_objects import Depth, NotationLanguage, SectionDepth


class TestGenerationContext:
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
            GenerationContext(
                subject="math", age=5, context="test", depth="standard", language="plain"
            )

    def test_rejects_invalid_age_high(self):
        with pytest.raises(ValidationError):
            GenerationContext(
                subject="math", age=100, context="test", depth="standard", language="plain"
            )

    def test_rejects_invalid_depth(self):
        with pytest.raises(ValidationError):
            GenerationContext(
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

    def test_rejects_inconsistent_reading_order(self):
        with pytest.raises(ValidationError):
            CurriculumPlan(
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
                reading_order=[],
            )


class TestSectionContent:
    def test_valid_content(self):
        content = SectionContent(
            section_id="section_01",
            hook="Imagine you have a mystery box...",
            prerequisites_block="Remember that an equation says two sides have the same value.",
            plain_explanation="A variable is a name for a value.",
            formal_definition="A variable x represents an unknown quantity.",
            worked_example="If x + 3 = 7, then x = 4.",
            common_misconception="Variables are not always 'x'.",
            practice_problems=[
                PracticeProblem(
                    difficulty="warm",
                    statement="Solve y + 1 = 4.",
                    hint="Subtract 1 from both sides.",
                ),
                PracticeProblem(
                    difficulty="medium",
                    statement="Write an equation for a mystery number plus 5 equals 9.",
                    hint="Choose a letter to stand in for the unknown number.",
                ),
                PracticeProblem(
                    difficulty="cold",
                    statement="Explain why x = 2 and 2 = x are equivalent.",
                    hint="Read both equations out loud in plain English.",
                ),
            ],
            interview_anchor="How would you explain a variable to someone who hates algebra jargon?",
            think_prompt="What role does the symbol play before you know its value?",
            connection_forward="Next we'll see how variables combine in expressions.",
        )
        assert content.section_id == "section_01"
        assert len(content.practice_problems) == 3

    def test_defaults_new_optional_rulebook_fields(self):
        content = SectionContent(
            section_id="section_01",
            hook="Hook",
            plain_explanation="Explanation",
            formal_definition="Definition",
            worked_example="Example",
            common_misconception="Misconception",
            connection_forward="Forward",
        )
        assert content.prerequisites_block == ""
        assert content.practice_problems == []
        assert content.interview_anchor == ""
        assert content.think_prompt == ""


class TestPracticeProblem:
    def test_valid_practice_problem(self):
        problem = PracticeProblem(
            difficulty="warm",
            statement="Solve x + 2 = 6.",
            hint="Subtract 2 from both sides.",
        )
        assert problem.difficulty == "warm"


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


class TestGeneration:
    def test_valid_generation(self):
        gen = Generation(
            id="gen-001",
            user_id="user-001",
            subject="algebra",
            context="I need help with variables",
        )
        assert gen.status == "pending"
        assert gen.output_path is None
        assert gen.error is None
        assert gen.quality_passed is None
        assert gen.generation_time_seconds is None
        assert gen.completed_at is None

    def test_completed_generation(self):
        gen = Generation(
            id="gen-002",
            user_id="user-001",
            subject="calculus",
            context="Integration basics",
            status="completed",
            output_path="/outputs/gen-002.html",
            quality_passed=True,
            generation_time_seconds=45.2,
        )
        assert gen.status == "completed"
        assert gen.quality_passed is True

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            Generation(
                id="gen-003",
                user_id="user-001",
                subject="math",
                status="unknown",
            )


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
                    check_source="mechanical",
                )
            ],
        )
        assert report.passed is False
        assert len(report.issues) == 1
        assert report.issues[0].check_source == "mechanical"
