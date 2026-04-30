from __future__ import annotations

outcome_role_map: dict[str, list[str]] = {
    "understand": ["introduce", "explain", "example", "visualize", "check"],
    "practice": ["model", "practice", "hint", "answer_check"],
    "review": ["summary", "practice", "check", "reflect"],
    "assess": ["question_set", "short_response", "answer_key"],
    "compare": ["compare", "example", "check", "reflect"],
    "vocabulary": ["vocabulary", "example", "practice", "check"],
}

support_role_map: dict[str, list[str]] = {
    "visuals": ["visualize"],
    "vocabulary_support": ["vocabulary"],
    "worked_examples": ["model"],
    "step_by_step": ["hint", "scaffold"],
    "discussion_questions": ["discuss", "reflect"],
    "simpler_reading": ["simplify", "chunk"],
    "challenge_questions": ["challenge"],
}

role_component_map: dict[str, list[str]] = {
    "introduce": ["HookHero", "SectionHeader"],
    "explain": ["ExplanationBlock"],
    "model": ["WorkedExampleCard"],
    "practice": ["PracticeStack"],
    "check": ["PracticeStack"],
    "vocabulary": ["DefinitionCard", "GlossaryStrip"],
    "visualize": ["DiagramBlock"],
    "reflect": ["FillInBlock", "ShortResponseField"],
    "compare": ["ExplanationBlock"],
    "challenge": ["PracticeStack"],
    "summary": ["SummaryBlock"],
    "self_assess": ["FillInBlock"],
    "question_set": ["PracticeStack"],
    "answer_key": ["AnswerKeyBlock"],
    "hint": ["CalloutBlock"],
    "scaffold": ["StepSequence"],
}
