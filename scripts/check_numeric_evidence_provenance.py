#!/usr/bin/env python3
"""Reject numeric ratings supported only by auxiliary opportunities."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_DIR = (
    ROOT
    / "fixtures/calibration/full-episodes/ambiguous-structure/low"
)

from gd_eval.results.evaluation_result import EvaluationBuildError  # noqa: E402
from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.runner import run_full_episode  # noqa: E402


def main() -> None:
    loaded = load_case(CASE_DIR, ROOT)
    auxiliary_only = copy.deepcopy(loaded.runtime)

    for sheet in auxiliary_only.rater_sheets:
        entry = next(
            item
            for item in sheet["dimensions"]
            if item["dimension"] == "logical_reasoning"
        )
        # ev_opp_11 is a valid decision_and_consensus opportunity whose
        # response m017 is target-user-owned, but it is not a primary
        # logical_reasoning opportunity.
        entry["opportunity_evidence_event_ids"] = ["ev_opp_11"]
        entry["selected_evidence_message_ids"] = ["m017"]

    try:
        run_full_episode(auxiliary_only)
    except EvaluationBuildError as exc:
        expected = "PRIMARY_OPPORTUNITY_EVIDENCE_INSUFFICIENT"
        if expected not in str(exc):
            raise AssertionError(
                f"WRONG_FAILURE: expected {expected}, got {exc}"
            ) from exc
    else:
        raise AssertionError("AUXILIARY_ONLY_NUMERIC_SCORE_ACCEPTED")

    print("Numeric evidence provenance v0.1 OK")
    print("Auxiliary-only numeric rating: rejected")


if __name__ == "__main__":
    main()
