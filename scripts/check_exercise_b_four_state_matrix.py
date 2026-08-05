#!/usr/bin/env python3
"""Validate Exercise B high/medium/low/system_failure as one matrix."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calibration_four_state_matrix import (  # noqa: E402
    FourStateMatrixConfig,
    run_four_state_matrix,
)

CONFIG = FourStateMatrixConfig(
    title="Exercise B Four-State Matrix v0.1",
    matrix_id="exercise-b-four-state-v0.1",
    exercise_id="candidate-assessment-b-stakeholder-conflict",
    scenario_version="candidate-assessment-b-v0.1",
    case_root=ROOT / "fixtures/calibration/full-episodes/stakeholder-conflict",
    matrix_json=ROOT / "fixtures/calibration/matrices/exercise-b-four-state-v0.1.json",
    matrix_markdown=ROOT / "fixtures/calibration/matrices/exercise-b-four-state-v0.1.md",
    matrix_schema=ROOT / "schemas/exercise-four-state-matrix-v0.1.schema.json",
    normal_opportunity_summary={
        "offered": 15,
        "not_offered": 0,
        "invalid": 0,
        "with_candidate_response": 15,
    },
    system_failure_opportunity_summary={
        "offered": 11,
        "not_offered": 0,
        "invalid": 4,
        "with_candidate_response": 11,
    },
    system_failure_ne=("issue_framing", "decision_and_consensus"),
    system_failure_failed_rules=("B-PROH-01",),
)

EXPECTED_INVALID = {
    "B-OP-IS-01",
    "B-OP-DE-01",
    "B-OP-DE-02",
    "B-OP-DE-03",
}


def message_signature(
    message: dict[str, Any], include_content: bool = True
) -> tuple[Any, ...]:
    base = (
        message["message_id"],
        message["speaker_type"],
        message["phase"],
        message["start_ms"],
        message["end_ms"],
        message.get("generation_id"),
    )
    return base + ((message["text"], message["move"]) if include_content else ())


def assert_controlled_system_failure(
    loaded_by_state: dict[str, Any],
    generated_by_state: dict[str, Any],
) -> None:
    medium_messages = {
        message["message_id"]: message
        for message in loaded_by_state["medium"].runtime.episode["messages"]
    }
    system_messages = {
        message["message_id"]: message
        for message in loaded_by_state["system_failure"].runtime.episode["messages"]
    }
    if set(medium_messages) != set(system_messages):
        raise AssertionError("SYSTEM_FAILURE_MESSAGE_SET_CHANGED")

    for message_id, medium_message in medium_messages.items():
        system_message = system_messages[message_id]
        if medium_message["speaker_type"] == "user":
            if message_signature(medium_message) != message_signature(system_message):
                raise AssertionError(f"CANDIDATE_MESSAGE_CHANGED: {message_id}")
        elif message_id == "m004":
            if message_signature(medium_message, False) != message_signature(
                system_message, False
            ):
                raise AssertionError("M004_CONTROL_FIELDS_CHANGED")
            if medium_message["move"] != "ask_question":
                raise AssertionError("MEDIUM_M004_CONTROL_INVALID")
            if system_message["move"] != "propose_decision":
                raise AssertionError("SYSTEM_FAILURE_M004_NOT_EARLY_DECISION")
            if medium_message["text"] == system_message["text"]:
                raise AssertionError("SYSTEM_FAILURE_M004_TEXT_NOT_CHANGED")
        elif message_signature(medium_message) != message_signature(system_message):
            raise AssertionError(f"UNEXPECTED_AI_MESSAGE_CHANGED: {message_id}")

    invalid_ids = {
        item["opportunity_id"]
        for item in generated_by_state[
            "system_failure"
        ].opportunity_resolution["items"]
        if item["status"] == "invalid"
    }
    if invalid_ids != EXPECTED_INVALID:
        raise AssertionError(
            f"SYSTEM_FAILURE_INVALID_SCOPE_CHANGED: {sorted(invalid_ids)}"
        )


def main() -> None:
    _, loaded_by_state, generated_by_state = run_four_state_matrix(ROOT, CONFIG)
    assert_controlled_system_failure(loaded_by_state, generated_by_state)
    print("Exercise B four-state matrix v0.1 OK")
    print("Golden replay: exact for 4 full-Episode cases")
    print("Normal states: identical AI quality and 15 opportunities")
    print("Score order: high > medium > low on all 7 dimensions")
    print("Low: 7 numeric dimensions, no NE")
    print("System failure: 5 numeric dimensions, 2 causal NE dimensions")
    print("System failure AI delta: m004 text and move only")
    print("System failure invalid scope: exact 4 opportunities")
    print("Runner state independence: verified")
    print("Matrix JSON and Markdown: exact deterministic replay")


if __name__ == "__main__":
    main()
