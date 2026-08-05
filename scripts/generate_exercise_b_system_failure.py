#!/usr/bin/env python3
"""Generate Exercise B system-failure source fixtures and deterministic goldens."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/stakeholder-conflict"
MEDIUM_ROOT = CASE_ROOT / "medium"
DESTINATION = CASE_ROOT / "system_failure"
SESSION_ID = "exercise-b-system-failure-001"
TARGET_ID = "candidate_b_system_failure"
NE_DIMENSIONS = {
    "issue_framing": ["ev_opp_b_is_01"],
    "decision_and_consensus": [
        "ev_opp_b_de_01",
        "ev_opp_b_de_02",
        "ev_opp_b_de_03",
    ],
}

from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.runner import (  # noqa: E402
    run_full_episode,
    transcript_hash,
    write_generated,
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def replace_identity(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: replace_identity(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_identity(item, old, new) for item in value]
    return new if value == old else value


def build_case() -> dict[str, Any]:
    case = read_json(MEDIUM_ROOT / "case.json")
    case["case_id"] = SESSION_ID
    case["state"] = "system_failure"
    case["target_participant_id"] = TARGET_ID
    return case


def build_episode() -> dict[str, Any]:
    episode = read_json(MEDIUM_ROOT / "episode.json")
    episode = replace_identity(episode, "candidate_b_medium", TARGET_ID)
    episode["session_id"] = SESSION_ID
    episode["started_at"] = "2026-08-05T12:00:00Z"
    episode["ended_at"] = "2026-08-05T12:15:00Z"
    message = next(item for item in episode["messages"] if item["message_id"] == "m004")
    message["text"] = (
        "追加予算は子育て1700万円、地域交通1300万円とし、"
        "観光は既存事業で対応する形で進めましょう。"
    )
    message["move"] = "propose_decision"
    episode.setdefault("versions", {})["prompt_version"] = (
        "exercise-b-system-failure-script-v0.1"
    )
    episode["transcript_hash"] = transcript_hash(episode["messages"])
    return episode


def build_rater(suffix: str) -> dict[str, Any]:
    sheet = read_json(MEDIUM_ROOT / f"rater-sheet-{suffix}.json")
    sheet["sheet_id"] = f"rater-{suffix}-{SESSION_ID}"
    sheet["episode_id"] = SESSION_ID
    sheet["calibration_set_version"] = "exercise-b-system-failure-v0.1"
    sheet["started_at"] = "2026-08-05T12:20:00Z"
    sheet["completed_at"] = "2026-08-05T12:35:00Z"
    for item in sheet["dimensions"]:
        dimension = item["dimension"]
        if dimension not in NE_DIMENSIONS:
            continue
        item["score"] = "NE"
        item["opportunity_status"] = "insufficient"
        item["opportunity_evidence_event_ids"] = NE_DIMENSIONS[dimension]
        item["selected_evidence_message_ids"] = []
        item["confidence"] = 0.95
        item["comment"] = (
            "AIが候補者より先に配分を確定し、主要評価機会が因果的に無効化された。"
        )
        item["not_evaluable_reason"] = "AI_QUALITY_FAILURE"
        item["flags"] = ["OPPORTUNITY_ISSUE"]
    sheet["overall_notes"] = (
        "Exercise B system_failureとして、影響2軸だけをNEへ分離した。"
    )
    return sheet


def build_adjudication() -> dict[str, Any]:
    adjudication = read_json(MEDIUM_ROOT / "adjudication.json")
    adjudication["adjudication_id"] = f"adj-{SESSION_ID}"
    adjudication["episode_id"] = SESSION_ID
    adjudication["rater_sheet_ids"] = [
        f"rater-a-{SESSION_ID}",
        f"rater-b-{SESSION_ID}",
    ]
    adjudication["created_at"] = "2026-08-05T12:50:00Z"
    for item in adjudication["dimension_resolutions"]:
        if item["dimension"] not in NE_DIMENSIONS:
            continue
        item["rater_scores"] = ["NE", "NE"]
        item["agreement_class"] = "exact"
        item["final_score"] = "NE"
        item["final_evidence_message_ids"] = []
        item["resolution_reason"] = (
            "B-PROH-01により主要機会が無効化され、候補者能力として採点できない。"
        )
        item["not_evaluable_reason"] = "AI_QUALITY_FAILURE"
        item["rubric_issue_code"] = "PROCESS_DEVIATION"
    adjudication["overall_resolution_notes"] = (
        "AI先回りと因果関係のある2軸だけをNEとし、影響外5軸はmediumを維持した。"
    )
    return adjudication


def main() -> None:
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    DESTINATION.mkdir(parents=True)
    write_json(DESTINATION / "case.json", build_case())
    write_json(DESTINATION / "episode.json", build_episode())
    write_json(DESTINATION / "rater-sheet-a.json", build_rater("a"))
    write_json(DESTINATION / "rater-sheet-b.json", build_rater("b"))
    write_json(DESTINATION / "adjudication.json", build_adjudication())
    loaded = load_case(DESTINATION, ROOT)
    generated = run_full_episode(loaded.runtime)
    write_generated(DESTINATION, generated)
    (DESTINATION / "feedback.json").replace(
        DESTINATION / "expected-feedback.json"
    )
    print("Generated Exercise B system_failure fixture")


if __name__ == "__main__":
    main()
