from __future__ import annotations

from html import escape

import core.events as core_events

from pipeline.events import InteractionOutcomeEvent
from pipeline.media.assembly import (
    apply_slot_results_to_section,
    build_slot_result,
)
from pipeline.media.runtime_events import (
    emit_frame_failed,
    emit_frame_ready,
    emit_frame_started,
    emit_slot_state,
)
from pipeline.media.planner.media_planner import find_slot
from pipeline.media.prompts.simulation_prompts import build_simulation_prompt
from pipeline.media.qc.simulation_qc import validate_simulation_content
from pipeline.media.types import SlotType, VisualFrameResult, VisualFrameResultStatus
from pipeline.state import PipelineError
from pipeline.state import TextbookPipelineState
from pipeline.types.section_content import (
    InteractionContext,
    InteractionDimensions,
    InteractionSpec,
    SimulationContent,
)


def _publish_interaction_outcome(
    generation_id: str,
    section_id: str | None,
    outcome: str,
    *,
    skip_reason: str | None = None,
    interaction_count: int = 0,
) -> None:
    if not generation_id or not section_id:
        return
    core_events.event_bus.publish(
        generation_id,
        InteractionOutcomeEvent(
            generation_id=generation_id,
            section_id=section_id,
            outcome=outcome,
            skip_reason=skip_reason,
            interaction_count=interaction_count,
        ),
    )


def _resolve_colors(state: TextbookPipelineState) -> tuple[str, str]:
    palette = (state.style_context.palette if state.style_context is not None else "").lower()
    if "navy" in palette:
        return "#17417a", "#f7fbff"
    if "green" in palette:
        return "#166534", "#f6fff9"
    return "#1f3b6b", "#fbfcfe"


def build_interaction_spec(
    state: TextbookPipelineState,
    section,
    slot,
) -> InteractionSpec:
    accent_color, surface_color = _resolve_colors(state)
    learner_level = getattr(state.current_section_plan, "interaction_policy", "allowed")
    return InteractionSpec(
        type=(slot.simulation_type or "graph_slider"),  # type: ignore[arg-type]
        goal=slot.simulation_goal or slot.simulation_intent or slot.pedagogical_intent,
        anchor_content={
            "headline": section.hook.headline,
            "body": section.explanation.body[:280],
            "anchor_block": slot.anchor_block or "explanation",
        },
        context=InteractionContext(
            learner_level=learner_level,
            template_id=state.contract.id,
            color_mode="light",
            accent_color=accent_color,
            surface_color=surface_color,
            font_mono="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
        ),
        dimensions=InteractionDimensions(
            width="100%",
            height=420,
            resizable=True,
        ),
        print_translation=slot.print_translation or "static_diagram",
    )


def _milestones(slot) -> list[str]:
    milestones = slot.frames[0].must_include if slot.frames else []
    return milestones[:4] or ["Observe", "Adjust", "Compare", "Explain"]


