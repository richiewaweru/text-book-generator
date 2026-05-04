"""Prompt templates for V3 Studio LLM steps."""

import json
from functools import lru_cache
from pathlib import Path

from pipeline.contracts import get_manifest

SIGNAL_SYSTEM = """You extract structured teaching signals from a short teacher brief.
Infer topic, subtopic, prior knowledge, learner needs, teacher goal, and resource type.
resource_type must be one of: lesson, mini_booklet (default lesson).
missing_signals lists signal dimensions still uncertain (max 5 short phrases).
confidence reflects how complete the brief was."""

CLARIFY_SYSTEM = """You write at most 2 short clarification questions for the teacher.
Each question has question text, reason why you're asking, and optional=true only if skippable.
Return fewer questions if signals are already strong."""

ADJUST_SYSTEM = """You revise the given ProductionBlueprint JSON according to the teacher's plain-language instruction.
Preserve IDs where possible; keep schema valid. Output the full revised blueprint."""


@lru_cache(maxsize=1)
def _manifest_block() -> str:
    """Extract planning-relevant manifest data for guided-concept-path."""
    manifest = get_manifest()
    contract = _load_guided_concept_contract()
    always_present = set(contract.get("always_present", []))
    available = set(contract.get("available_components", []))
    all_available = always_present | available
    lines: list[str] = [
        "TEMPLATE: guided-concept-path",
        "AVAILABLE COMPONENTS (use only these slugs):",
        f"REQUIRED in every section: {', '.join(sorted(always_present))}",
        "",
    ]
    phases_raw = manifest.get("phases")
    items: list[tuple[str, dict]]
    if isinstance(phases_raw, dict):

        def _phase_sort_key(k: str) -> tuple[int, str]:
            try:
                return (int(k), k)
            except ValueError:
                return (999, k)

        items = [(str(k), v) for k, v in phases_raw.items() if isinstance(v, dict)]
        items.sort(key=lambda kv: _phase_sort_key(kv[0]))
    elif isinstance(phases_raw, list):
        items = [(str(i), p) for i, p in enumerate(phases_raw) if isinstance(p, dict)]
    else:
        items = []

    for phase_key, phase_group in items:
        phase_num = phase_group.get("id", phase_key)
        phase_name = phase_group.get("name", "")
        lines.append(f"\nPhase {phase_num} — {phase_name}:")
        for component in phase_group.get("components") or []:
            if not isinstance(component, dict):
                continue
            cid = str(component.get("id", "") or "")
            section_field = str(component.get("section_field", "") or "—")
            role = str(component.get("role", "") or "")
            cognitive_job = str(component.get("cognitive_job", "") or "")
            if not cid or cid not in all_available:
                continue
            required_tag = " [REQUIRED]" if cid in always_present else ""
            lines.append(
                f"  {cid} [{section_field}]{required_tag}: {role} — {cognitive_job}"
            )
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _load_guided_concept_contract() -> dict:
    path = Path(__file__).parents[3] / "contracts" / "guided-concept-path.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_architect_system_prompt() -> str:
    """System prompt for the lesson architect, including live Lectio manifest and lenses."""
    from generation.v3_lenses.loader import format_lenses_for_prompt

    contract = _load_guided_concept_contract()
    component_budget = contract.get("component_budget", {})
    max_per_section = contract.get("max_per_section", {})
    manifest_block = _manifest_block()
    lenses_block = format_lenses_for_prompt()
    budget_lines = [f"  {slug}: max {limit}" for slug, limit in component_budget.items()]
    section_lines = [
        f"  {slug}: max {limit} per section"
        for slug, limit in max_per_section.items()
    ]
    budget_rules = (
        "\nCOMPONENT BUDGETS (max across entire lesson):\n" + "\n".join(budget_lines)
        if budget_lines
        else ""
    )
    section_rules = (
        "\nPER-SECTION LIMITS:\n" + "\n".join(section_lines) if section_lines else ""
    )
    return f"""You are a lesson architect. Output ONLY a valid ProductionBlueprint matching the schema.

{manifest_block}

CONSTRAINT: Each section_field (shown in brackets above) may appear at
most once per section. Never plan two components with the same
section_field in the same section.
{budget_rules}{section_rules}

{lenses_block}

Rules:
- Only use component slugs from the component list above. Never invent new slugs.
- metadata: version "3.0", title, subject (from teacher subject)
- lesson: lesson_mode first_exposure|consolidation|repair|retrieval|transfer, resource_type lesson|mini_booklet
- applied_lenses: min 1 lens with lens_id and effects (non-empty strings); choose lens_ids from the pedagogical lenses section where possible
- voice: register (simple|balanced|formal etc), optional tone
- anchor: reuse_scope string
- sections: min 1, each section_id, title, role, visual_required bool,
  components min 1 with component slug from the list above and content_intent
- question_plan: min 1 items with question_id, section_id, temperature
  warm|medium|cold|transfer, prompt, expected_answer, diagram_required
- visual_strategy: visuals list (can match sections needing visuals)
- answer_key: style string (e.g. concise_steps, answers_only)
- teacher_materials, prior_knowledge lists allowed
Use sensible IDs like orient, model, practice, summary for sections when appropriate."""
