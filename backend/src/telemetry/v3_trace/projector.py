from __future__ import annotations

from telemetry.v3_trace.event_types import (
    ANSWER_KEY_COMPLETED,
    BLUEPRINT_ADJUSTED,
    BLUEPRINT_GENERATED,
    COHERENCE_REVIEWED,
    GENERATION_COMPLETED,
    GENERATION_FAILED,
    GENERATION_STARTED,
    QUESTIONS_COMPLETED,
    REPAIR_ATTEMPTED,
    REPAIR_ESCALATED,
    SECTION_COMPLETED,
    SECTION_FAILED,
    VISUAL_COMPLETED,
    VISUAL_FAILED,
)


def project_report(events: list[dict]) -> dict:
    report: dict = {
        "blueprint": None,
        "execution": {
            "sections": [],
            "visuals": [],
            "questions": [],
            "answer_key": None,
        },
        "review": None,
        "repairs": [],
        "terminal": None,
        "llm_summary": {},
    }

    for event in events:
        event_type = event["event_type"]
        payload = event["payload"]

        if event_type == BLUEPRINT_GENERATED:
            report["blueprint"] = payload

        elif event_type == BLUEPRINT_ADJUSTED:
            if report.get("blueprint_adjustments") is None:
                report["blueprint_adjustments"] = []
            report["blueprint_adjustments"].append(payload)

        elif event_type == GENERATION_STARTED:
            report["generation"] = payload

        elif event_type == SECTION_COMPLETED:
            report["execution"]["sections"].append(
                {
                    "id": payload["section_id"],
                    "title": payload["section_title"],
                    "ok": payload["ok"],
                    "components": payload["component_count"],
                    "warnings": payload.get("warnings", []),
                }
            )

        elif event_type == SECTION_FAILED:
            report["execution"]["sections"].append(
                {
                    "id": payload["section_id"],
                    "title": payload["section_title"],
                    "ok": False,
                    "error_type": payload["error_type"],
                    "error": payload["error_summary"],
                    "node": payload["node"],
                    "attempt": payload["attempt"],
                }
            )

        elif event_type == VISUAL_COMPLETED:
            report["execution"]["visuals"].append(
                {
                    "section_id": payload["section_id"],
                    "mode": payload["mode"],
                    "frames": payload["frame_count"],
                    "ok": payload["ok"],
                }
            )

        elif event_type == VISUAL_FAILED:
            report["execution"]["visuals"].append(
                {
                    "section_id": payload["section_id"],
                    "mode": payload["mode"],
                    "ok": False,
                    "error": payload["error_summary"],
                    "attempt": payload["attempt"],
                }
            )

        elif event_type == QUESTIONS_COMPLETED:
            report["execution"]["questions"].append(
                {
                    "section_id": payload["section_id"],
                    "count": payload["question_count"],
                    "ok": payload["ok"],
                }
            )

        elif event_type == ANSWER_KEY_COMPLETED:
            report["execution"]["answer_key"] = {
                "style": payload["style"],
                "count": payload["question_count"],
                "ok": payload["ok"],
            }

        elif event_type == COHERENCE_REVIEWED:
            report["review"] = payload

        elif event_type in (REPAIR_ATTEMPTED, REPAIR_ESCALATED):
            report["repairs"].append(payload)

        elif event_type in (GENERATION_COMPLETED, GENERATION_FAILED):
            report["terminal"] = payload
            report["llm_summary"] = payload.get("llm_summary", {})

    return report