def _build_html_document(*, title: str, prompt: str, spec: InteractionSpec, milestones: list[str]) -> str:
    escaped_title = escape(title)
    escaped_goal = escape(spec.goal)
    escaped_prompt = escape(prompt)
    steps = ", ".join(f"'{escape(item)}'" for item in milestones)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escaped_title}</title>
    <style>
      :root {{
        --accent: {spec.context.accent_color};
        --surface: {spec.context.surface_color};
        --ink: #132238;
        --muted: #5b6b82;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Inter, 'Segoe UI', sans-serif;
        background:
          radial-gradient(circle at top right, rgba(255,255,255,0.95), transparent 48%),
          linear-gradient(180deg, #ffffff 0%, var(--surface) 100%);
        color: var(--ink);
      }}
      main {{ padding: 24px; display: grid; gap: 18px; min-height: 100vh; }}
      .panel {{
        background: rgba(255,255,255,0.88);
        border: 1px solid rgba(19,34,56,0.08);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 16px 40px rgba(19,34,56,0.08);
      }}
      .eyebrow {{
        font-size: 12px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--muted);
        margin: 0 0 8px;
      }}
      h1 {{ margin: 0 0 10px; font-size: 1.5rem; }}
      p {{ margin: 0; line-height: 1.55; }}
      input[type="range"] {{ width: 100%; accent-color: var(--accent); }}
      .meter {{
        height: 14px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(19,34,56,0.08);
      }}
      .meter-fill {{
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, var(--accent), #7dd3fc);
        transition: width 180ms ease;
      }}
      .milestones {{
        display: grid;
        gap: 10px;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      }}
      .milestone {{
        border-radius: 14px;
        padding: 12px;
        background: rgba(19,34,56,0.04);
        border: 1px solid rgba(19,34,56,0.08);
      }}
      .milestone.active {{
        border-color: rgba(23,65,122,0.24);
        background: rgba(23,65,122,0.08);
      }}
      code {{
        display: block;
        white-space: pre-wrap;
        font-family: {escape(spec.context.font_mono)};
        font-size: 12px;
        color: var(--muted);
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="panel">
        <p class="eyebrow">{escape(spec.type.replace('_', ' '))}</p>
        <h1>{escaped_title}</h1>
        <p>{escaped_goal}</p>
      </section>
      <section class="panel">
        <p class="eyebrow">Manipulate</p>
        <input id="progress" type="range" min="0" max="100" value="35" />
        <div class="meter" aria-hidden="true"><div id="meterFill" class="meter-fill"></div></div>
        <p id="readout"></p>
      </section>
      <section class="panel">
        <p class="eyebrow">Observe</p>
        <div id="milestones" class="milestones"></div>
      </section>
      <section class="panel">
        <p class="eyebrow">Plan</p>
        <code>{escaped_prompt}</code>
      </section>
    </main>
    <script>
      const milestones = [{steps}];
      const slider = document.getElementById('progress');
      const readout = document.getElementById('readout');
      const meterFill = document.getElementById('meterFill');
      const container = document.getElementById('milestones');

      function render(value) {{
        const normalized = Number(value) / 100;
        meterFill.style.width = value + '%';
        const activeIndex = Math.min(milestones.length - 1, Math.floor(normalized * milestones.length));
        readout.textContent = `Current state: ${{
          Math.round(normalized * 100)
        }}% — focus on "${{milestones[activeIndex]}}"`;
        container.innerHTML = milestones.map((item, index) => `
          <div class="milestone ${{index <= activeIndex ? 'active' : ''}}">
            <strong>${{index + 1}}.</strong> ${{item}}
          </div>
        `).join('');
      }}

      slider.addEventListener('input', (event) => render(event.target.value));
      render(slider.value);
    </script>
  </body>
</html>"""


async def simulation_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    _ = model_overrides
    typed = TextbookPipelineState.parse(state)
    sid = typed.current_section_id
    section = typed.generated_sections.get(sid)
    generation_id = typed.request.generation_id or ""

    if sid is None or section is None:
        return {"completed_nodes": ["interaction_generator"]}

    has_contract_slot = "simulation-block" in (
        set(typed.contract.required_components) | set(typed.contract.optional_components)
    )
    if not has_contract_slot:
        _publish_interaction_outcome(generation_id, sid, "skipped", skip_reason="no_slot")
        return {"completed_nodes": ["interaction_generator"]}

    media_plan = typed.media_plans.get(sid)
    slot = find_slot(media_plan, SlotType.SIMULATION)
    if slot is None:
        _publish_interaction_outcome(generation_id, sid, "skipped", skip_reason="no_plan")
        return {"completed_nodes": ["interaction_generator"]}

    if typed.current_section_plan is not None and typed.current_section_plan.interaction_policy == "disabled":
        _publish_interaction_outcome(generation_id, sid, "skipped", skip_reason="policy_disabled")
        return {"completed_nodes": ["interaction_generator"]}

    if typed.contract.interaction_level not in {"medium", "high"}:
        _publish_interaction_outcome(
            generation_id,
            sid,
            "skipped",
            skip_reason="low_interaction_level",
        )
        return {"completed_nodes": ["interaction_generator"]}

    spec = build_interaction_spec(typed, section, slot)
    frame = slot.frames[0]
    prompt = build_simulation_prompt(
        section_title=section.header.title,
        slot=slot,
        frame=frame,
    )
    emit_frame_started(
        generation_id=generation_id,
        section_id=sid,
        slot=slot,
        frame=frame,
    )
    html_content = _build_html_document(
        title=section.header.title,
        prompt=prompt,
        spec=spec,
        milestones=_milestones(slot),
    )
    frame_result = VisualFrameResult(
        slot_id=slot.slot_id,
        frame_index=frame.index,
        label=frame.label,
        render=slot.preferred_render,
        status=VisualFrameResultStatus.GENERATED,
        html_content=html_content,
        interaction_spec=spec,
        explanation=(
            f"Interactive view for {section.header.title}. "
            f"Use it to explore {spec.goal.lower()} step by step."
        ),
    )
    frame_results = {str(frame.index): frame_result}
    slot_result = build_slot_result(slot, frame_results)
    preview_section = apply_slot_results_to_section(
        section,
        slot,
        frame_results,
        fallback_diagram=section.diagram,
    )
    preview_simulation = preview_section.simulation or SimulationContent(
        spec=spec,
        html_content=html_content,
        explanation=frame_result.explanation,
    )
    qc_issues = validate_simulation_content(
        slot=slot,
        simulation=preview_simulation,
        fallback_diagram=preview_simulation.fallback_diagram,
    )
    if qc_issues:
        frame_result.status = VisualFrameResultStatus.FAILED
        frame_result.error_message = "; ".join(qc_issues)
        frame_results = {str(frame.index): frame_result}
        slot_result = build_slot_result(slot, frame_results, error_message=frame_result.error_message)
        emit_frame_failed(
            generation_id=generation_id,
            section_id=sid,
            slot=slot,
            frame=frame,
            error=frame_result.error_message,
        )
        emit_slot_state(
            generation_id=generation_id,
            section_id=sid,
            slot=slot,
            ready_frames=slot_result.completed_frames,
            total_frames=slot_result.total_frames,
            error=slot_result.error_message,
        )
        _publish_interaction_outcome(generation_id, sid, "error", interaction_count=1)
        return {
            "errors": [
                PipelineError(
                    node="interaction_generator",
                    section_id=sid,
                    message=f"Simulation QC failed: {'; '.join(qc_issues)}",
                    recoverable=True,
                )
            ],
            "media_frame_results": {sid: {slot.slot_id: frame_results}},
            "media_slot_results": {sid: {slot.slot_id: slot_result}},
            "media_lifecycle": {sid: "failed"},
            "completed_nodes": ["interaction_generator"],
        }

    emit_frame_ready(
        generation_id=generation_id,
        section_id=sid,
        slot=slot,
        frame=frame,
    )
    emit_slot_state(
        generation_id=generation_id,
        section_id=sid,
        slot=slot,
        ready_frames=slot_result.completed_frames,
        total_frames=slot_result.total_frames,
        error=slot_result.error_message,
    )
    _publish_interaction_outcome(generation_id, sid, "generated", interaction_count=1)
    return {
        "generated_sections": {sid: preview_section},
        "interaction_specs": {sid: spec},
        "media_frame_results": {sid: {slot.slot_id: frame_results}},
        "media_slot_results": {sid: {slot.slot_id: slot_result}},
        "media_lifecycle": {sid: "generated"},
        "completed_nodes": ["interaction_generator"],
    }
