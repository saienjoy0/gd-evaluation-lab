#!/usr/bin/env python3
"""Validate Exercise A high/medium/low calibration cases."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/ambiguous-structure"
STATES = ("high", "medium", "low")

from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.manifest import build_manifest, validate_manifest  # noqa: E402
from gd_eval.vertical_slice.runner import compare_oracles, run_full_episode  # noqa: E402


def schema(instance: dict, filename: str) -> None:
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


def score_map(generated) -> dict[str, int]:
    return {
        item["dimension"]: int(item["score"])
        for item in generated.evaluation_result["candidate_dimensions"]
    }


def rule_map(generated) -> dict[str, str]:
    return {
        item["rule_id"]: item["outcome"]
        for item in generated.deterministic_rules["rule_results"]
    }


def ai_message_signature(episode: dict) -> list[tuple]:
    return [
        (
            message["participant_id"],
            message["text"],
            message["phase"],
            message["move"],
            message["start_ms"],
            message["end_ms"],
            message.get("generation_id"),
        )
        for message in episode["messages"]
        if message["speaker_type"] == "ai"
    ]


def assert_score_four_spans_phases(loaded, generated) -> None:
    phase_by_message = {
        message["message_id"]: message["phase"]
        for message in loaded.runtime.episode["messages"]
    }
    for dimension in generated.evaluation_result["candidate_dimensions"]:
        if dimension["score"] != 4:
            continue
        phases = {
            phase_by_message[message_id]
            for message_id in dimension["evidence_message_ids"]
        }
        if len(phases) < 2:
            raise AssertionError(
                f"SCORE_FOUR_SINGLE_PHASE: {dimension['dimension']}: {sorted(phases)}"
            )


def main() -> None:
    loaded_by_state = {}
    generated_by_state = {}

    for state in STATES:
        loaded = load_case(CASE_ROOT / state, ROOT)
        if loaded.profile.state != state:
            raise AssertionError(f"CASE_STATE_MISMATCH: {state}")
        generated = run_full_episode(loaded.runtime)
        compare_oracles(generated, loaded.oracle_paths)
        if run_full_episode(loaded.runtime) != generated:
            raise AssertionError(f"NONDETERMINISTIC_OUTPUT: {state}")

        manifest = build_manifest(
            loaded.profile, loaded.runtime, generated, loaded.oracle_paths
        )
        validate_manifest(manifest)
        if manifest["state"] != state:
            raise AssertionError(f"MANIFEST_STATE_MISMATCH: {state}")

        schema(
            generated.deterministic_rules,
            "deterministic-rule-result-v0.1.schema.json",
        )
        schema(
            generated.system_quality,
            "system-quality-result-v0.1.schema.json",
        )
        schema(
            generated.opportunity_resolution,
            "opportunity-resolution-v0.1.schema.json",
        )
        schema(
            generated.evaluation_result,
            "evaluation-result-v0.1.schema.json",
        )
        schema(manifest, "full-episode-manifest-v0.1.schema.json")

        loaded_by_state[state] = loaded
        generated_by_state[state] = generated

    dimensions = [
        item["dimension"]
        for item in generated_by_state["medium"].evaluation_result[
            "candidate_dimensions"
        ]
    ]
    high = score_map(generated_by_state["high"])
    medium = score_map(generated_by_state["medium"])
    low = score_map(generated_by_state["low"])
    for dimension in dimensions:
        if not high[dimension] > medium[dimension] > low[dimension]:
            raise AssertionError(
                "CALIBRATION_ORDER_INVALID: "
                f"{dimension}: {high[dimension]} > {medium[dimension]} > "
                f"{low[dimension]}"
            )

    reference_quality = generated_by_state["medium"].system_quality
    reference_items = generated_by_state["medium"].opportunity_resolution["items"]
    reference_ai_messages = ai_message_signature(
        loaded_by_state["medium"].runtime.episode
    )
    for state in STATES:
        loaded = loaded_by_state[state]
        generated = generated_by_state[state]
        quality = generated.system_quality
        opportunities = generated.opportunity_resolution

        if quality["status"] != "pass":
            raise AssertionError(f"AI_QUALITY_NOT_PASS: {state}")
        if quality["dimension_scores"] != reference_quality["dimension_scores"]:
            raise AssertionError(f"AI_QUALITY_DIMENSIONS_DIFFER: {state}")
        if quality["rule_results"] != reference_quality["rule_results"]:
            raise AssertionError(f"AI_QUALITY_RULES_DIFFER: {state}")
        if ai_message_signature(loaded.runtime.episode) != reference_ai_messages:
            raise AssertionError(f"AI_MESSAGES_DIFFER: {state}")
        if opportunities["items"] != reference_items:
            raise AssertionError(f"OPPORTUNITY_SUPPLY_DIFFER: {state}")
        if opportunities["summary"] != {
            "offered": 12,
            "not_offered": 0,
            "invalid": 0,
            "with_candidate_response": 12,
        }:
            raise AssertionError(f"OPPORTUNITY_COVERAGE_INVALID: {state}")

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

    low_dimensions = generated_by_state["low"].evaluation_result[
        "candidate_dimensions"
    ]
    if any(item["score"] == "NE" for item in low_dimensions):
        raise AssertionError("LOW_SCORE_INCORRECTLY_NE")
    if any(int(item["score"]) >= 3 for item in low_dimensions):
        raise AssertionError("LOW_SCORE_PROFILE_TOO_HIGH")
    if generated_by_state["low"].feedback["strengths"]:
        raise AssertionError("LOW_SCORE_FALSE_STRENGTH")

    case_ids = {
        loaded.profile.case_id for loaded in loaded_by_state.values()
    }
    target_ids = {
        loaded.profile.target_participant_id for loaded in loaded_by_state.values()
    }
    if len(case_ids) != 3 or len(target_ids) != 3:
        raise AssertionError("CASE_ID_COLLISION")

    print("Exercise A high/medium/low calibration OK")
    print("Golden replay: exact for 3 cases")
    print("AI messages, AI quality, and 12 opportunity supply: controlled")
    print("Candidate score order: high > medium > low on all 7 dimensions")
    print("High score-4 multi-phase evidence: passed")
    print("Low numeric-score and false-strength guards: passed")


if __name__ == "__main__":
    main()
