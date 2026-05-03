from __future__ import annotations

from v3_blueprint.models import ProductionBlueprint, QuestionPlanItem
from v3_blueprint.compiler import BlueprintCompiler

from v3_execution.component_aliases import canonical_component_id
from v3_execution.models import (
    AnswerKeyExecutorWorkOrder,
    AnswerKeyPlanSpec,
    CompiledWorkOrders,
    LearnerProfileSpec,
    QuestionWriterWorkOrder,
    RegisterSpec,
    SectionWriterWorkOrder,
    SourceOfTruthEntry,
    VisualDependency,
    VisualFrameSpec,
    VisualGeneratorWorkOrder,
    VisualPlanItem,
    WriterQuestion,
    WriterSection,
    WriterSectionComponent,
)


def _truth_from_blueprint(blueprint: ProductionBlueprint) -> list[SourceOfTruthEntry]:
    entries: list[SourceOfTruthEntry] = []
    for line in blueprint.prior_knowledge:
        entries.append(SourceOfTruthEntry(key=f"prior:{line}", text=line))
    if blueprint.repair_focus is not None:
        entries.append(
            SourceOfTruthEntry(
                key="fault_line",
                text=blueprint.repair_focus.fault_line,
            )
        )
        for w in blueprint.repair_focus.what_not_to_teach:
            entries.append(SourceOfTruthEntry(key=f"avoid:{w}", text=w))
    return entries


def _register_from_blueprint(blueprint: ProductionBlueprint) -> RegisterSpec:
    return RegisterSpec(
        level=blueprint.voice.register_name,
        tone=blueprint.voice.tone or "instructional_clear",
    )


def _manifest_for_components(component_ids: list[str], template_id: str) -> dict[str, object]:
    from pipeline.contracts import get_component_registry_entry

    manifest: dict[str, object] = {}
    for cid in component_ids:
        entry = get_component_registry_entry(cid) or {}
        manifest[cid] = entry
    _ = template_id
    return manifest


def _infer_visual_dependency(
    section_id: str, strategy: str
) -> VisualDependency:
    strat = strategy.lower()
    if "question" in strat or "practice" in strat:
        return "question_text"
    if "section" in strat or section_id in strat:
        # Heuristic: annotated walkthroughs tend to depend on section text
        if "walkthrough" in strat or "annotate" in strat or "model" in strat:
            return "section_text"
    return "blueprint_only"


def compile_execution_bundle(
    blueprint: ProductionBlueprint,
    *,
    generation_id: str,
    blueprint_id: str,
    template_id: str,
) -> CompiledWorkOrders:
    """Map foundation blueprint + Lectio contracts → proposal-2 execution work orders."""
    BlueprintCompiler().compile_all(blueprint)  # validate blueprint shape early
    register = _register_from_blueprint(blueprint)
    truth = _truth_from_blueprint(blueprint)
    consistency_rules = [
        "Do not change anchor facts or fixed units.",
        "Do not add or remove planned components or questions.",
    ]

    section_orders: list[SectionWriterWorkOrder] = []
    for sec in blueprint.sections:
        comps: list[WriterSectionComponent] = []
        for position, c in enumerate(sec.components):
            canonical = canonical_component_id(c.component)
            comps.append(
                WriterSectionComponent(
                    component_id=canonical,
                    teacher_label=c.component.replace("_", " ").title(),
                    content_intent=c.content_intent,
                )
            )
        learning_intent = (
            "; ".join(c.content_intent for c in sec.components) or sec.title
        )
        wo = SectionWriterWorkOrder(
            work_order_id=f"sec-{sec.section_id}",
            section=WriterSection(
                id=sec.section_id,
                title=sec.title,
                learning_intent=learning_intent,
                constraints=[f"role:{sec.role}"],
                register_notes=[],
                components=comps,
            ),
            register=register,
            learner_profile=LearnerProfileSpec(),
            support_adaptations=[e.effects[0] for e in blueprint.applied_lenses if e.effects],
            source_of_truth=truth,
            consistency_rules=consistency_rules,
            manifest_components=_manifest_for_components(
                [canonical_component_id(c.component) for c in sec.components],
                template_id,
            ),
            template_id=template_id,
        )
        section_orders.append(wo)

    question_orders: list[QuestionWriterWorkOrder] = []
    by_section: dict[str, list[QuestionPlanItem]] = {}
    for q in blueprint.question_plan:
        by_section.setdefault(q.section_id, []).append(q)
    for sec_id, items in by_section.items():
        qs = [
            WriterQuestion(
                id=item.question_id,
                difficulty="extension" if item.temperature == "transfer" else item.temperature,
                diagram_required=item.diagram_required,
                expected_answer=item.expected_answer,
                uses_anchor_id=None,
                skill_target="lesson_objective",
                purpose="practice",
            )
            for item in items
        ]
        question_orders.append(
            QuestionWriterWorkOrder(
                work_order_id=f"q-{sec_id}",
                section_id=sec_id,
                questions=qs,
                source_of_truth=truth,
                register=register,
                consistency_rules=consistency_rules,
            )
        )

    visual_orders: list[VisualGeneratorWorkOrder] = []
    for idx, vis in enumerate(blueprint.visual_strategy.visuals):
        series = "series" in vis.strategy.lower()
        mode = "diagram_series" if series else "diagram"
        dependency = _infer_visual_dependency(vis.section_id, vis.strategy)
        plan = VisualPlanItem(
            id=f"vis-{vis.section_id}-{idx}",
            attaches_to=vis.section_id,
            mode=mode,
            purpose=vis.strategy,
            must_show=[vis.strategy] + ([f"density:{vis.density}"] if vis.density else []),
            frames=[VisualFrameSpec(description=vis.strategy)] if series else [],
        )
        visual_orders.append(
            VisualGeneratorWorkOrder(
                work_order_id=plan.id,
                resource_type=blueprint.lesson.resource_type,
                dependency=dependency,
                visual=plan,
                source_of_truth=truth,
            )
        )

    mapped_style = _map_answer_key_style(blueprint.answer_key.style)
    aq_questions = [
        WriterQuestion(
            id=item.question_id,
            difficulty="extension" if item.temperature == "transfer" else item.temperature,
            diagram_required=item.diagram_required,
            expected_answer=item.expected_answer,
        )
        for item in blueprint.question_plan
    ]
    answer_key_order = AnswerKeyExecutorWorkOrder(
        work_order_id="answer-key-main",
        questions=aq_questions,
        answer_key_plan=AnswerKeyPlanSpec(
            style=mapped_style,
            include_question_ids=[q.id for q in aq_questions],
        ),
        source_of_truth=truth,
    )

    return CompiledWorkOrders(
        generation_id=generation_id,
        blueprint_id=blueprint_id,
        template_id=template_id,
        section_orders=section_orders,
        question_orders=question_orders,
        visual_orders=visual_orders,
        answer_key_order=answer_key_order,
    )


def _map_answer_key_style(raw: str) -> str:
    lowered = raw.strip().lower().replace(" ", "_")
    if lowered in {"full_working"}:
        return "full_working"
    if lowered in {"answers_only"}:
        return "answers_only"
    if lowered in {"brief_explanations", "explanation_focused"}:
        return "brief_explanations"
    return "brief_explanations"


__all__ = ["compile_execution_bundle"]
