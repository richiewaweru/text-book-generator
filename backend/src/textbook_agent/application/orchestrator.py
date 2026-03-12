import time
import uuid
from typing import Callable

from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.domain.ports.renderer import RendererPort
from textbook_agent.domain.services.planner import CurriculumPlannerNode
from textbook_agent.domain.services.content_generator import (
    ContentGeneratorNode,
    ContentGeneratorInput,
)
from textbook_agent.domain.services.diagram_generator import (
    DiagramGeneratorNode,
    DiagramGeneratorInput,
)
from textbook_agent.domain.services.code_generator import (
    CodeGeneratorNode,
    CodeGeneratorInput,
)
from textbook_agent.domain.services.assembler import AssemblerNode, AssemblerInput
from textbook_agent.domain.services.quality_checker import (
    QualityCheckerNode,
    QualityCheckerInput,
)
from textbook_agent.domain.services.rerun_strategy import decide_reruns
from textbook_agent.application.dtos.generation_request import GenerationResponse


class TextbookAgent:
    """Top-level orchestrator that wires the 6-node pipeline together.

    Pipeline flow:
        GenerationContext
        -> [1] Planner -> CurriculumPlan
        -> [2] ContentGenerator -> list[SectionContent]
        -> [3] DiagramGenerator -> list[SectionDiagram]
        -> [4] CodeGenerator -> list[SectionCode]
        -> [5] Assembler -> RawTextbook
        -> [6] QualityChecker -> QualityReport
        -> if failed: re-run flagged sections (up to max_quality_reruns)
        -> HTMLRenderer -> final output
    """

    def __init__(
        self,
        provider: BaseProvider,
        repository: TextbookRepository,
        renderer: RendererPort,
        quality_check_enabled: bool = True,
        max_quality_reruns: int = 2,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.renderer = renderer
        self.quality_check_enabled = quality_check_enabled
        self.max_quality_reruns = max_quality_reruns
        self._on_progress = on_progress or (lambda _: None)

    def _report(self, node_name: str) -> None:
        self._on_progress(node_name)

    async def generate(self, profile: GenerationContext) -> GenerationResponse:
        start = time.monotonic()

        planner = CurriculumPlannerNode(provider=self.provider)
        content_gen = ContentGeneratorNode(provider=self.provider)
        diagram_gen = DiagramGeneratorNode(provider=self.provider)
        code_gen = CodeGeneratorNode(provider=self.provider)
        assembler = AssemblerNode()
        quality_checker = QualityCheckerNode(provider=self.provider)

        self._report("CurriculumPlanner")
        plan = await planner.execute(profile)

        # Build section_id -> SectionSpec lookup for reruns
        spec_by_id = {spec.id: spec for spec in plan.sections}

        sections = []
        diagrams = []
        code_examples = []

        for spec in plan.sections:
            self._report(f"ContentGenerator:{spec.id}")
            content = await content_gen.execute(
                ContentGeneratorInput(section=spec, profile=profile)
            )
            sections.append(content)

            if spec.needs_diagram:
                self._report(f"DiagramGenerator:{spec.id}")
                diagram = await diagram_gen.execute(
                    DiagramGeneratorInput(section=spec, content=content)
                )
                diagrams.append(diagram)

            if spec.needs_code:
                self._report(f"CodeGenerator:{spec.id}")
                code = await code_gen.execute(
                    CodeGeneratorInput(section=spec, content=content)
                )
                code_examples.append(code)

        self._report("Assembler")
        textbook = await assembler.execute(
            AssemblerInput(
                profile=profile,
                plan=plan,
                sections=sections,
                diagrams=diagrams,
                code_examples=code_examples,
            )
        )

        quality_report: QualityReport | None = None
        quality_reruns = 0

        if self.quality_check_enabled:
            self._report("QualityChecker")
            quality_report = await quality_checker.execute(
                QualityCheckerInput(textbook=textbook, plan=plan)
            )

            # Re-run loop: only re-generate sections flagged with errors
            while (
                quality_report is not None
                and not quality_report.passed
                and quality_reruns < self.max_quality_reruns
            ):
                rerun_ids = decide_reruns(quality_report)
                if not rerun_ids:
                    break

                quality_reruns += 1

                for sid in rerun_ids:
                    spec = spec_by_id.get(sid)
                    if spec is None:
                        continue

                    self._report(f"ContentGenerator:{sid}:rerun_{quality_reruns}")
                    new_content = await content_gen.execute(
                        ContentGeneratorInput(section=spec, profile=profile)
                    )
                    sections = [
                        new_content if s.section_id == sid else s for s in sections
                    ]

                    if spec.needs_diagram:
                        self._report(f"DiagramGenerator:{sid}:rerun_{quality_reruns}")
                        new_diagram = await diagram_gen.execute(
                            DiagramGeneratorInput(section=spec, content=new_content)
                        )
                        diagrams = [
                            new_diagram if d.section_id == sid else d for d in diagrams
                        ]

                    if spec.needs_code:
                        self._report(f"CodeGenerator:{sid}:rerun_{quality_reruns}")
                        new_code = await code_gen.execute(
                            CodeGeneratorInput(section=spec, content=new_content)
                        )
                        code_examples = [
                            new_code if c.section_id == sid else c
                            for c in code_examples
                        ]

                self._report(f"Assembler:rerun_{quality_reruns}")
                textbook = await assembler.execute(
                    AssemblerInput(
                        profile=profile,
                        plan=plan,
                        sections=sections,
                        diagrams=diagrams,
                        code_examples=code_examples,
                    )
                )
                self._report(f"QualityChecker:rerun_{quality_reruns}")
                quality_report = await quality_checker.execute(
                    QualityCheckerInput(textbook=textbook, plan=plan)
                )

        self._report("HTMLRenderer")
        html = self.renderer.render(textbook)

        output_path = await self.repository.save(textbook, html)

        elapsed = time.monotonic() - start
        textbook_id = str(uuid.uuid4())

        return GenerationResponse(
            textbook_id=textbook_id,
            output_path=output_path,
            quality_report=quality_report,
            generation_time_seconds=round(elapsed, 2),
            quality_reruns=quality_reruns,
        )
