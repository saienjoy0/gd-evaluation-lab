#!/usr/bin/env python3
"""Validate Exercise B high/medium/low controlled calibration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/stakeholder-conflict"

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
        "issue_framing": 4,
        "logical_reasoning": 4,
        "listening_and_response": 4,
        "valuable_contribution": 4,
        "collaboration_and_relationship": 4,
        "decision_and_consensus": 4,
        "process_and_time_management": 3,
    },
    "medium": {
        "issue_framing": 3,
        "logical_reasoning": 3,
        "listening_and_response": 3,
        "valuable_contribution": 3,
        "collaboration_and_relationship": 3,
        "decision_and_consensus": 3,
        "process_and_time_management": 2,
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



def assert_prompt_control(loaded_by_state) -> None:
    prompt_versions = {
        loaded.runtime.episode["versions"]["prompt_version"]
        for loaded in loaded_by_state.values()
    }
    if len(prompt_versions) != 1:
        raise AssertionError(f"PROMPT_VERSION_DIFFER: {sorted(prompt_versions)}")


def assert_low_semantic_consistency(loaded, generated) -> None:
    events = loaded.runtime.episode["events"]
    decision = next(
        event
        for event in events
        if event.get("event") == "DECISION_ALLOCATION_RECORDED"
    )
    if "mitigation" in decision or "mitigation" in decision.get("fields", []):
        raise AssertionError("LOW_FALSE_MITIGATION_EVENT")
    if any(
        event.get("event") == "MINORITY_CONCERN_STATUS" for event in events
    ):
        raise AssertionError("LOW_FALSE_MINORITY_ADDRESS_EVENT")
    summary = next(
        event
        for event in events
        if event.get("event") == "SUMMARY_FIELDS_RECORDED"
    )
    if summary.get("fields") != ["allocation"]:
        raise AssertionError(
            f"LOW_FALSE_SUMMARY_FIELDS: {summary.get('fields')}"
        )

    dimensions = {
        item["dimension"]: item
        for item in generated.evaluation_result["candidate_dimensions"]
    }
    for group_id, group in generated.feedback["display_groups"].items():
        bottleneck = group["bottleneck_dimension"]
        expected = dimensions[bottleneck]["missing_behavior"]
        if group["summary"] != expected:
            raise AssertionError(
                f"LOW_FALSE_GROUP_SUMMARY: {group_id}: {group['summary']}"
            )


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
    assert_low_semantic_consistency(
        loaded_by_state["low"], generated_by_state["low"]
    )

    for state, expected in EXPECTED_SCORES.items():
        actual = score_map(generated_by_state[state])
        if actual != expected:
            raise AssertionError(f"SCORE_PROFILE_INVALID: {state}: {actual}")
        if hasattr(loaded_by_state[state].runtime, "state"):
            raise AssertionError(f"RUNTIME_RECEIVED_STATE_LABEL: {state}")

    expected_high_rules = {
        "B-R01": "pass",
        "B-R02": "pass",
        "B-R03": "pass",
        "B-R04": "pass",
        "B-R05": "pass",
        "B-R06": "pass",
    }
    expected_low_rules = {
        "B-R01": "pass",
        "B-R02": "fail",
        "B-R03": "fail",
        "B-R04": "fail",
        "B-R05": "pass",
        "B-R06": "pass",
    }
    if rule_map(generated_by_state["high"]) != expected_high_rules:
        raise AssertionError("HIGH_RULE_PROFILE_INVALID")
    if rule_map(generated_by_state["low"]) != expected_low_rules:
        raise AssertionError("LOW_RULE_PROFILE_INVALID")

    assert_score_four_spans_phases(
        loaded_by_state["high"], generated_by_state["high"]
    )
    assert_low_numeric_and_no_strengths(generated_by_state["low"])

    high_dimensions = generated_by_state["high"].evaluation_result[
        "candidate_dimensions"
    ]
    score_four = [item for item in high_dimensions if item["score"] == 4]
    if len(score_four) != 6:
        raise AssertionError(f"HIGH_SCORE_FOUR_COUNT_INVALID: {len(score_four)}")

    print("Exercise B high/medium/low calibration OK")
    print("Golden replay: exact for 3 cases")
    print("AI messages, System Quality, and 15 opportunity supply: controlled")
    print("Candidate score order: high > medium > low on all 7 dimensions")
    print("High score-4 multi-phase evidence: passed for 6 dimensions")
    print("Low numeric-score and false-strength guards: passed")


if __name__ == "__main__":
    main()
