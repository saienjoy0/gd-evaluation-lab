#!/usr/bin/env python3
"""Validate Exercise C high/medium/low/system_failure as one matrix."""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calibration_four_state_matrix import (  # noqa: E402
    FourStateMatrixConfig,
    assert_controlled_case_inputs,
    assert_matrix,
    build_matrix,
    run_four_state_matrix,
)

CONFIG = FourStateMatrixConfig(
    title="Exercise C Four-State Matrix v0.1",
    matrix_id="exercise-c-four-state-v0.1",
    exercise_id="candidate-assessment-c-time-boxed-decision",
    scenario_version="candidate-assessment-c-v0.1",
    case_root=ROOT / "fixtures/calibration/full-episodes/time-boxed-decision",
    matrix_json=ROOT / "fixtures/calibration/matrices/exercise-c-four-state-v0.1.json",
    matrix_markdown=ROOT / "fixtures/calibration/matrices/exercise-c-four-state-v0.1.md",
    matrix_schema=ROOT / "schemas/exercise-four-state-matrix-v0.1.schema.json",
    normal_opportunity_summary={
        "offered": 15,
        "not_offered": 0,
        "invalid": 0,
        "with_candidate_response": 15,
    },
    system_failure_opportunity_summary={
        "offered": 8,
        "not_offered": 0,
        "invalid": 7,
        "with_candidate_response": 8,
    },
    system_failure_ne=(
        "logical_reasoning",
        "listening_and_response",
        "decision_and_consensus",
    ),
    system_failure_failed_rules=("C-PROH-01",),
)

EXPECTED_INVALID = {
    "C-OP-LO-01",
    "C-OP-LO-02",
    "C-OP-LI-01",
    "C-OP-LI-02",
    "C-OP-DE-01",
    "C-OP-DE-02",
    "C-OP-DE-03",
}


def candidate_message_signature(message: dict[str, Any]) -> tuple[Any, ...]:
    """Compare candidate behavior while allowing the state-specific participant ID."""
    return (
        message["message_id"],
        message["speaker_type"],
        message["text"],
        message["phase"],
        message["move"],
        message["start_ms"],
        message["end_ms"],
        message.get("generation_id"),
    )


def ai_message_signature(
    message: dict[str, Any], include_content: bool = True
) -> tuple[Any, ...]:
    """AI identity is controlled; only m025 text and move may differ."""
    base = (
        message["message_id"],
        message["participant_id"],
        message["speaker_type"],
        message["phase"],
        message["start_ms"],
        message["end_ms"],
        message.get("generation_id"),
    )
    return base + ((message["text"], message["move"]) if include_content else ())


def ai_participant_signature(episode: dict[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            participant["participant_id"],
            participant["speaker_type"],
            participant.get("agent_role"),
        )
        for participant in episode["participants"]
        if participant["speaker_type"] == "ai"
    )


