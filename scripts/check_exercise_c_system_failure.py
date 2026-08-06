#!/usr/bin/env python3
"""Validate Exercise C low-score versus system-failure separation."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision"

from gd_eval.results.evaluation_result import EvaluationBuildError  # noqa: E402
from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.manifest import build_manifest, validate_manifest  # noqa: E402
from gd_eval.vertical_slice.runner import (  # noqa: E402
    compare_oracles,
    run_full_episode,
    transcript_hash,
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
EXPECTED_NE = {
    "logical_reasoning",
    "listening_and_response",
    "decision_and_consensus",
}
UNAFFECTED = {
    "issue_framing",
    "valuable_contribution",
    "collaboration_and_relationship",
    "process_and_time_management",
}


def validate_schema(instance: dict, filename: str) -> None:
    raw = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(raw)
    errors = sorted(
        Draft202012Validator(raw, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        raise AssertionError(
            f"SCHEMA_INVALID: {filename}: {list(first.absolute_path)} {first.message}"
        )


def score_map(result: dict) -> dict[str, int | str]:
    return {item["dimension"]: item["score"] for item in result["candidate_dimensions"]}


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


def set_dimension_ne(runtime, dimension: str, reason: str) -> None:
    for sheet in runtime.rater_sheets:
        entry = next(item for item in sheet["dimensions"] if item["dimension"] == dimension)
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


def set_dimension_numeric(
    runtime,
    dimension: str,
    score: int,
    opportunity_event_ids: list[str],
    message_ids: list[str],
) -> None:
    for sheet in runtime.rater_sheets:
        entry = next(item for item in sheet["dimensions"] if item["dimension"] == dimension)
        entry["score"] = score
        entry["opportunity_status"] = "sufficient"
        entry["opportunity_evidence_event_ids"] = opportunity_event_ids
        entry["selected_evidence_message_ids"] = message_ids
        entry["not_evaluable_reason"] = None
        entry["flags"] = []
    resolution = next(
        item
        for item in runtime.adjudication["dimension_resolutions"]
        if item["dimension"] == dimension
    )
    resolution["rater_scores"] = [score, score]
    resolution["agreement_class"] = "exact"
    resolution["final_score"] = score
    resolution["final_evidence_message_ids"] = message_ids
    resolution["not_evaluable_reason"] = None
    resolution["rubric_issue_code"] = None


def message_signature(
    message: dict,
    *,
    include_content: bool = True,
    include_participant: bool = True,
) -> tuple:
    base = (
        message["message_id"],
        message["speaker_type"],
        message["phase"],
        message["start_ms"],
        message["end_ms"],
        message.get("generation_id"),
    )
    if include_participant:
        base += (message["participant_id"],)
    if include_content:
        base += (message["text"], message["move"])
    return base


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
    if any(
        event.get("event") == "PROHIBITED_CONDITION_TRIGGERED"
        for event in system_loaded.runtime.episode["events"]
    ):
        raise AssertionError("EXPLICIT_PROHIBITED_EVENT_NOT_ALLOWED")
    if system_generated.system_quality["status"] != "fail":
        raise AssertionError("SYSTEM_QUALITY_FAILURE_NOT_DETECTED")

    failed_rules = {
        item["rule_id"]
        for item in system_generated.system_quality["rule_results"]
        if item["outcome"] == "fail"
    }
    if failed_rules != {"C-PROH-01"}:
        raise AssertionError(f"UNEXPECTED_FAILED_RULES: {sorted(failed_rules)}")

    deterministic = {
        item["rule_id"]: item["outcome"]
        for item in system_generated.deterministic_rules["rule_results"]
    }
    if deterministic != {f"C-R0{index}": "pass" for index in range(1, 6)}:
        raise AssertionError(f"SYSTEM_FAILURE_RULE_PROFILE_INVALID: {deterministic}")

    invalid_ids = {
        item["opportunity_id"]
        for item in system_generated.opportunity_resolution["items"]
        if item["status"] == "invalid"
    }
    if invalid_ids != EXPECTED_INVALID:
        raise AssertionError(f"INVALIDATION_SCOPE_MISMATCH: {sorted(invalid_ids)}")
    if system_generated.opportunity_resolution["summary"] != {
        "offered": 8,
        "not_offered": 0,
        "invalid": 7,
        "with_candidate_response": 8,
    }:
        raise AssertionError("SYSTEM_FAILURE_OPPORTUNITY_SUMMARY_INVALID")

    system_scores = score_map(system_generated.evaluation_result)
    ne_dimensions = {
        dimension for dimension, score in system_scores.items() if score == "NE"
    }
    if ne_dimensions != EXPECTED_NE:
        raise AssertionError(f"NE_SCOPE_INVALID: {sorted(ne_dimensions)}")
    for item in system_generated.evaluation_result["candidate_dimensions"]:
        if item["dimension"] in EXPECTED_NE:
            reason = item.get("not_evaluable_reason") or {}
            if reason.get("code") != "AI_QUALITY_FAILURE":
                raise AssertionError(f"NE_REASON_INVALID: {item['dimension']}")
        elif item["not_evaluable_reason"] is not None:
            raise AssertionError(f"NUMERIC_DIMENSION_HAS_NE_REASON: {item['dimension']}")

    feedback_ne = system_generated.feedback.get("not_evaluable_dimensions", {})
    if set(feedback_ne) != EXPECTED_NE:
        raise AssertionError(f"FEEDBACK_NE_SCOPE_INVALID: {sorted(feedback_ne)}")
    for dimension in EXPECTED_NE:
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

    for dimension in UNAFFECTED:
        if system_scores[dimension] != medium_scores[dimension]:
            raise AssertionError(
                f"UNAFFECTED_SCORE_CHANGED: {dimension}: "
                f"{system_scores[dimension]} != {medium_scores[dimension]}"
            )

    medium_messages = {
        item["message_id"]: item for item in medium_loaded.runtime.episode["messages"]
    }
    system_messages = {
        item["message_id"]: item for item in system_loaded.runtime.episode["messages"]
    }
    for message_id, medium_message in medium_messages.items():
        system_message = system_messages[message_id]
        if medium_message["speaker_type"] == "user":
            if message_signature(
                medium_message, include_participant=False
            ) != message_signature(system_message, include_participant=False):
                raise AssertionError(f"CANDIDATE_MESSAGE_CHANGED: {message_id}")
        elif message_id == "m025":
            if message_signature(
                medium_message, include_content=False
            ) != message_signature(system_message, include_content=False):
                raise AssertionError("M025_CONTROL_FIELDS_CHANGED")
            if system_message["move"] != "propose_decision":
                raise AssertionError("M025_NOT_EARLY_DECISION")
            if system_message["text"] == medium_message["text"]:
                raise AssertionError("M025_TEXT_NOT_CHANGED")
        elif message_signature(medium_message) != message_signature(system_message):
            raise AssertionError(f"UNEXPECTED_AI_MESSAGE_CHANGED: {message_id}")

    if low_generated.system_quality["status"] != "pass":
        raise AssertionError("LOW_CASE_SYSTEM_QUALITY_NOT_PASS")
    if any(score == "NE" for score in low_scores.values()):
        raise AssertionError("LOW_CASE_WRONGLY_CONVERTED_TO_NE")

    removed_failure = copy.deepcopy(system_loaded.runtime)
    medium_m025 = medium_messages["m025"]
    system_m025 = next(
        item
        for item in removed_failure.episode["messages"]
        if item["message_id"] == "m025"
    )
    system_m025["text"] = medium_m025["text"]
    system_m025["move"] = medium_m025["move"]
    removed_failure.episode["transcript_hash"] = transcript_hash(
        removed_failure.episode["messages"]
    )
    expect_evaluation_failure(
        removed_failure,
        "AI_QUALITY_NE_WITHOUT_CAUSAL_INSUFFICIENCY",
    )

    invalid_numeric = copy.deepcopy(system_loaded.runtime)
    set_dimension_numeric(
        invalid_numeric,
        "logical_reasoning",
        3,
        ["ev_opp_c_op_lo_01", "ev_opp_c_op_lo_02"],
        ["m020", "m028"],
    )
    expect_evaluation_failure(
        invalid_numeric,
        "INVALIDATED_OPPORTUNITY_NUMERIC_SCORE",
    )

    false_ne = copy.deepcopy(system_loaded.runtime)
    set_dimension_ne(false_ne, "issue_framing", "AI_QUALITY_FAILURE")
    expect_evaluation_failure(
        false_ne,
        "AI_QUALITY_NE_WITHOUT_CAUSAL_INSUFFICIENCY",
    )

    partial_logical_ne = copy.deepcopy(system_loaded.runtime)
    for opportunity in partial_logical_ne.scenario["evaluation_opportunities"]:
        if opportunity["opportunity_id"] == "C-OP-LO-02":
            opportunity["invalidated_by"] = []
    expect_evaluation_failure(
        partial_logical_ne,
        "AI_QUALITY_NE_WITHOUT_CAUSAL_INSUFFICIENCY",
    )

    partial_logical_numeric = copy.deepcopy(partial_logical_ne)
    set_dimension_numeric(
        partial_logical_numeric,
        "logical_reasoning",
        3,
        ["ev_opp_c_op_lo_02"],
        ["m028"],
    )
    partial_generated = run_full_episode(partial_logical_numeric)
    if score_map(partial_generated.evaluation_result)["logical_reasoning"] != 3:
        raise AssertionError("PARTIAL_INVALID_NUMERIC_SCORE_NOT_PRESERVED")

    false_insufficient = copy.deepcopy(low_loaded.runtime)
    set_dimension_ne(
        false_insufficient,
        "logical_reasoning",
        "INSUFFICIENT_OPPORTUNITY",
    )
    expect_evaluation_failure(
        false_insufficient,
        "INSUFFICIENT_OPPORTUNITY_WITH_SUFFICIENT_VALID",
    )

    unsupported_reason = copy.deepcopy(low_loaded.runtime)
    set_dimension_ne(
        unsupported_reason,
        "logical_reasoning",
        "INSUFFICIENT_EVIDENCE",
    )
    expect_evaluation_failure(unsupported_reason, "UNSUPPORTED_NE_REASON")

    mixed_failure = copy.deepcopy(system_loaded.runtime)
    mixed_failure.episode["events"].append(
        {
            "event_id": "ev_early_session_close",
            "event": "SESSION_CLOSED",
            "timestamp_ms": 650000,
        }
    )
    expect_evaluation_failure(
        mixed_failure,
        "INVALIDATED_OPPORTUNITY_NUMERIC_SCORE",
    )

    print("Exercise C system failure separation v0.1 OK")
    print("System failure: 7 invalid opportunities, 3 NE dimensions")
    print("Unaffected dimensions: 4 medium numeric scores preserved")
    print("Low case: 7 numeric scores, no NE")
    print("Feedback NE reasons: preserved")
    print("Single-defect profile: C-PROH-01 only")
    print("AI delta: m025 text and move only")
    print("Negative separation tests: 7 passed")


if __name__ == "__main__":
    main()
