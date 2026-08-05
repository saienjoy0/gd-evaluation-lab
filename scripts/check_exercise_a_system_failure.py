#!/usr/bin/env python3
"""Validate Exercise A low-score versus system-failure separation."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/ambiguous-structure"

from gd_eval.results.evaluation_result import EvaluationBuildError  # noqa: E402
from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.manifest import build_manifest, validate_manifest  # noqa: E402
from gd_eval.vertical_slice.runner import compare_oracles, run_full_episode  # noqa: E402


def validate_schema(instance: dict, filename: str) -> None:
    raw = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(raw)
    errors = sorted(
        Draft202012Validator(
            raw, format_checker=FormatChecker()
        ).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        raise AssertionError(
            f"SCHEMA_INVALID: {filename}: {list(first.absolute_path)} {first.message}"
        )


def expect_schema_failure(instance: dict, filename: str) -> None:
    raw = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    errors = list(
        Draft202012Validator(
            raw, format_checker=FormatChecker()
        ).iter_errors(instance)
    )
    if not errors:
        raise AssertionError(f"EXPECTED_SCHEMA_FAILURE_NOT_RAISED: {filename}")


def score_map(result: dict) -> dict[str, int | str]:
    return {
        item["dimension"]: item["score"]
        for item in result["candidate_dimensions"]
    }


def expect_evaluation_failure(runtime, expected: str) -> None:
    try:
        run_full_episode(runtime)
    except EvaluationBuildError as exc:
        if expected not in str(exc):
            raise AssertionError(
                f"WRONG_FAILURE: expected {expected}, got {exc}"
            ) from exc
        return
    raise AssertionError(f"EXPECTED_FAILURE_NOT_RAISED: {expected}")


def _make_one_valuable_opportunity_valid(runtime) -> None:
    opportunity = next(
        item
        for item in runtime.scenario["evaluation_opportunities"]
        if item["opportunity_id"] == "A-OP-VA-02"
    )
    opportunity["invalidated_by"] = []


def _score_valuable_contribution_numerically(runtime, score: int = 2) -> None:
    for sheet in runtime.rater_sheets:
        entry = next(
            item
            for item in sheet["dimensions"]
            if item["dimension"] == "valuable_contribution"
        )
        entry["score"] = score
        entry["opportunity_status"] = "sufficient"
        entry["opportunity_evidence_event_ids"] = ["ev_opp_09"]
        entry["selected_evidence_message_ids"] = ["m016"]
        entry["not_evaluable_reason"] = None
        entry["flags"] = []
    resolution = next(
        item
        for item in runtime.adjudication["dimension_resolutions"]
        if item["dimension"] == "valuable_contribution"
    )
    resolution["rater_scores"] = [score, score]
    resolution["agreement_class"] = "exact"
    resolution["final_score"] = score
    resolution["final_evidence_message_ids"] = ["m016"]
    resolution["not_evaluable_reason"] = None
    resolution["rubric_issue_code"] = None


def _set_dimension_ne(runtime, dimension: str, reason: str) -> None:
    for sheet in runtime.rater_sheets:
        entry = next(
            item for item in sheet["dimensions"] if item["dimension"] == dimension
        )
        entry["score"] = "NE"
        entry["opportunity_status"] = "insufficient"
        entry["selected_evidence_message_ids"] = []
        entry["not_evaluable_reason"] = reason
        entry["flags"] = ["OPPORTUNITY_ISSUE"]
    resolution = next(
        item
        for item in runtime.adjudication["dimension_resolutions"]
        if item["dimension"] == dimension
    )
    resolution["rater_scores"] = ["NE", "NE"]
    resolution["agreement_class"] = "exact"
    resolution["final_score"] = "NE"
    resolution["final_evidence_message_ids"] = []
    resolution["not_evaluable_reason"] = reason
    resolution["rubric_issue_code"] = "PROCESS_DEVIATION"


def main() -> None:
    system_loaded = load_case(CASE_ROOT / "system_failure", ROOT)
    system_generated = run_full_episode(system_loaded.runtime)
    compare_oracles(system_generated, system_loaded.oracle_paths)
    if run_full_episode(system_loaded.runtime) != system_generated:
        raise AssertionError("NONDETERMINISTIC_SYSTEM_FAILURE_OUTPUT")

    manifest = build_manifest(
        system_loaded.profile,
        system_loaded.runtime,
        system_generated,
        system_loaded.oracle_paths,
    )
    validate_manifest(manifest)
    validate_schema(
        system_generated.deterministic_rules,
        "deterministic-rule-result-v0.1.schema.json",
    )
    validate_schema(
        system_generated.system_quality,
        "system-quality-result-v0.1.schema.json",
    )
    validate_schema(
        system_generated.opportunity_resolution,
        "opportunity-resolution-v0.1.schema.json",
    )
    validate_schema(
        system_generated.evaluation_result,
        "evaluation-result-v0.1.schema.json",
    )
    validate_schema(manifest, "full-episode-manifest-v0.1.schema.json")

    if system_loaded.profile.state != "system_failure":
        raise AssertionError("SYSTEM_FAILURE_STATE_MISSING")
    if system_generated.system_quality["status"] != "fail":
        raise AssertionError("SYSTEM_QUALITY_FAILURE_NOT_DETECTED")

    failed_rules = {
        item["rule_id"]
        for item in system_generated.system_quality["rule_results"]
        if item["outcome"] == "fail"
    }
    if failed_rules != {"A-R01", "A-PROH-01"}:
        raise AssertionError(f"UNEXPECTED_FAILED_RULES: {sorted(failed_rules)}")

    deterministic = {
        item["rule_id"]: item["outcome"]
        for item in system_generated.deterministic_rules["rule_results"]
    }
    if deterministic != {
        "A-R01": "fail",
        "A-R02": "pass",
        "A-R03": "pass",
        "A-R04": "pass",
        "A-R05": "pass",
    }:
        raise AssertionError(f"SYSTEM_FAILURE_RULE_PROFILE_INVALID: {deterministic}")

    invalid_ids = {
        item["opportunity_id"]
        for item in system_generated.opportunity_resolution["items"]
        if item["status"] == "invalid"
    }
    expected_invalid = {
        "A-OP-IS-01",
        "A-OP-IS-02",
        "A-OP-IS-03",
        "A-OP-VA-01",
        "A-OP-VA-02",
    }
    if invalid_ids != expected_invalid:
        raise AssertionError(
            f"INVALIDATION_SCOPE_MISMATCH: {sorted(invalid_ids)}"
        )
    if system_generated.opportunity_resolution["summary"] != {
        "offered": 7,
        "not_offered": 0,
        "invalid": 5,
        "with_candidate_response": 7,
    }:
        raise AssertionError("SYSTEM_FAILURE_OPPORTUNITY_SUMMARY_INVALID")

    system_scores = score_map(system_generated.evaluation_result)
    ne_dimensions = {
        dimension for dimension, score in system_scores.items() if score == "NE"
    }
    if ne_dimensions != {"issue_framing", "valuable_contribution"}:
        raise AssertionError(f"NE_SCOPE_INVALID: {sorted(ne_dimensions)}")
    for item in system_generated.evaluation_result["candidate_dimensions"]:
        if item["dimension"] in ne_dimensions:
            if item["not_evaluable_reason"]["code"] != "AI_QUALITY_FAILURE":
                raise AssertionError(
                    f"NE_REASON_INVALID: {item['dimension']}"
                )
        elif item["not_evaluable_reason"] is not None:
            raise AssertionError(
                f"NUMERIC_DIMENSION_HAS_NE_REASON: {item['dimension']}"
            )

    feedback_ne = system_generated.feedback.get("not_evaluable_dimensions", {})
    if set(feedback_ne) != ne_dimensions:
        raise AssertionError(
            f"FEEDBACK_NE_SCOPE_INVALID: {sorted(feedback_ne)}"
        )
    for dimension in ne_dimensions:
        entry = feedback_ne[dimension]
        if (
            entry.get("evaluation_status") != "not_evaluable"
            or entry.get("reason_code") != "AI_QUALITY_FAILURE"
            or not entry.get("reason")
        ):
            raise AssertionError(f"FEEDBACK_NE_REASON_MISSING: {dimension}")

    medium_loaded = load_case(CASE_ROOT / "medium", ROOT)
    low_loaded = load_case(CASE_ROOT / "low", ROOT)
    medium_generated = run_full_episode(medium_loaded.runtime)
    low_generated = run_full_episode(low_loaded.runtime)
    medium_scores = score_map(medium_generated.evaluation_result)
    low_scores = score_map(low_generated.evaluation_result)

    unaffected = {
        "logical_reasoning",
        "listening_and_response",
        "collaboration_and_relationship",
        "decision_and_consensus",
        "process_and_time_management",
    }
    for dimension in unaffected:
        if system_scores[dimension] != medium_scores[dimension]:
            raise AssertionError(
                "UNAFFECTED_SCORE_CHANGED: "
                f"{dimension}: {system_scores[dimension]} != "
                f"{medium_scores[dimension]}"
            )

    if low_generated.system_quality["status"] != "pass":
        raise AssertionError("LOW_CASE_SYSTEM_QUALITY_NOT_PASS")
    if any(score == "NE" for score in low_scores.values()):
        raise AssertionError("LOW_CASE_WRONGLY_CONVERTED_TO_NE")
    if not all(
        isinstance(score, int) and score <= 2
        for score in low_scores.values()
    ):
        raise AssertionError("LOW_CASE_NUMERIC_PROFILE_INVALID")

    invalid_numeric = copy.deepcopy(system_loaded.runtime)
    for sheet in invalid_numeric.rater_sheets:
        entry = next(
            item for item in sheet["dimensions"]
            if item["dimension"] == "issue_framing"
        )
        entry["score"] = 2
        entry["opportunity_status"] = "sufficient"
        entry["selected_evidence_message_ids"] = ["m004"]
        entry["not_evaluable_reason"] = None
        entry["flags"] = []
    resolution = next(
        item for item in invalid_numeric.adjudication["dimension_resolutions"]
        if item["dimension"] == "issue_framing"
    )
    resolution["rater_scores"] = [2, 2]
    resolution["final_score"] = 2
    resolution["final_evidence_message_ids"] = ["m004"]
    resolution["not_evaluable_reason"] = None
    resolution["rubric_issue_code"] = None
    expect_evaluation_failure(
        invalid_numeric, "INVALIDATED_OPPORTUNITY_NUMERIC_SCORE"
    )

    false_ne = copy.deepcopy(system_loaded.runtime)
    _set_dimension_ne(false_ne, "logical_reasoning", "AI_QUALITY_FAILURE")
    expect_evaluation_failure(
        false_ne, "AI_QUALITY_NE_WITHOUT_CAUSAL_INSUFFICIENCY"
    )

    partial_invalid_ne = copy.deepcopy(system_loaded.runtime)
    _make_one_valuable_opportunity_valid(partial_invalid_ne)
    expect_evaluation_failure(
        partial_invalid_ne, "AI_QUALITY_NE_WITHOUT_CAUSAL_INSUFFICIENCY"
    )

    partial_invalid_numeric = copy.deepcopy(system_loaded.runtime)
    _make_one_valuable_opportunity_valid(partial_invalid_numeric)
    _score_valuable_contribution_numerically(partial_invalid_numeric)
    partial_generated = run_full_episode(partial_invalid_numeric)
    if score_map(partial_generated.evaluation_result)["valuable_contribution"] != 2:
        raise AssertionError("PARTIAL_INVALID_NUMERIC_SCORE_NOT_PRESERVED")
    partial_opportunities = [
        item
        for item in partial_generated.opportunity_resolution["items"]
        if item["dimension"] == "valuable_contribution"
    ]
    if {item["status"] for item in partial_opportunities} != {
        "invalid",
        "offered",
    }:
        raise AssertionError("PARTIAL_INVALID_OPPORTUNITY_PROFILE_INVALID")

    false_insufficient = copy.deepcopy(low_loaded.runtime)
    _set_dimension_ne(
        false_insufficient, "logical_reasoning", "INSUFFICIENT_OPPORTUNITY"
    )
    expect_evaluation_failure(
        false_insufficient, "INSUFFICIENT_OPPORTUNITY_WITH_SUFFICIENT_VALID"
    )

    unsupported_reason = copy.deepcopy(low_loaded.runtime)
    _set_dimension_ne(
        unsupported_reason, "logical_reasoning", "INSUFFICIENT_EVIDENCE"
    )
    expect_evaluation_failure(
        unsupported_reason, "UNSUPPORTED_NE_REASON"
    )

    missing_opportunity_provenance = copy.deepcopy(system_loaded.runtime)
    missing_entry = next(
        item
        for item in missing_opportunity_provenance.rater_sheets[0]["dimensions"]
        if item["dimension"] == "logical_reasoning"
    )
    missing_entry["opportunity_evidence_event_ids"] = []
    expect_schema_failure(
        missing_opportunity_provenance.rater_sheets[0],
        "rater-sheet-v0.1.schema.json",
    )
    expect_evaluation_failure(
        missing_opportunity_provenance, "NUMERIC_OPPORTUNITY_EVIDENCE_MISSING"
    )

    unrelated_rater_evidence = copy.deepcopy(system_loaded.runtime)
    unrelated_entry = next(
        item
        for item in unrelated_rater_evidence.rater_sheets[0]["dimensions"]
        if item["dimension"] == "logical_reasoning"
    )
    unrelated_entry["selected_evidence_message_ids"] = ["m011"]
    expect_evaluation_failure(
        unrelated_rater_evidence, "EVIDENCE_NOT_LINKED_TO_OPPORTUNITY"
    )

    unrelated_adjudication_evidence = copy.deepcopy(system_loaded.runtime)
    unrelated_resolution = next(
        item
        for item in unrelated_adjudication_evidence.adjudication[
            "dimension_resolutions"
        ]
        if item["dimension"] == "logical_reasoning"
    )
    unrelated_resolution["final_evidence_message_ids"] = ["m011"]
    expect_evaluation_failure(
        unrelated_adjudication_evidence,
        "ADJUDICATION_EVIDENCE_NOT_LINKED_TO_OPPORTUNITY",
    )

    print("Exercise A system failure separation v0.1 OK")
    print("System failure: 5 invalid opportunities, 2 NE dimensions")
    print("Unaffected dimensions: 5 numeric scores preserved")
    print("Low case: 7 numeric scores, no NE")
    print("Feedback NE reasons: preserved")
    print("Partial invalidation: NE rejected, numeric score preserved")
    print("NE reason handling: fail closed")
    print("Numeric evidence: opportunity provenance enforced")
    print("Negative separation tests: 8 passed")


if __name__ == "__main__":
    main()
