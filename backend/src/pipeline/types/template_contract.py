"""
pipeline.types.template_contract

The subset of Lectio's TemplateContract that the pipeline needs.
Read from backend/contracts/{template_id}.json — produced by
npm run export-contracts in the Lectio library.
"""

from __future__ import annotations

from pydantic import BaseModel


class GenerationGuidance(BaseModel):
    tone: str
    pacing: str
    chunking: str
    emphasis: str
    avoid: list[str]


class TemplateContractSummary(BaseModel):
    id: str
    name: str
    family: str
    intent: str
    tagline: str
    lesson_flow: list[str]
    required_components: list[str]
    optional_components: list[str]
    default_behaviours: dict[str, str]
    generation_guidance: GenerationGuidance
    best_for: list[str]
    not_ideal_for: list[str]
    learner_fit: list[str]
    subjects: list[str]
    interaction_level: str
    allowed_presets: list[str] = []


class TemplatePresetSummary(BaseModel):
    id: str
    name: str
    palette: str
    typography: str
    density: str
    surface_style: str