def assert_controlled_system_failure(
    loaded_by_state: dict[str, Any],
    generated_by_state: dict[str, Any],
) -> None:
    medium_episode = loaded_by_state["medium"].runtime.episode
    system_episode = loaded_by_state["system_failure"].runtime.episode

    if ai_participant_signature(medium_episode) != ai_participant_signature(
        system_episode
    ):
        raise AssertionError("AI_PARTICIPANTS_CHANGED")

    medium_messages = {
        message["message_id"]: message for message in medium_episode["messages"]
    }
    system_messages = {
        message["message_id"]: message for message in system_episode["messages"]
    }
    if set(medium_messages) != set(system_messages):
        raise AssertionError("SYSTEM_FAILURE_MESSAGE_SET_CHANGED")

    for message_id, medium_message in medium_messages.items():
        system_message = system_messages[message_id]
        if medium_message["speaker_type"] == "user":
            if candidate_message_signature(
                medium_message
            ) != candidate_message_signature(system_message):
                raise AssertionError(f"CANDIDATE_MESSAGE_CHANGED: {message_id}")
        elif message_id == "m025":
            if ai_message_signature(
                medium_message, False
            ) != ai_message_signature(system_message, False):
                raise AssertionError("M025_CONTROL_FIELDS_CHANGED")
            if medium_message["move"] == "propose_decision":
                raise AssertionError("MEDIUM_M025_ALREADY_FINALIZES")
            if system_message["move"] != "propose_decision":
                raise AssertionError("SYSTEM_FAILURE_M025_NOT_EARLY_DECISION")
            if medium_message["text"] == system_message["text"]:
                raise AssertionError("SYSTEM_FAILURE_M025_TEXT_NOT_CHANGED")
        elif ai_message_signature(medium_message) != ai_message_signature(
            system_message
        ):
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

    failed_rules = sorted(
        item["rule_id"]
        for item in generated_by_state["system_failure"].system_quality[
            "rule_results"
        ]
        if item["outcome"] == "fail"
    )
    if failed_rules != ["C-PROH-01"]:
        raise AssertionError(f"SYSTEM_FAILURE_RULE_SCOPE_CHANGED: {failed_rules}")

    violation = generated_by_state["system_failure"].evaluation_result[
        "ai_quality"
    ]["violations"]
    if len(violation) != 1 or violation[0].get("message_ids") != ["m025"]:
        raise AssertionError("SYSTEM_FAILURE_CAUSAL_MESSAGE_CHANGED")


def expect_assertion(action: Callable[[], None], expected: str) -> None:
    try:
        action()
    except AssertionError as exc:
        if expected not in str(exc):
            raise AssertionError(
                f"WRONG_NEGATIVE_FAILURE: expected {expected}, got {exc}"
            ) from exc
        return
    raise AssertionError(f"EXPECTED_NEGATIVE_FAILURE_NOT_RAISED: {expected}")


