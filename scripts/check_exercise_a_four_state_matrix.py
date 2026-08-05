#!/usr/bin/env python3
"""Validate Exercise A high/medium/low/system_failure as one matrix."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calibration_four_state_matrix import (  # noqa: E402
    FourStateMatrixConfig,
    run_four_state_matrix,
)

CONFIG = FourStateMatrixConfig(
    title="Exercise A Four-State Matrix v0.1",
    matrix_id="exercise-a-four-state-v0.1",
    exercise_id="candidate-assessment-a-ambiguous-structure",
    scenario_version="candidate-assessment-a-v0.1",
    case_root=ROOT / "fixtures/calibration/full-episodes/ambiguous-structure",
    matrix_json=ROOT / "fixtures/calibration/matrices/exercise-a-four-state-v0.1.json",
    matrix_markdown=ROOT / "fixtures/calibration/matrices/exercise-a-four-state-v0.1.md",
    matrix_schema=ROOT / "schemas/exercise-four-state-matrix-v0.1.schema.json",
    normal_opportunity_summary={
        "offered": 12,
        "not_offered": 0,
        "invalid": 0,
        "with_candidate_response": 12,
    },
    system_failure_opportunity_summary={
        "offered": 7,
        "not_offered": 0,
        "invalid": 5,
        "with_candidate_response": 7,
    },
    system_failure_ne=("issue_framing", "valuable_contribution"),
    system_failure_failed_rules=("A-PROH-01", "A-R01"),
)


def main() -> None:
    run_four_state_matrix(ROOT, CONFIG)
    print("Exercise A four-state matrix v0.1 OK")
    print("Golden replay: exact for 4 full-Episode cases")
    print("Normal states: identical AI quality and 12 opportunities")
    print("Score order: high > medium > low on all 7 dimensions")
    print("Low: 7 numeric dimensions, no NE")
    print("System failure: 5 numeric dimensions, 2 causal NE dimensions")
    print("Runner state independence: verified")
    print("Matrix JSON and Markdown: exact deterministic replay")


if __name__ == "__main__":
    main()
