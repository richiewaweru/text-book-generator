import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from textbook_agent.application.dtos.generation_request import GenerationResponse
from textbook_agent.application.dtos.generation_status import GenerationProgress
from textbook_agent.domain.entities.correction_context import (
    CodeCorrectionContext,
    ContentCorrectionContext,
    DiagramCorrectionContext,
)
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan, SectionSpec
from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.entities.quality_report import QualityIssue, QualityReport
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.renderer import RendererPort
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.domain.services.assembler import AssemblerInput, AssemblerNode
from textbook_agent.domain.services.code_generator import (
    CodeGeneratorInput,
    CodeGeneratorNode,
)
from textbook_agent.domain.services.content_generator import (
    ContentGeneratorInput,
    ContentGeneratorNode,
)
from textbook_agent.domain.services.diagram_generator import (
    DiagramGeneratorInput,
    DiagramGeneratorNode,
)
from textbook_agent.domain.services.inline_qc import InlineQualityChecker
from textbook_agent.domain.services.planner import CurriculumPlannerNode
from textbook_agent.domain.services.quality_checker import (
    QualityCheckerInput,
    QualityCheckerNode,
)
from textbook_agent.domain.services.rerun_strategy import (
    document_blockers,
    group_retry_issues,
)
from textbook_agent.domain.value_objects import GenerationMode, ModelRouting


_DIAGRAM_ISSUE_TYPES = {"svg_missing_required_attributes"}
_CODE_ISSUE_TYPES = {
    "missing_code_language",
    "code_line_too_long",
    "invalid_python_code",
}


@dataclass
class SectionArtifacts:
    content: SectionContent
    diagram: SectionDiagram | None = None
    code_example: SectionCode | None = None


