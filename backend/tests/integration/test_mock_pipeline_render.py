from typing import Any

from textbook_agent.application.orchestrator import TextbookAgent
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
from textbook_agent.infrastructure.repositories.file_textbook_repo import FileTextbookRepository
from conftest import MockProvider, SAMPLE_CONTENT, _MOCK_RESPONSES


class EscapingMockProvider(MockProvider):
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> Any:
        if response_schema is SectionContent:
            return SAMPLE_CONTENT.model_copy(
                update={
                    "hook": "<script>alert('x')</script>",
                    "think_prompt": "Pause and test whether <b>formatting</b> gets escaped.",
                }
            )
        if response_schema is QualityReport:
            return QualityReport(passed=True, issues=[])
        return _MOCK_RESPONSES[response_schema]


async def test_mock_pipeline_renders_rulebook_html(beginner_profile, tmp_path):
    repository = FileTextbookRepository(output_dir=str(tmp_path))
    agent = TextbookAgent(
        provider=EscapingMockProvider(),
        repository=repository,
        renderer=HTMLRenderer(),
        quality_check_enabled=True,
    )

    result = await agent.generate(beginner_profile)
    html = repository.resolve_output_path(result.output_path).read_text(encoding="utf-8")

    assert "<!DOCTYPE html>" in html
    assert "MathJax" not in html
    assert "<math" in html
    assert 'class="practice-problems"' in html
    assert 'class="callout interview"' in html
    assert 'class="callout think"' in html
    assert 'class="code-wrap"' in html
    assert "&lt;script&gt;alert" in html
    assert "&lt;b&gt;formatting&lt;/b&gt;" in html
