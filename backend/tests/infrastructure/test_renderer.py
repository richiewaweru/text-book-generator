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

    def test_render_contains_style_tag(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "<style>" in html
        assert "--bg-primary" in html

    def test_render_contains_section_heading(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "Introduction to Variables" in html

    def test_render_contains_toc(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert 'class="sidebar"' in html
        assert "Table of Contents" in html

    def test_render_contains_hook(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "mystery box" in html

    def test_render_contains_diagram_svg(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "<svg" in html

    def test_render_contains_code_block(self, renderer, minimal_textbook):
        html = renderer.render(minimal_textbook)
        assert "x = 7" in html

    def test_render_no_sections(self, renderer, beginner_profile):
        textbook = RawTextbook(
            subject="empty",
            profile=beginner_profile,
            plan=SAMPLE_PLAN,
            sections=[],
        )
        html = renderer.render(textbook)
        assert "<!DOCTYPE html>" in html
