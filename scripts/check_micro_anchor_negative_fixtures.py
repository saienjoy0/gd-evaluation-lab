#!/usr/bin/env python3
"""Run fail-closed negative controls for the Micro Anchor foundation."""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from micro_anchor_contract import AnchorValidationError, load_json, validate_anchor  # noqa: E402
from micro_anchor_set import validate_anchor_collection  # noqa: E402


def clone_anchor(anchor_id: str) -> tuple[dict[str, Any], Path]:
    path = (
        ROOT
        / "fixtures"
        / "anchors"
        / "issue_framing"
        / f"{anchor_id}.json"
    )
    return copy.deepcopy(load_json(path)), path


def apply_anchor_mutation(
    mutation: str,
) -> tuple[dict[str, Any], Path]:
    baseline, baseline_path = clone_anchor("anchor-if-1-001")
    if mutation == "numeric_evidence_empty":
        baseline["expected_evidence_message_ids"] = []
    elif mutation == "score4_one_evidence":
        baseline, baseline_path = clone_anchor("anchor-if-4-001")
        baseline["expected_evidence_message_ids"] = ["m003"]
    elif mutation == "evidence_owner_ai":
        baseline["expected_evidence_message_ids"] = ["m001"]
    elif mutation == "evidence_missing":
        baseline["expected_evidence_message_ids"] = ["m999"]
    elif mutation == "ne_evidence_present":
        baseline, baseline_path = clone_anchor("anchor-if-ne-001")
        baseline["expected_evidence_message_ids"] = ["m005"]
    elif mutation == "ne_reason_missing":
        baseline, baseline_path = clone_anchor("anchor-if-ne-001")
        baseline["expected_not_evaluable_reason"] = None
    elif mutation == "numeric_reason_present":
        baseline["expected_not_evaluable_reason"] = "AI_QUALITY_FAILURE"
    elif mutation == "score1_insufficient":
        baseline["opportunity_description"]["status"] = "insufficient"
    elif mutation == "too_short":
        baseline["micro_episode"] = baseline["micro_episode"][:2]
    elif mutation == "too_long":
        last = baseline["micro_episode"][-1]
        for index in (7, 8, 9):
            extra = copy.deepcopy(last)
            extra["message_id"] = f"m{index:03d}"
            extra["sequence_index"] = index
            baseline["micro_episode"].append(extra)
    elif mutation == "duplicate_message":
        duplicate = copy.deepcopy(baseline["micro_episode"][-1])
        duplicate["sequence_index"] = 7
        duplicate["message_id"] = "m001"
        baseline["micro_episode"].append(duplicate)
    elif mutation == "path_dimension_mismatch":
        baseline_path = (
            ROOT
            / "fixtures"
            / "anchors"
            / "logical_reasoning"
            / baseline_path.name
        )
    elif mutation == "id_dimension_mismatch":
        baseline["anchor_id"] = "anchor-lr-1-001"
    elif mutation == "forbidden_inference":
        baseline["rationale"] = "外向的な性格だから課題設定が得意だと判断した。"
    elif mutation == "approved_without_reviewer":
        baseline["approval_status"] = "approved"
        baseline["reviewer"] = None
    else:
        raise AssertionError(f"UNKNOWN_NEGATIVE_MUTATION: {mutation}")
    return baseline, baseline_path


def expect_error(action: Any, expected: str, case_id: str) -> None:
    try:
        action()
    except (AnchorValidationError, AssertionError) as exc:
        if expected not in str(exc):
            raise AssertionError(
                f"NEGATIVE_CASE_WRONG_ERROR: {case_id}: "
                f"expected {expected}, got {exc}"
            ) from exc
        return
    raise AssertionError(
        f"NEGATIVE_CASE_DID_NOT_FAIL: {case_id}: {expected}"
    )


def run_set_case(mutation: str) -> None:
    paths = sorted(
        (
            ROOT
            / "fixtures"
            / "anchors"
            / "issue_framing"
        ).glob("anchor-*.json")
    )
    anchors = [load_json(path) for path in paths]
    if mutation == "coverage_missing":
        anchors = [
            anchor for anchor in anchors
            if anchor["anchor_id"] != "anchor-if-3-001"
        ]
    elif mutation == "cell_duplicated":
        duplicate = copy.deepcopy(anchors[0])
        duplicate["anchor_id"] = "anchor-if-1-002"
        anchors.append(duplicate)
    else:
        raise AssertionError(f"UNKNOWN_SET_MUTATION: {mutation}")
    validate_anchor_collection(anchors)


def main() -> int:
    suite = load_json(
        ROOT / "fixtures" / "negative" / "micro-anchors" / "cases.json"
    )
    for case in suite["cases"]:
        if case["scope"] == "anchor":
            anchor, path = apply_anchor_mutation(case["mutation"])
            expect_error(
                lambda anchor=anchor, path=path: validate_anchor(
                    anchor, path, ROOT
                ),
                case["expected_error"],
                case["case_id"],
            )
        else:
            expect_error(
                lambda mutation=case["mutation"]: run_set_case(mutation),
                case["expected_error"],
                case["case_id"],
            )
    print("Micro Anchor negative fixtures OK")
    print(f"Negative cases: {len(suite['cases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
