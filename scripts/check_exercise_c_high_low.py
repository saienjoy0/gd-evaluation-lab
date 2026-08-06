#!/usr/bin/env python3
"""Validate Exercise C high/medium/low controlled calibration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision"

from calibration_controlled_states import (  # noqa: E402
    assert_controlled_environment,
    assert_low_numeric_and_no_strengths,
    assert_score_four_spans_phases,
    assert_strict_order,
    assert_unique_case_identity,
    load_states,
    rule_map,
    score_map,
)

EXPECTED_SCORES = {
    "high": {
        "issue_framing": 3,
        "logical_reasoning": 4,
        "listening_and_response": 4,
        "valuable_contribution": 4,
        "collaboration_and_relationship": 4,
        "decision_and_consensus": 4,
        "process_and_time_management": 4,
    },
    "medium": {
        "issue_framing": 2,
        "logical_reasoning": 3,
        "listening_and_response": 3,
        "valuable_contribution": 2,
        "collaboration_and_relationship": 2,
        "decision_and_consensus": 3,
        "process_and_time_management": 3,
    },
    "low": {
        "issue_framing": 1,
        "logical_reasoning": 1,
        "listening_and_response": 2,
        "valuable_contribution": 1,
        "collaboration_and_relationship": 1,
        "decision_and_consensus": 1,
        "process_and_time_management": 1,
    },
}


def event_map(episode: dict) -> dict[str, dict]:
    return {event["event_id"]: event for event in episode["events"]}


def assert_prompt_control(loaded_by_state) -> None:
    prompt_versions = {
        loaded.runtime.episode["versions"]["prompt_version"]
        for loaded in loaded_by_state.values()
    }
    if len(prompt_versions) != 1:
        raise AssertionError(f"PROMPT_VERSION_DIFFER: {sorted(prompt_versions)}")


def assert_low_semantic_consistency(loaded) -> None:
    episode = loaded.runtime.episode
    events = event_map(episode)
    if any(
        event.get("event") == "PRIORITY_UPDATE_RECORDED"
        for event in episode["events"]
    ):
        raise AssertionError("LOW_FALSE_PRIORITY_UPDATE")
    if len(events["ev_options_compared"].get("criteria", [])) >= 2:
        raise AssertionError("LOW_FALSE_MULTI_CRITERIA_COMPARISON")
    if events["ev_revision"].get("changed_fields"):
        raise AssertionError("LOW_FALSE_DECISION_REVISION")
    if set(events["ev_summary_fields"].get("fields", [])) >= {
        "mode",
        "exception",
        "next_check",
    }:
        raise AssertionError("LOW_FALSE_COMPLETE_SUMMARY")
    if events["ev_summary"].get("exception") or events["ev_summary"].get(
        "next_check"
    ):
        raise AssertionError("LOW_FALSE_SUMMARY_VALUES")


def assert_candidate_profiles_differ(loaded_by_state) -> None:
    texts = {}
    for state, loaded in loaded_by_state.items():
        texts[state] = [
            message["text"]
            for message in loaded.runtime.episode["messages"]
            if message["speaker_type"] == "user"
        ]
    if texts["high"] == texts["medium"] or texts["medium"] == texts["low"]:
        raise AssertionError("CANDIDATE_PROFILE_NOT_DISTINCT")


def main() -> None:
    loaded_by_state, generated_by_state = load_states(ROOT, CASE_ROOT)
    assert_strict_order(generated_by_state)
    assert_controlled_environment(
        loaded_by_state,
        generated_by_state,
        {
            "offered": 15,
            "not_offered": 0,
            "invalid": 0,
            "with_candidate_response": 15,
        },
    )
    assert_unique_case_identity(loaded_by_state)
    assert_prompt_control(loaded_by_state)
    assert_candidate_profiles_differ(loaded_by_state)
    assert_low_semantic_consistency(loaded_by_state["low"])

    for state, expected in EXPECTED_SCORES.items():
        actual = score_map(generated_by_state[state])
        if actual != expected:
            raise AssertionError(f"SCORE_PROFILE_INVALID: {state}: {actual}")
        if hasattr(loaded_by_state[state].runtime, "state"):
            raise AssertionError(f"RUNTIME_RECEIVED_STATE_LABEL: {state}")

    expected_high = {
        "C-R01": "pass",
        "C-R02": "pass",
        "C-R03": "pass",
        "C-R04": "pass",
        "C-R05": "pass",
    }
    expected_medium = dict(expected_high)
    expected_low = {
        "C-R01": "pass",
        "C-R02": "pass",
        "C-R03": "fail",
        "C-R04": "fail",
        "C-R05": "fail",
    }
    if rule_map(generated_by_state["high"]) != expected_high:
        raise AssertionError("HIGH_RULE_PROFILE_INVALID")
    if rule_map(generated_by_state["medium"]) != expected_medium:
        raise AssertionError("MEDIUM_RULE_PROFILE_INVALID")
    if rule_map(generated_by_state["low"]) != expected_low:
        raise AssertionError("LOW_RULE_PROFILE_INVALID")

    assert_score_four_spans_phases(
        loaded_by_state["high"], generated_by_state["high"]
    )
    assert_low_numeric_and_no_strengths(generated_by_state["low"])

    score_four = [
        item
        for item in generated_by_state["high"].evaluation_result[
            "candidate_dimensions"
        ]
        if item["score"] == 4
    ]
    if len(score_four) != 6:
        raise AssertionError(f"HIGH_SCORE_FOUR_COUNT_INVALID: {len(score_four)}")

    print("Exercise C high/medium/low calibration OK")
    print("Golden replay: exact for 3 cases")
    print("AI messages, System Quality, and 15 opportunity supply: controlled")
    print("Candidate score order: high > medium > low on all 7 dimensions")
    print("High score-4 multi-phase evidence: passed for 6 dimensions")
    print("Low numeric-score and false-strength guards: passed")


if __name__ == "__main__":
    main()
