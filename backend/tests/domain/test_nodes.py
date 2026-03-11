import sys
from pathlib import Path

import pytest

# Allow direct import from tests root (for MockProvider and sample data)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.exceptions import PipelineError
from textbook_agent.domain.services.planner import CurriculumPlannerNode
from textbook_agent.domain.services.content_generator import (
    ContentGeneratorNode,
    ContentGeneratorInput,
)
from textbook_agent.domain.services.diagram_generator import (
    DiagramGeneratorNode,
    DiagramGeneratorInput,
)
from textbook_agent.domain.services.code_generator import (
    CodeGeneratorNode,
    CodeGeneratorInput,
)
from textbook_agent.domain.services.quality_checker import (
    QualityCheckerNode,
    QualityCheckerInput,
)
from textbook_agent.domain.services.assembler import AssemblerNode, AssemblerInput
from conftest import MockProvider, SAMPLE_SECTION_SPEC, SAMPLE_PLAN, SAMPLE_CONTENT


class TestCurriculumPlannerNode:
    async def test_returns_curriculum_plan(self, mock_provider, beginner_profile):
        node = CurriculumPlannerNode(provider=mock_provider)
        result = await node.execute(beginner_profile)
        assert isinstance(result, CurriculumPlan)
        assert result.subject == "algebra"

    async def test_retry_on_failure(self, beginner_profile):
        provider = MockProvider(fail_n_times=1)
        node = CurriculumPlannerNode(provider=provider)
        result = await node.execute(beginner_profile)
        assert isinstance(result, CurriculumPlan)
        assert provider.call_count == 2


class TestContentGeneratorNode:
    async def test_returns_section_content(self, mock_provider, beginner_profile):
        node = ContentGeneratorNode(provider=mock_provider)
        input_data = ContentGeneratorInput(
            section=SAMPLE_SECTION_SPEC,
            profile=beginner_profile,
        )
        result = await node.execute(input_data)
        assert isinstance(result, SectionContent)
        assert result.section_id == "section_01"


class TestDiagramGeneratorNode:
    async def test_returns_section_diagram(self, mock_provider):
        node = DiagramGeneratorNode(provider=mock_provider)
        input_data = DiagramGeneratorInput(
            section=SAMPLE_SECTION_SPEC,
            content=SAMPLE_CONTENT,
        )
        result = await node.execute(input_data)
        assert isinstance(result, SectionDiagram)
        assert result.section_id == "section_01"


class TestCodeGeneratorNode:
    async def test_returns_section_code(self, mock_provider):
        node = CodeGeneratorNode(provider=mock_provider)
        input_data = CodeGeneratorInput(
            section=SAMPLE_SECTION_SPEC,
            content=SAMPLE_CONTENT,
        )
        result = await node.execute(input_data)
        assert isinstance(result, SectionCode)
        assert result.section_id == "section_01"


class TestQualityCheckerNode:
    async def test_returns_quality_report(self, mock_provider, beginner_profile):
        node = QualityCheckerNode(provider=mock_provider)
        textbook = RawTextbook(
            subject="algebra",
            profile=beginner_profile,
            plan=SAMPLE_PLAN,
            sections=[SAMPLE_CONTENT],
        )
        input_data = QualityCheckerInput(textbook=textbook, plan=SAMPLE_PLAN)
        result = await node.execute(input_data)
        assert isinstance(result, QualityReport)
        assert result.passed is True


class TestAssemblerNode:
    async def test_assembles_textbook_in_reading_order(
        self, beginner_profile, sample_plan, sample_content, sample_diagram, sample_code
    ):
        node = AssemblerNode()
        input_data = AssemblerInput(
            profile=beginner_profile,
            plan=sample_plan,
            sections=[sample_content],
            diagrams=[sample_diagram],
            code_examples=[sample_code],
        )
        result = await node.execute(input_data)
        assert isinstance(result, RawTextbook)
        assert result.subject == "algebra"
        assert len(result.sections) == 1
        assert result.sections[0].section_id == "section_01"

    async def test_missing_section_raises(self, beginner_profile, sample_plan):
        node = AssemblerNode()
        input_data = AssemblerInput(
            profile=beginner_profile,
            plan=sample_plan,
            sections=[],
            diagrams=[],
            code_examples=[],
        )
        with pytest.raises(PipelineError, match="Missing content"):
            await node.execute(input_data)