def assert_negative_control_tests(
    matrix: dict[str, Any],
    loaded_by_state: dict[str, Any],
    generated_by_state: dict[str, Any],
) -> None:
    wrong_scenario = copy.deepcopy(loaded_by_state)
    wrong_scenario["high"].runtime.scenario["version"] = "wrong-version"
    expect_assertion(
        lambda: assert_controlled_case_inputs(wrong_scenario, CONFIG),
        "SCENARIO_VERSION_MISMATCH",
    )

    wrong_versions = copy.deepcopy(loaded_by_state)
    wrong_versions["low"].profile.versions["runner_version"] = "wrong-runner"
    expect_assertion(
        lambda: assert_controlled_case_inputs(wrong_versions, CONFIG),
        "VERSION_PROFILE_DIFFER",
    )

    wrong_rubric = copy.deepcopy(loaded_by_state)
    wrong_rubric["system_failure"].runtime.candidate_rubric["version"] = "wrong"
    expect_assertion(
        lambda: assert_controlled_case_inputs(wrong_rubric, CONFIG),
        "CANDIDATE_RUBRIC_DIFFER",
    )

    wrong_speaker = copy.deepcopy(loaded_by_state)
    wrong_m025 = next(
        message
        for message in wrong_speaker["system_failure"].runtime.episode["messages"]
        if message["message_id"] == "m025"
    )
    wrong_m025["participant_id"] = "ai_c_operations"
    expect_assertion(
        lambda: assert_controlled_system_failure(
            wrong_speaker, generated_by_state
        ),
        "M025_CONTROL_FIELDS_CHANGED",
    )

    wrong_timing = copy.deepcopy(loaded_by_state)
    wrong_m025 = next(
        message
        for message in wrong_timing["system_failure"].runtime.episode["messages"]
        if message["message_id"] == "m025"
    )
    wrong_m025["start_ms"] += 1
    expect_assertion(
        lambda: assert_controlled_system_failure(
            wrong_timing, generated_by_state
        ),
        "M025_CONTROL_FIELDS_CHANGED",
    )

    wrong_other_ai = copy.deepcopy(loaded_by_state)
    wrong_m024_ai = next(
        message
        for message in wrong_other_ai["system_failure"].runtime.episode["messages"]
        if message["message_id"] == "m023"
    )
    wrong_m024_ai["text"] = "changed"
    expect_assertion(
        lambda: assert_controlled_system_failure(
            wrong_other_ai, generated_by_state
        ),
        "UNEXPECTED_AI_MESSAGE_CHANGED",
    )

    wrong_candidate = copy.deepcopy(loaded_by_state)
    wrong_user = next(
        message
        for message in wrong_candidate["system_failure"].runtime.episode["messages"]
        if message["speaker_type"] == "user"
    )
    wrong_user["text"] = "changed"
    expect_assertion(
        lambda: assert_controlled_system_failure(
            wrong_candidate, generated_by_state
        ),
        "CANDIDATE_MESSAGE_CHANGED",
    )

    wrong_invalid = copy.deepcopy(generated_by_state)
    invalid_item = next(
        item
        for item in wrong_invalid["system_failure"].opportunity_resolution[
            "items"
        ]
        if item["status"] == "invalid"
    )
    invalid_item["status"] = "offered"
    expect_assertion(
        lambda: assert_controlled_system_failure(
            loaded_by_state, wrong_invalid
        ),
        "SYSTEM_FAILURE_INVALID_SCOPE_CHANGED",
    )

    wrong_matrix_rule = copy.deepcopy(matrix)
    system_case = next(
        case for case in wrong_matrix_rule["cases"] if case["state"] == "system_failure"
    )
    system_case["failed_system_rules"] = ["C-PROH-01", "C-PROH-02"]
    expect_assertion(
        lambda: assert_matrix(wrong_matrix_rule, CONFIG),
        "SYSTEM_FAILURE_RULE_SCOPE_INVALID",
    )

    wrong_unaffected = copy.deepcopy(matrix)
    system_case = next(
        case for case in wrong_unaffected["cases"] if case["state"] == "system_failure"
    )
    system_case["scores"]["valuable_contribution"] = 1
    expect_assertion(
        lambda: assert_matrix(wrong_unaffected, CONFIG),
        "SYSTEM_FAILURE_UNAFFECTED_CHANGED",
    )

    wrong_low = copy.deepcopy(matrix)
    low_case = next(case for case in wrong_low["cases"] if case["state"] == "low")
    low_case["numeric_dimensions"] = 6
    low_case["ne_dimensions"] = ["logical_reasoning"]
    expect_assertion(
        lambda: assert_matrix(wrong_low, CONFIG),
        "NORMAL_NUMERIC_PROFILE_INVALID",
    )

    rebuilt = build_matrix(ROOT, CONFIG, loaded_by_state, generated_by_state)
    if rebuilt != matrix:
        raise AssertionError("NEGATIVE_TEST_BASELINE_MATRIX_CHANGED")


def main() -> None:
    matrix, loaded_by_state, generated_by_state = run_four_state_matrix(
        ROOT, CONFIG
    )
    assert_controlled_system_failure(loaded_by_state, generated_by_state)
    assert_negative_control_tests(matrix, loaded_by_state, generated_by_state)
    print("Exercise C four-state matrix v0.1 OK")
    print("Golden replay: exact for 4 full-Episode cases")
    print("Normal states: identical AI quality and 15 opportunities")
    print("Score order: high > medium > low on all 7 dimensions")
    print("Low: 7 numeric dimensions, no NE")
    print("System failure: 4 numeric dimensions, 3 causal NE dimensions")
    print("System failure AI delta: m025 text and move only")
    print("System failure invalid scope: exact 7 opportunities")
    print("Scenario, version, rubric, and AI identity controls: verified")
    print("Negative control regressions: 11 passed")
    print("Runner state independence: verified")
    print("Matrix JSON and Markdown: exact deterministic replay")


if __name__ == "__main__":
    main()