class TextbookAgent:
    """Top-level orchestrator that runs the generation pipeline."""

    def __init__(
        self,
        provider: BaseProvider,
        repository: TextbookRepository,
        renderer: RendererPort,
        mode: GenerationMode = GenerationMode.BALANCED,
        quality_check_enabled: bool = True,
        max_quality_reruns: int = 3,
        max_retries: int = 2,
        retry_base_delay: float = 1.0,
        code_line_soft_limit: int = 80,
        code_line_hard_limit: int = 300,
        model_routing: ModelRouting | None = None,
        on_progress: Callable[[GenerationProgress], None] | None = None,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.renderer = renderer
        self.mode = mode
        self.quality_check_enabled = quality_check_enabled
        self.max_quality_reruns = max_quality_reruns
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.code_line_soft_limit = code_line_soft_limit
        self.code_line_hard_limit = code_line_hard_limit
        self.model_routing = model_routing or ModelRouting()
        self._on_progress = on_progress or (lambda _: None)

    async def generate(
        self,
        profile: GenerationContext,
        *,
        seed_textbook: RawTextbook | None = None,
        source_generation_id: str | None = None,
    ) -> GenerationResponse:
        start = time.monotonic()
        routing = self._routing_for_mode()

        planner = CurriculumPlannerNode(
            provider=self.provider,
            model_override=routing.planner,
        )
        content_gen = ContentGeneratorNode(
            provider=self.provider,
            model_override=routing.content,
        )
        diagram_gen = DiagramGeneratorNode(
            provider=self.provider,
            model_override=routing.diagram,
        )
        code_gen = CodeGeneratorNode(
            provider=self.provider,
            model_override=routing.code,
        )
        inline_checker = InlineQualityChecker(
            provider=self.provider,
            code_line_soft_limit=self.code_line_soft_limit,
            code_line_hard_limit=self.code_line_hard_limit,
            model_override=routing.inline_quality,
        )
        final_quality_checker = QualityCheckerNode(
            provider=self.provider,
            code_line_soft_limit=self.code_line_soft_limit,
            code_line_hard_limit=self.code_line_hard_limit,
            include_llm_review=self.mode != GenerationMode.DRAFT,
            model_override=routing.final_quality,
        )
        assembler = AssemblerNode()

        for node in (planner, content_gen, diagram_gen, code_gen, final_quality_checker):
            node.max_retries = self.max_retries
            node.retry_base_delay = self.retry_base_delay

        if seed_textbook is None:
            self._report(
                phase="planning",
                message="Planning your curriculum...",
            )
            plan = await planner.execute(profile)
            sections_by_id: dict[str, SectionArtifacts] = {}
        else:
            plan = seed_textbook.plan
            sections_by_id = self._artifacts_from_seed(seed_textbook)

        total_sections = len(plan.sections)
        sections_completed = 0

        for index, spec in enumerate(plan.sections, start=1):
            if seed_textbook is None:
                artifacts = await self._generate_section_package(
                    spec,
                    profile,
                    inline_checker,
                    content_gen,
                    diagram_gen,
                    code_gen,
                    index=index,
                    total_sections=total_sections,
                )
            else:
                self._report(
                    phase="checking",
                    message=f"Reviewing draft section {index} of {total_sections}...",
                    sections_total=total_sections,
                    sections_completed=sections_completed,
                    current_section_id=spec.id,
                    current_section_title=spec.title,
                )
                artifacts = sections_by_id.get(spec.id)
                if artifacts is None:
                    artifacts = await self._generate_section_package(
                        spec,
                        profile,
                        inline_checker,
                        content_gen,
                        diagram_gen,
                        code_gen,
                        index=index,
                        total_sections=total_sections,
                    )
                else:
                    artifacts, _ = await self._run_inline_quality_loop(
                        spec,
                        profile,
                        artifacts,
                        inline_checker,
                        content_gen,
                        diagram_gen,
                        code_gen,
                        index=index,
                        total_sections=total_sections,
                    )

            sections_by_id[spec.id] = artifacts
            sections_completed += 1

        textbook = await self._assemble_textbook(plan, profile, sections_by_id, assembler, total_sections)

        quality_report: QualityReport | None = None
        quality_reruns = 0

        if self.mode != GenerationMode.DRAFT and self.quality_check_enabled:
            quality_report = await self._run_final_quality_check(
                final_quality_checker,
                textbook,
                plan,
                total_sections=total_sections,
            )

            while quality_reruns < self._final_repair_budget():
                retry_groups = group_retry_issues(quality_report)
                if not retry_groups:
                    break

                quality_reruns += 1
                self._report(
                    phase="fixing",
                    message=(
                        f"Fixing {len(retry_groups)} section(s) from final review..."
                    ),
                    sections_total=total_sections,
                    sections_completed=total_sections,
                    retry_attempt=quality_reruns,
                    retry_limit=self._final_repair_budget(),
                    flagged_section_ids=list(retry_groups),
                )

                for section_id, issues in retry_groups.items():
                    spec = next((item for item in plan.sections if item.id == section_id), None)
                    if spec is None:
                        continue
                    artifacts = sections_by_id[section_id]
                    repaired = await self._repair_section_from_final_issues(
                        spec,
                        profile,
                        artifacts,
                        issues,
                        content_gen,
                        diagram_gen,
                        code_gen,
                        inline_checker,
                        index=plan.reading_order.index(section_id) + 1,
                        total_sections=total_sections,
                    )
                    sections_by_id[section_id] = repaired

                textbook = await self._assemble_textbook(
                    plan,
                    profile,
                    sections_by_id,
                    assembler,
                    total_sections,
                )
                quality_report = await self._run_final_quality_check(
                    final_quality_checker,
                    textbook,
                    plan,
                    total_sections=total_sections,
                )
                if document_blockers(quality_report):
                    break

        self._report(
            phase="rendering",
            message=(
                "Rendering enhanced textbook..."
                if source_generation_id
                else "Rendering your textbook..."
            ),
            sections_total=total_sections,
            sections_completed=total_sections,
        )
        html = self.renderer.render(textbook)
        output_path = await self.repository.save(textbook, html)
        elapsed = time.monotonic() - start

        return GenerationResponse(
            textbook_id=str(uuid.uuid4()),
            output_path=output_path,
            mode=self.mode,
            quality_report=quality_report,
            generation_time_seconds=round(elapsed, 2),
            quality_reruns=quality_reruns,
            source_generation_id=source_generation_id,
        )

    def _report(
        self,
        *,
        phase: Literal["planning", "generating", "checking", "fixing", "rendering"],
        message: str,
        sections_total: int | None = None,
        sections_completed: int = 0,
        current_section_id: str | None = None,
        current_section_title: str | None = None,
        retry_attempt: int | None = None,
        retry_limit: int | None = None,
        flagged_section_ids: list[str] | None = None,
    ) -> None:
        self._on_progress(
            GenerationProgress(
                mode=self.mode,
                phase=phase,
                message=message,
                sections_total=sections_total,
                sections_completed=sections_completed,
                current_section_id=current_section_id,
                current_section_title=current_section_title,
                retry_attempt=retry_attempt,
                retry_limit=retry_limit,
                flagged_section_ids=flagged_section_ids or [],
            )
        )

    def _routing_for_mode(self) -> ModelRouting:
        if self.mode == GenerationMode.STRICT:
            premium = self.model_routing.planner
            return ModelRouting(
                planner=premium,
                content=self.model_routing.content or premium,
                diagram=self.model_routing.content or premium,
                code=self.model_routing.code or premium,
                inline_quality=self.model_routing.content or premium,
                final_quality=self.model_routing.final_quality or premium,
            )
        return self.model_routing

    def _final_repair_budget(self) -> int:
        if self.mode == GenerationMode.DRAFT:
            return 0
        if self.mode == GenerationMode.BALANCED:
            return min(1, self.max_quality_reruns)
        return self.max_quality_reruns

    def _inline_retry_limit(self) -> int:
        return self.max_retries + 1

    @staticmethod
    def _artifacts_from_seed(textbook: RawTextbook) -> dict[str, SectionArtifacts]:
        diagram_map = {diagram.section_id: diagram for diagram in textbook.diagrams}
        code_map = {
            code_example.section_id: code_example
            for code_example in textbook.code_examples
        }
        return {
            section.section_id: SectionArtifacts(
                content=section,
                diagram=diagram_map.get(section.section_id),
                code_example=code_map.get(section.section_id),
            )
            for section in textbook.sections
        }

    async def _generate_section_package(
        self,
        spec: SectionSpec,
        profile: GenerationContext,
        inline_checker: InlineQualityChecker,
        content_gen: ContentGeneratorNode,
        diagram_gen: DiagramGeneratorNode,
        code_gen: CodeGeneratorNode,
        *,
        index: int,
        total_sections: int,
    ) -> SectionArtifacts:
        content = await self._generate_content(
            spec,
            profile,
            content_gen,
            index=index,
            total_sections=total_sections,
        )
        diagram = await self._generate_diagram(
            spec,
            content,
            diagram_gen,
            index=index,
            total_sections=total_sections,
        )
        code_example = await self._generate_code(
            spec,
            content,
            code_gen,
            index=index,
            total_sections=total_sections,
        )
        artifacts, _ = await self._run_inline_quality_loop(
            spec,
            profile,
            SectionArtifacts(content=content, diagram=diagram, code_example=code_example),
            inline_checker,
            content_gen,
            diagram_gen,
            code_gen,
            index=index,
            total_sections=total_sections,
        )
        return artifacts

    async def _run_inline_quality_loop(
        self,
        spec: SectionSpec,
        profile: GenerationContext,
        artifacts: SectionArtifacts,
        inline_checker: InlineQualityChecker,
        content_gen: ContentGeneratorNode,
        diagram_gen: DiagramGeneratorNode,
        code_gen: CodeGeneratorNode,
        *,
        index: int,
        total_sections: int,
    ) -> tuple[SectionArtifacts, QualityReport]:
        self._report(
            phase="checking",
            message=f"Checking section {index} of {total_sections}...",
            sections_total=total_sections,
            sections_completed=index - 1,
            current_section_id=spec.id,
            current_section_title=spec.title,
        )
        report = await inline_checker.check_section(
            spec,
            artifacts.content,
            diagram=artifacts.diagram,
            code_example=artifacts.code_example,
        )

        attempt = 0
        while (
            not report.passed
            and attempt < self._inline_retry_limit()
        ):
            retryable_issues = [
                issue
                for issue in report.issues
                if issue.severity == "error" and issue.scope == "section"
            ]
            if not retryable_issues:
                break

            attempt += 1
            self._report(
                phase="fixing",
                message=f"Fixing section {index} of {total_sections}...",
                sections_total=total_sections,
                sections_completed=index - 1,
                current_section_id=spec.id,
                current_section_title=spec.title,
                retry_attempt=attempt,
                retry_limit=self._inline_retry_limit(),
                flagged_section_ids=[spec.id],
            )
            artifacts = await self._repair_section_artifacts(
                spec,
                profile,
                artifacts,
                retryable_issues,
                content_gen,
                diagram_gen,
                code_gen,
                index=index,
                total_sections=total_sections,
            )
            report = await inline_checker.check_section(
                spec,
                artifacts.content,
                diagram=artifacts.diagram,
                code_example=artifacts.code_example,
            )

        return artifacts, report

    async def _repair_section_from_final_issues(
        self,
        spec: SectionSpec,
        profile: GenerationContext,
        artifacts: SectionArtifacts,
        issues: list[QualityIssue],
        content_gen: ContentGeneratorNode,
        diagram_gen: DiagramGeneratorNode,
        code_gen: CodeGeneratorNode,
        inline_checker: InlineQualityChecker,
        *,
        index: int,
        total_sections: int,
    ) -> SectionArtifacts:
        artifacts = await self._repair_section_artifacts(
            spec,
            profile,
            artifacts,
            issues,
            content_gen,
            diagram_gen,
            code_gen,
            index=index,
            total_sections=total_sections,
        )
        artifacts, _ = await self._run_inline_quality_loop(
            spec,
            profile,
            artifacts,
            inline_checker,
            content_gen,
            diagram_gen,
            code_gen,
            index=index,
            total_sections=total_sections,
        )
        return artifacts

    async def _repair_section_artifacts(
        self,
        spec: SectionSpec,
        profile: GenerationContext,
        artifacts: SectionArtifacts,
        issues: list[QualityIssue],
        content_gen: ContentGeneratorNode,
        diagram_gen: DiagramGeneratorNode,
        code_gen: CodeGeneratorNode,
        *,
        index: int,
        total_sections: int,
    ) -> SectionArtifacts:
        content_issues, diagram_issues, code_issues = self._partition_section_issues(issues)
        content_changed = bool(content_issues)

        if content_changed:
            artifacts.content = await self._generate_content(
                spec,
                profile,
                content_gen,
                correction_context=ContentCorrectionContext(
                    original_content=artifacts.content,
                    issues=content_issues,
                ),
                index=index,
                total_sections=total_sections,
            )
            if spec.needs_diagram:
                artifacts.diagram = await self._generate_diagram(
                    spec,
                    artifacts.content,
                    diagram_gen,
                    correction_context=(
                        DiagramCorrectionContext(
                            original_diagram=artifacts.diagram,
                            issues=diagram_issues,
                        )
                        if artifacts.diagram is not None and diagram_issues
                        else None
                    ),
                    index=index,
                    total_sections=total_sections,
                )
            if spec.needs_code:
                artifacts.code_example = await self._generate_code(
                    spec,
                    artifacts.content,
                    code_gen,
                    correction_context=(
                        CodeCorrectionContext(
                            original_code=artifacts.code_example,
                            issues=code_issues,
                        )
                        if artifacts.code_example is not None and code_issues
                        else None
                    ),
                    index=index,
                    total_sections=total_sections,
                )
            return artifacts

        if diagram_issues and spec.needs_diagram:
            artifacts.diagram = await self._generate_diagram(
                spec,
                artifacts.content,
                diagram_gen,
                correction_context=(
                    DiagramCorrectionContext(
                        original_diagram=artifacts.diagram,
                        issues=diagram_issues,
                    )
                    if artifacts.diagram is not None
                    else None
                ),
                index=index,
                total_sections=total_sections,
            )

        if code_issues and spec.needs_code:
            artifacts.code_example = await self._generate_code(
                spec,
                artifacts.content,
                code_gen,
                correction_context=(
                    CodeCorrectionContext(
                        original_code=artifacts.code_example,
                        issues=code_issues,
                    )
                    if artifacts.code_example is not None
                    else None
                ),
                index=index,
                total_sections=total_sections,
            )

        return artifacts

    async def _generate_content(
        self,
        spec: SectionSpec,
        profile: GenerationContext,
        content_gen: ContentGeneratorNode,
        *,
        correction_context: ContentCorrectionContext | None = None,
        index: int | None = None,
        total_sections: int | None = None,
    ) -> SectionContent:
        if index is not None and total_sections is not None:
            self._report(
                phase="generating",
                message=f"Writing section {index} of {total_sections}...",
                sections_total=total_sections,
                sections_completed=max(index - 1, 0),
                current_section_id=spec.id,
                current_section_title=spec.title,
            )
        return await content_gen.execute(
            ContentGeneratorInput(
                section=spec,
                profile=profile,
                correction_context=correction_context,
            )
        )

    async def _generate_diagram(
        self,
        spec: SectionSpec,
        content: SectionContent,
        diagram_gen: DiagramGeneratorNode,
        *,
        correction_context: DiagramCorrectionContext | None = None,
        index: int | None = None,
        total_sections: int | None = None,
    ) -> SectionDiagram | None:
        if not spec.needs_diagram:
            return None
        if index is not None and total_sections is not None:
            self._report(
                phase="generating",
                message=f"Creating diagram for section {index} of {total_sections}...",
                sections_total=total_sections,
                sections_completed=max(index - 1, 0),
                current_section_id=spec.id,
                current_section_title=spec.title,
            )
        return await diagram_gen.execute(
            DiagramGeneratorInput(
                section=spec,
                content=content,
                correction_context=correction_context,
            )
        )

    async def _generate_code(
        self,
        spec: SectionSpec,
        content: SectionContent,
        code_gen: CodeGeneratorNode,
        *,
        correction_context: CodeCorrectionContext | None = None,
        index: int | None = None,
        total_sections: int | None = None,
    ) -> SectionCode | None:
        if not spec.needs_code:
            return None
        if index is not None and total_sections is not None:
            self._report(
                phase="generating",
                message=f"Generating code for section {index} of {total_sections}...",
                sections_total=total_sections,
                sections_completed=max(index - 1, 0),
                current_section_id=spec.id,
                current_section_title=spec.title,
            )
        return await code_gen.execute(
            CodeGeneratorInput(
                section=spec,
                content=content,
                correction_context=correction_context,
            )
        )

    async def _assemble_textbook(
        self,
        plan: CurriculumPlan,
        profile: GenerationContext,
        sections_by_id: dict[str, SectionArtifacts],
        assembler: AssemblerNode,
        total_sections: int,
    ) -> RawTextbook:
        self._report(
            phase="generating",
            message="Assembling your textbook...",
            sections_total=total_sections,
            sections_completed=total_sections,
        )
        return await assembler.execute(
            AssemblerInput(
                profile=profile,
                plan=plan,
                sections=[
                    sections_by_id[section_id].content for section_id in plan.reading_order
                ],
                diagrams=[
                    sections_by_id[section_id].diagram
                    for section_id in plan.reading_order
                    if sections_by_id[section_id].diagram is not None
                ],
                code_examples=[
                    sections_by_id[section_id].code_example
                    for section_id in plan.reading_order
                    if sections_by_id[section_id].code_example is not None
                ],
            )
        )

    async def _run_final_quality_check(
        self,
        checker: QualityCheckerNode,
        textbook: RawTextbook,
        plan: CurriculumPlan,
        *,
        total_sections: int,
    ) -> QualityReport:
        self._report(
            phase="checking",
            message="Running final quality review...",
            sections_total=total_sections,
            sections_completed=total_sections,
        )
        return await checker.execute(
            QualityCheckerInput(textbook=textbook, plan=plan)
        )

    @staticmethod
    def _partition_section_issues(
        issues: list[QualityIssue],
    ) -> tuple[list[QualityIssue], list[QualityIssue], list[QualityIssue]]:
        content_issues: list[QualityIssue] = []
        diagram_issues: list[QualityIssue] = []
        code_issues: list[QualityIssue] = []

        for issue in issues:
            if issue.issue_type.startswith("diagram_") or issue.issue_type in _DIAGRAM_ISSUE_TYPES:
                diagram_issues.append(issue)
            elif issue.issue_type.startswith("code_") or issue.issue_type in _CODE_ISSUE_TYPES:
                code_issues.append(issue)
            else:
                content_issues.append(issue)

        return content_issues, diagram_issues, code_issues
