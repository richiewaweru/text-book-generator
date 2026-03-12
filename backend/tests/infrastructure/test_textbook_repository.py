from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.infrastructure.repositories.file_textbook_repo import (
    FileTextbookRepository,
)
from conftest import SAMPLE_CODE, SAMPLE_CONTENT, SAMPLE_DIAGRAM, SAMPLE_PLAN


async def test_save_returns_sanitized_relative_output_name(beginner_profile, tmp_path):
    repo = FileTextbookRepository(output_dir=str(tmp_path))
    textbook = RawTextbook(
        subject="Intro to Algebra!",
        profile=beginner_profile,
        plan=SAMPLE_PLAN,
        sections=[SAMPLE_CONTENT],
        diagrams=[SAMPLE_DIAGRAM],
        code_examples=[SAMPLE_CODE],
    )

    output_path = await repo.save(textbook, "<!DOCTYPE html><html></html>")

    assert output_path.endswith(".html")
    assert " " not in output_path
    assert "!" not in output_path
    assert repo.resolve_output_path(output_path).exists()


async def test_load_html_reads_saved_artifact(beginner_profile, tmp_path):
    repo = FileTextbookRepository(output_dir=str(tmp_path))
    textbook = RawTextbook(
        subject="algebra",
        profile=beginner_profile,
        plan=SAMPLE_PLAN,
        sections=[SAMPLE_CONTENT],
        diagrams=[SAMPLE_DIAGRAM],
        code_examples=[SAMPLE_CODE],
    )

    output_path = await repo.save(textbook, "<!DOCTYPE html><html><body>ok</body></html>")

    html = await repo.load_html(output_path)

    assert "<body>ok</body>" in html


async def test_resolve_output_path_rejects_escape(tmp_path):
    repo = FileTextbookRepository(output_dir=str(tmp_path))

    try:
        repo.resolve_output_path("../outside.html")
    except ValueError:
        return

    raise AssertionError("Expected resolve_output_path to reject paths outside the output dir")
