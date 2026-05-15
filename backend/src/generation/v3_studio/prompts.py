"""Prompt templates for V3 Studio LLM steps."""

from functools import lru_cache

from contracts.lectio import get_component_card, get_planner_index, get_template_contract

SIGNAL_SYSTEM = """You extract structured teaching signals from a structured teacher form.

The form already provides lesson_mode, learner_level, support_needs, prior_knowledge_level,
intended_outcome, grade_level, subject, duration_minutes, topic, and subtopics.

Do NOT re-infer these from free text. Read them directly from the form fields.

Your job:
- Confirm the teaching topic (short, specific).
- Optionally select ONE subtopic string (or null) if the form subtopics are empty or too broad.
- Summarise teacher_goal in one clear sentence.
- Set inferred_resource_type to one of:
    lesson          — default; full instructional lesson with explanation and practice
    mini_booklet    — compact guided learning students can follow step by step
    worksheet       — practice resource; concept has already been taught
    quiz            — formal assessment with scored questions
    exit_ticket     — short end-of-lesson check, 3–5 questions
    practice_set    — drill-style repetition, minimal explanation
    quick_explainer — focused concept clarification or reference card
  Default to lesson if the teacher's intent does not clearly match another type.
- Populate missing_signals ONLY if topic is genuinely ambiguous or contradictory.
"""

CLARIFY_SYSTEM = """You write at most 2 short clarification questions for the teacher.
Each question has question text, reason why you're asking, and optional=true only if skippable.

The form already includes lesson_mode, learner_level, reading_level, language_support,
prior_knowledge_level, intended_outcome, support_needs, and learning_preferences.
Do NOT ask about those.

Only ask if the topic is unclear, contradictory, or missing key details that block planning.
Return fewer questions (including zero) if signals are already strong.
"""

REASONING_SCAFFOLD = """
━━━ REASONING STEPS — work through these before writing any JSON ━━━━━━━━━━━━

Do not skip ahead. Each step locks a decision that the next step depends on.
Keep answers short. You are building toward the blueprint, not writing an essay.

STEP 1 — LEARNER CONTEXT
  Who is this class? What is their level and what are their main barriers?
  What does their support profile mean for content density and visual load?
  Does anything in their needs (EAL, low confidence, fragile prior knowledge)
  require a specific approach before you choose components?
  (Answer in 2–3 sentences. Be specific — "mixed class" is not an answer.)

STEP 2 — CONCEPT AND DIFFICULTY
  What is the core concept in one sentence?
  What is the single hardest step for this learner to understand?
  What misconception most commonly arises here, and does it need a pitfall section?
  (Answer in 3 sentences.)

STEP 2.5 — LENS SELECTION
  From the pedagogical lenses in your context, select 1–3 that fit this class.
  For each chosen lens, state: lens_id, why it fits (one sentence), and
  what specific effect it will have on your sequencing or component choices.
  Check conflicts_with — do not apply lenses that conflict with each other.
  (Answer as: lens_id → why → effect on plan.)

  Example:
    first_exposure → learner has no prior model → keep anchor constant across
                     all sections; warm questions only; model before practice
    eal           → multilingual class → definition-card before explanation-block;
                     label all diagram elements; no idiom in question stems

STEP 3 — RESOURCE STRUCTURE
  Read the RESOURCE SPEC in your context window.
  State: what is this resource type for, what is forbidden, what sections are required.
  If a section you wanted to plan is forbidden by the spec, remove it now.
  (Answer as: purpose / forbidden / required sections list.)

  This step is a gate. If you plan a component that the spec forbids,
  the output is wrong. Check forbidden_components before proceeding.

STEP 4 — TEACHING SEQUENCE
  Given the lesson_mode, learner_level, and the lens effects from Step 2.5,
  write the teaching sequence as an ordered list of 4–6 moves.
  Each move is one verb phrase: "Orient the learner to...", "Explain how to...",
  "Model with...", "Practice...".
  Apply lens effects here: if a lens says "lead with a worked example", put Model
  before Understand. If a lens says "define terms first", put Understand before
  Explain. The sequence should reflect how a good teacher would actually order this.
  (Answer as a numbered list.)

STEP 5 — COMPONENT MAPPING (phase-first)
  Map each sequence move to one component slug.
  Follow this order for every move:
    a. Name the pedagogical role of this move
       (orient / understand / model / practice / alert / visual / simulate)
    b. Find the phase in the AVAILABLE COMPONENTS that matches that role
    c. Choose the right component from that phase for this learner and context
    d. Check section_field — no two components with the same field in one section
  (Answer as: move → role → phase → slug [field].)

  Example:
    "Explain how to find equivalent fractions"
    → role: understand → Phase 2 — Understand
    → slug: explanation-block [explanation]

STEP 6 — VISUALS
  For each section, answer yes or no: does this concept require visual support here?
  Spatial and procedural steps usually need visuals.
  Definitions and pitfall warnings usually do not.
  Check resource spec visual policy — some resource types restrict visuals.
  (Answer as: section_id → yes/no, one word reason.)

STEP 7 — QUESTIONS
  Given the lesson_mode, what is the right difficulty progression?
  lesson_mode → allowed temperatures:
    first_exposure  → warm and medium only (no cold for below-average groups)
    consolidation   → start medium, reach cold and transfer
    repair          → warm only at first; cold only after pitfall is resolved
    retrieval       → cold and transfer; no warm unless very fragile
    transfer        → transfer questions; cold acceptable; no warm or medium

  For each planned question, write one sentence: difficulty, what cognitive
  move it tests, whether it needs a diagram.
  Question count must stay within the depth limits in the resource spec.
  (Answer as: Q1 warm — tests recall of...; Q2 medium — requires application of...)

Now produce the ProductionBlueprint JSON exactly matching the schema.
Do not include the reasoning steps in the JSON output.
"""

