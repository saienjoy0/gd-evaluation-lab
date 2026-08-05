#!/usr/bin/env python3
"""Validate Exercise A high/medium/low calibration cases."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/ambiguous-structure"

from calibration_controlled_states import (  # noqa: E402
    assert_controlled_environment,
    assert_low_numeric_and_no_strengths,
    assert_score_four_spans_phases,
    assert_strict_order,
    assert_unique_case_identity,
    load_states,
    rule_map,
)


def main() -> None:
    loaded_by_state, generated_by_state = load_states(ROOT, CASE_ROOT)
    assert_strict_order(generated_by_state)
    assert_controlled_environment(
        loaded_by_state,
        generated_by_state,
        {
            "offered": 12,
            "not_offered": 0,
            "invalid": 0,
            "with_candidate_response": 12,
        },
    )
    assert_unique_case_identity(loaded_by_state)

    if rule_map(generated_by_state["high"]) != {
        "A-R01": "pass",
        "A-R02": "pass",
        "A-R03": "pass",
        "A-R04": "pass",
        "A-R05": "pass",
    }:
        raise AssertionError("HIGH_RULE_PROFILE_INVALID")

    if rule_map(generated_by_state["low"]) != {
        "A-R01": "pass",
        "A-R02": "fail",
        "A-R03": "fail",
        "A-R04": "pass",
        "A-R05": "fail",
    }:
        raise AssertionError("LOW_RULE_PROFILE_INVALID")

    assert_score_four_spans_phases(
        loaded_by_state["high"], generated_by_state["high"]
    )
    assert_low_numeric_and_no_strengths(generated_by_state["low"])

    print("Exercise A high/medium/low calibration OK")
    print("Golden replay: exact for 3 cases")
    print("AI messages, AI quality, and 12 opportunity supply: controlled")
    print("Candidate score order: high > medium > low on all 7 dimensions")
    print("High score-4 multi-phase evidence: passed")
    print("Low numeric-score and false-strength guards: passed")


if __name__ == "__main__":
    main()
