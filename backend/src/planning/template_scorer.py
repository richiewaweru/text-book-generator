from __future__ import annotations

from planning.models import (
    NormalizedBrief,
    PlanningTemplateContract,
    TemplateAlternative,
    TemplateDecision,
)

_WEIGHTS = {
    "topic_type": 0.25,
    "learning_outcome": 0.30,
    "class_style": 0.25,
    "format": 0.20,
}


def _score_contract(brief: NormalizedBrief, contract: PlanningTemplateContract) -> float:
    signals = contract.signal_affinity
    score = 0.0
    score += _WEIGHTS["topic_type"] * signals.topic_type.get(brief.resolved_topic_type, 0.45)
    score += _WEIGHTS["learning_outcome"] * signals.learning_outcome.get(
        brief.resolved_learning_outcome, 0.45
    )
    if brief.brief.signals.class_style:
        class_scores = [
            signals.class_style.get(style, 0.45) for style in brief.brief.signals.class_style
        ]
        score += _WEIGHTS["class_style"] * (sum(class_scores) / len(class_scores))
    else:
        score += _WEIGHTS["class_style"] * 0.55
    score += _WEIGHTS["format"] * signals.format.get(brief.resolved_format, 0.55)
    return round(score, 4)


def _why_not_chosen(contract: PlanningTemplateContract, score: float) -> str:
    if contract.not_ideal_for:
        return contract.not_ideal_for[0]
    if contract.best_for:
        return f"Strong fit for {contract.best_for[0]}, but the top option scored higher."
    return f"Scored {score:.2f}, but another template matched the brief more closely."


def _decision_rationale(contract: PlanningTemplateContract, brief: NormalizedBrief) -> str:
    reasons: list[str] = []
    if contract.best_for:
        reasons.append(contract.best_for[0])
    if brief.resolved_learning_outcome == "be-able-to-do":
        reasons.append("it supports a doing-oriented outcome")
    elif brief.resolved_learning_outcome == "understand-why":
        reasons.append("it fits explanation-first teaching")
    if brief.brief.constraints.keep_short:
        reasons.append("it can stay compact without losing structure")
    if not reasons:
        return f"{contract.name} is the best overall fit for this lesson."
    return f"{contract.name} is the best fit because {'; '.join(reasons[:2])}."


def choose_template(
    brief: NormalizedBrief,
    contracts: list[PlanningTemplateContract],
) -> tuple[PlanningTemplateContract, TemplateDecision]:
    scored = [(contract, _score_contract(brief, contract)) for contract in contracts]
    scored.sort(key=lambda item: item[1], reverse=True)

    chosen_contract, chosen_score = scored[0]
    decision = TemplateDecision(
        chosen_id=chosen_contract.id,
        chosen_name=chosen_contract.name,
        rationale=_decision_rationale(chosen_contract, brief),
        fit_score=chosen_score,
        alternatives=[
            TemplateAlternative(
                template_id=contract.id,
                template_name=contract.name,
                fit_score=score,
                why_not_chosen=_why_not_chosen(contract, score),
            )
            for contract, score in scored[1:4]
        ],
    )
    return chosen_contract, decision
