import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textbook_agent.application.orchestrator import TextbookAgent
from textbook_agent.application.dtos.generation_request import GenerationResponse
from textbook_agent.domain.entities.quality_report import QualityIssue, QualityReport
from textbook_agent.infrastructure.repositories.file_textbook_repo import FileTextbookRepository
from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
from conftest import MockProvider, _MOCK_RESPONSES


class TestTextbookAgent:
    async def test_full_pipeline_with_mock_provider(self, beginner_profile, tmp_path):
        provider = MockProvider()
        repository = FileTextbookRepository(output_dir=str(tmp_path))
        renderer = HTMLRenderer()
        agent = TextbookAgent(
            provider=provider,
            repository=repository,
            renderer=renderer,
            quality_check_enabled=True,
        )

        result = await agent.generate(beginner_profile)

        assert isinstance(result, GenerationResponse)
        assert result.textbook_id
        assert result.output_path
        assert result.generation_time_seconds >= 0
        assert result.quality_report is not None
        assert result.quality_report.passed is True

        output_file = repository.resolve_output_path(result.output_path)
        assert output_file.exists()
        html = output_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html

    async def test_pipeline_without_quality_check(self, beginner_profile, tmp_path):
        provider = MockProvider()
        repository = FileTextbookRepository(output_dir=str(tmp_path))
        renderer = HTMLRenderer()
        agent = TextbookAgent(
            provider=provider,
            repository=repository,
            renderer=renderer,
            quality_check_enabled=False,
        )

        result = await agent.generate(beginner_profile)
        assert result.quality_report is None

    async def test_progress_callback_is_called(self, beginner_profile, tmp_path):
        provider = MockProvider()
        repository = FileTextbookRepository(output_dir=str(tmp_path))
        renderer = HTMLRenderer()
        progress_log: list[str] = []

        agent = TextbookAgent(
            provider=provider,
            repository=repository,
            renderer=renderer,
            quality_check_enabled=True,
            on_progress=progress_log.append,
        )

        await agent.generate(beginner_profile)

        assert "CurriculumPlanner" in progress_log
        assert "Assembler" in progress_log
        assert "QualityChecker" in progress_log
        assert "HTMLRenderer" in progress_log

    async def test_quality_rerun_triggers_on_failure(self, beginner_profile, tmp_path):
        """When QualityChecker fails first, orchestrator reruns flagged sections."""

        failing_report = QualityReport(
            passed=False,
            issues=[
                QualityIssue(
                    section_id="section_01",
                    issue_type="missing_prerequisite",
                    description="References concept not introduced",
                    severity="error",
                ),
            ],
        )
        passing_report = QualityReport(passed=True, issues=[])

        quality_call_count = 0

        class RerunMockProvider(MockProvider):
            def complete(
                self,
                system_prompt: str,
                user_prompt: str,
                response_schema: type,
                temperature: float = 0.3,
                max_tokens: int = 4096,
            ) -> Any:
                nonlocal quality_call_count
                if response_schema is QualityReport:
                    quality_call_count += 1
                    return failing_report if quality_call_count == 1 else passing_report
                return _MOCK_RESPONSES[response_schema]

        provider = RerunMockProvider()
        repository = FileTextbookRepository(output_dir=str(tmp_path))
        renderer = HTMLRenderer()
        progress_log: list[str] = []

        agent = TextbookAgent(
            provider=provider,
            repository=repository,
            renderer=renderer,
            quality_check_enabled=True,
            max_quality_reruns=2,
            on_progress=progress_log.append,
        )

        result = await agent.generate(beginner_profile)

        assert result.quality_reruns == 1
        assert result.quality_report is not None
        assert result.quality_report.passed is True
        assert quality_call_count == 2
        # Verify rerun progress was reported
        assert "ContentGenerator:section_01:rerun_1" in progress_log
        assert "Assembler:rerun_1" in progress_log
        assert "QualityChecker:rerun_1" in progress_log

    async def test_quality_rerun_capped_at_max(self, beginner_profile, tmp_path):
        """Reruns stop after max_quality_reruns even if still failing."""

        always_failing = QualityReport(
            passed=False,
            issues=[
                QualityIssue(
                    section_id="section_01",
                    issue_type="complexity_spike",
                    description="Difficulty spikes unexpectedly",
                    severity="error",
                ),
            ],
        )

        class AlwaysFailProvider(MockProvider):
            def complete(
                self,
                system_prompt: str,
                user_prompt: str,
                response_schema: type,
                temperature: float = 0.3,
                max_tokens: int = 4096,
            ) -> Any:
                if response_schema is QualityReport:
                    return always_failing
                return _MOCK_RESPONSES[response_schema]

        provider = AlwaysFailProvider()
        repository = FileTextbookRepository(output_dir=str(tmp_path))
        renderer = HTMLRenderer()

        agent = TextbookAgent(
            provider=provider,
            repository=repository,
            renderer=renderer,
            quality_check_enabled=True,
            max_quality_reruns=2,
        )

        result = await agent.generate(beginner_profile)

        assert result.quality_reruns == 2
        assert result.quality_report is not None
        assert result.quality_report.passed is False
