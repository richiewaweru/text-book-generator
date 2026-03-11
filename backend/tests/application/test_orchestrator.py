import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textbook_agent.application.orchestrator import TextbookAgent
from textbook_agent.application.dtos.generation_request import GenerationResponse
from textbook_agent.infrastructure.repositories.file_textbook_repo import FileTextbookRepository
from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
from conftest import MockProvider


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

        output_file = Path(result.output_path)
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