ADJUST_SYSTEM = """You revise the given ProductionBlueprint JSON according to the teacher's plain-language instruction.
Preserve IDs where possible; keep schema valid. Output the full revised blueprint."""


@lru_cache(maxsize=1)
def _planner_index_block() -> str:
    """
    Build the component palette block for the lesson architect prompt.

    Reads from lectio-content-contract.json via pipeline.contracts accessors.
    Produces phase-grouped component lines with [REQUIRED] tags, budgets,
    and per-section limits.
    """
    template = get_template_contract("guided-concept-path") or {}
    planner = get_planner_index()

    always_present = set(template.get("always_present", []))
    available = set(template.get("available_components", []))
    all_available = always_present | available

    component_budget: dict = template.get("component_budget", {})
    max_per_section: dict = template.get("max_per_section", {})

    lines: list[str] = [
        "TEMPLATE: guided-concept-path",
        f"REQUIRED in every section: {', '.join(sorted(always_present)) or 'none'}",
        "AVAILABLE COMPONENTS (use only these slugs):",
    ]

    phase_map: dict = planner.get("phase_map", {})
    for phase_num in sorted(phase_map.keys(), key=lambda k: int(k)):
        phase = phase_map[phase_num]
        phase_name = phase.get("name", f"Phase {phase_num}")
        lines.append(f"\nPhase {phase_num} — {phase_name}:")
        for cid in phase.get("components", []):
            if cid not in all_available:
                continue
            card = get_component_card(cid) or {}
            field = card.get("section_field", "—")
            role = card.get("role", "")
            cj = card.get("cognitive_job", "")
            req = " [REQUIRED]" if cid in always_present else ""
            lines.append(f"  {cid} [{field}]{req}: {role} — {cj}")

    if component_budget:
        lines.append("\nCOMPONENT BUDGETS (max across entire lesson):")
        for slug, limit in component_budget.items():
            lines.append(f"  {slug}: max {limit}")

    if max_per_section:
        lines.append("\nPER-SECTION LIMITS:")
        for slug, limit in max_per_section.items():
            lines.append(f"  {slug}: max {limit} per section")

    return "\n".join(lines)


def build_architect_system_prompt() -> str:
    """System prompt for the lesson architect, including live Lectio manifest and lenses."""
    from generation.v3_lenses.loader import format_lenses_for_prompt

    planner_block = _planner_index_block()
    lenses_block = format_lenses_for_prompt()

    return f"""You are a lesson architect. Output ONLY a valid ProductionBlueprint matching the schema.

{planner_block}

CONSTRAINT: Each section_field (shown in brackets above) may appear at
most once per section. Never plan two components with the same
section_field in the same section.

{lenses_block}

{REASONING_SCAFFOLD}

OUTPUT RULES:
- Only use component slugs from the AVAILABLE COMPONENTS list above. Never invent slugs.
- metadata: version "3.0", title, subject (from teacher subject)
- lesson:
    lesson_mode — choose from: first_exposure | consolidation | repair | retrieval | transfer
    resource_type — read from the RESOURCE SPEC in your context window (do not invent)
- applied_lenses: exactly the lenses you selected in Step 2.5, each with lens_id
  and specific non-empty effects drawn from your Step 2.5 reasoning.
  Bad effect: "use clear language"
  Good effect: "define 'equivalent fraction' before explanation-block; reuse same
               fraction pair across all practice questions"
- voice: register (simple|balanced|formal), optional tone — match to learner level
- anchor: reuse_scope string — describe how the anchor example recurs across sections
- sections: each with section_id, title, role, visual_required bool,
  components with slug and content_intent.
  content_intent must be specific enough that a writer can act on it without asking questions.
  Bad:  "explain photosynthesis"
  Good: "explain light-dependent reactions; contrast what happens with and without sunlight;
         use the chloroplast membrane as the anchor structure throughout"
- question_plan: temperature must match lesson_mode guidance from Step 7.
  Each item: question_id, section_id, temperature, prompt, expected_answer, diagram_required.
- visual_strategy: only for sections where visual_required = true.
  Each item: section_id, strategy (what the visual should show), optional density.
- answer_key: style — answers_only | brief_explanations | full_working
- repair_focus: required when lesson_mode = repair.
  fault_line: what specifically went wrong (one sentence).
  what_not_to_teach: list of things to exclude from this lesson.
- teacher_materials and prior_knowledge lists are allowed and encouraged.
Use short, clear section IDs: orient, understand, model, practice, alert, summary."""
