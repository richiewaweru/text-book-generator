from __future__ import annotations

from pipeline.types.section_content import SectionContent


def section_title(section: SectionContent, fallback: str | None = None) -> str:
    if section.header is not None and section.header.title.strip():
        return section.header.title.strip()
    if fallback and fallback.strip():
        return fallback.strip()
    if section.section_id.strip():
        return section.section_id.strip()
    return "Untitled section"


def hook_headline(section: SectionContent, fallback: str | None = None) -> str:
    if section.hook is not None and section.hook.headline.strip():
        return section.hook.headline.strip()
    return section_title(section, fallback=fallback)


def explanation_body(section: SectionContent) -> str:
    if section.explanation is not None and section.explanation.body.strip():
        return section.explanation.body.strip()
    if section.hook is not None and section.hook.body.strip():
        return section.hook.body.strip()
    return ""


def explanation_emphasis(section: SectionContent) -> list[str]:
    if section.explanation is None:
        return []
    return [item for item in section.explanation.emphasis if item]


def practice_problems(section: SectionContent) -> list:
    if section.practice is None:
        return []
    return list(section.practice.problems)
