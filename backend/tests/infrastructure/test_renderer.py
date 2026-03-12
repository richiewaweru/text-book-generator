import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
from conftest import SAMPLE_PLAN, SAMPLE_CONTENT, SAMPLE_DIAGRAM, SAMPLE_CODE


@pytest.fixture
def renderer() -> HTMLRenderer:
    return HTMLRenderer()


@pytest.fixture
def minimal_textbook(beginner_profile) -> RawTextbook:
    return RawTextbook(
        subject="algebra",
        profile=beginner_profile,
        plan=SAMPLE_PLAN,
        sections=[SAMPLE_CONTENT],
        diagrams=[SAMPLE_DIAGRAM],
        code_examples=[SAMPLE_CODE],
    )


class TestHTMLRenderer:
    def test_render_returns_html_string(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_render_contains_rulebook_assets(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "fonts.googleapis.com" not in html
        assert "MathJax" not in html
        assert "<math" in html
        assert "@media print" in html
        assert "--surface: #141414;" in html

    def test_render_contains_sidebar_titles(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert 'class="sidebar"' in html
        assert "Introduction to Variables" in html
        assert "Textbook Outline" in html

    def test_render_contains_rulebook_blocks(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert 'class="callout hook"' in html
        assert 'class="callout def-box"' in html
        assert 'class="callout pitfall"' in html
        assert 'class="callout interview"' in html
        assert 'class="callout think"' in html
        assert 'class="practice-problems"' in html

    def test_render_contains_figure_and_code_shell(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "<figure" in html
        assert "Figure 1." in html
        assert 'class="code-wrap"' in html
        assert 'class="code-dots"' in html

    def test_render_escapes_non_svg_content(self, renderer, beginner_profile):
        content = SAMPLE_CONTENT.model_copy(
            update={
                "hook": "<script>alert('x')</script>",
                "plain_explanation": "A <b>bold</b> idea.",
            }
        )
        textbook = RawTextbook(
            subject="algebra",
            profile=beginner_profile,
            plan=SAMPLE_PLAN,
            sections=[content],
            diagrams=[SAMPLE_DIAGRAM],
            code_examples=[SAMPLE_CODE],
        )

        html = renderer.render(textbook)

        assert "&lt;script&gt;alert" in html
        assert "&lt;b&gt;bold&lt;/b&gt;" in html
        assert "<script>alert('x')</script>" not in html

    def test_render_contains_practice_problem_content(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "difficulty-warm" in html
        assert "Undo the +2" in html
        assert 'class="write-in-field"' in html

    def test_render_converts_latex_to_mathml(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert '<math xmlns="http://www.w3.org/1998/Math/MathML"' in html
        assert "<mi>x</mi>" in html

    def test_render_no_sections(self, renderer, beginner_profile):
        textbook = RawTextbook(
            subject="empty",
            profile=beginner_profile,
            plan=SAMPLE_PLAN,
            sections=[],
        )
        html = renderer.render(textbook)
        assert "<!DOCTYPE html>" in html
