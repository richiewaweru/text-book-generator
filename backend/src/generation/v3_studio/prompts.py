"""Prompt templates for V3 Studio LLM steps."""

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


def _format_manifest_for_prompt() -> str:
    """Format manifest.json into a compact component list for the architect."""
    manifest = get_manifest()
    lines: list[str] = [
        "Available Lectio components (use only these slugs as component ids in the blueprint):"
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
        lines.append(f"\n  Phase {phase_num} — {phase_name}:")
        for component in phase_group.get("components") or []:
            if not isinstance(component, dict):
                continue
            cid = str(component.get("id", "") or "")
            role = str(component.get("role", "") or "")
            cognitive_job = str(component.get("cognitive_job", "") or "")
            if not cid:
                continue
            suffix = f" [{cognitive_job}]" if cognitive_job else ""
            lines.append(f"    {cid}: {role}{suffix}")
    return "\n".join(lines)


def build_architect_system_prompt() -> str:
    """System prompt for the lesson architect, including live Lectio manifest and lenses."""
    from generation.v3_lenses.loader import format_lenses_for_prompt

    manifest_block = _format_manifest_for_prompt()
    lenses_block = format_lenses_for_prompt()
    return f"""You are a lesson architect. Output ONLY a valid ProductionBlueprint matching the schema.

{manifest_block}

{lenses_block}

Rules:
- Only use component slugs from the component list above. Never invent new slugs.
- metadata: version "3.0", title, subject (from teacher subject)
- lesson: lesson_mode first_exposure|consolidation|repair, resource_type lesson|mini_booklet
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
Use sensible IDs like orient, model, practice, summary for sections when appropriate.
Diagram-led templates favor concept_intro, worked_example, guided_questions, key_takeaways style components when those slugs appear in the list above."""
