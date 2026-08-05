"""Reusable checks for high/medium/low controlled calibration cases."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from gd_eval.vertical_slice.loader import load_case
from gd_eval.vertical_slice.manifest import build_manifest, validate_manifest
from gd_eval.vertical_slice.runner import compare_oracles, run_full_episode

STATES = ("high", "medium", "low")
SCHEMAS = (
    ("deterministic_rules", "deterministic-rule-result-v0.1.schema.json"),
    ("system_quality", "system-quality-result-v0.1.schema.json"),
    ("opportunity_resolution", "opportunity-resolution-v0.1.schema.json"),
    ("evaluation_result", "evaluation-result-v0.1.schema.json"),
)


def validate_schema(root: Path, instance: dict[str, Any], filename: str) -> None:
    raw = json.loads((root / "schemas" / filename).read_text(encoding="utf-8"))
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


def score_map(generated: Any) -> dict[str, int]:
    return {
        item["dimension"]: int(item["score"])
        for item in generated.evaluation_result["candidate_dimensions"]
    }


def rule_map(generated: Any) -> dict[str, str]:
    return {
        item["rule_id"]: item["outcome"]
        for item in generated.deterministic_rules["rule_results"]
    }


def ai_message_signature(episode: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (
            message["message_id"],
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


def semantic_quality(generated: Any) -> dict[str, Any]:
    quality = generated.system_quality
    return {
        "status": quality["status"],
        "dimension_scores": quality["dimension_scores"],
        "rule_results": quality["rule_results"],
    }


def opportunity_signature(generated: Any) -> list[dict[str, Any]]:
    return generated.opportunity_resolution["items"]


def load_states(root: Path, case_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    loaded_by_state: dict[str, Any] = {}
    generated_by_state: dict[str, Any] = {}
    for state in STATES:
        loaded = load_case(case_root / state, root)
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
        for attribute, filename in SCHEMAS:
            validate_schema(root, getattr(generated, attribute), filename)
        validate_schema(root, manifest, "full-episode-manifest-v0.1.schema.json")
        loaded_by_state[state] = loaded
        generated_by_state[state] = generated
    return loaded_by_state, generated_by_state


def assert_strict_order(generated_by_state: dict[str, Any]) -> None:
    high = score_map(generated_by_state["high"])
    medium = score_map(generated_by_state["medium"])
    low = score_map(generated_by_state["low"])
    if set(high) != set(medium) or set(medium) != set(low):
        raise AssertionError("DIMENSION_SET_DIFFER")
    for dimension in medium:
        if not high[dimension] > medium[dimension] > low[dimension]:
            raise AssertionError(
                "CALIBRATION_ORDER_INVALID: "
                f"{dimension}: {high[dimension]} > {medium[dimension]} > {low[dimension]}"
            )


def assert_controlled_environment(
    loaded_by_state: dict[str, Any],
    generated_by_state: dict[str, Any],
    expected_summary: dict[str, int],
) -> None:
    reference_ai = ai_message_signature(loaded_by_state["medium"].runtime.episode)
    reference_quality = semantic_quality(generated_by_state["medium"])
    reference_opportunities = opportunity_signature(generated_by_state["medium"])
    for state in STATES:
        loaded = loaded_by_state[state]
        generated = generated_by_state[state]
        if ai_message_signature(loaded.runtime.episode) != reference_ai:
            raise AssertionError(f"AI_MESSAGES_DIFFER: {state}")
        if semantic_quality(generated) != reference_quality:
            raise AssertionError(f"AI_QUALITY_DIFFER: {state}")
        if generated.system_quality["status"] != "pass":
            raise AssertionError(f"AI_QUALITY_NOT_PASS: {state}")
        if opportunity_signature(generated) != reference_opportunities:
            raise AssertionError(f"OPPORTUNITY_SUPPLY_DIFFER: {state}")
        if generated.opportunity_resolution["summary"] != expected_summary:
            raise AssertionError(f"OPPORTUNITY_COVERAGE_INVALID: {state}")


def assert_score_four_spans_phases(loaded: Any, generated: Any) -> None:
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


def assert_low_numeric_and_no_strengths(generated: Any) -> None:
    dimensions = generated.evaluation_result["candidate_dimensions"]
    if any(item["score"] == "NE" for item in dimensions):
        raise AssertionError("LOW_SCORE_INCORRECTLY_NE")
    if any(int(item["score"]) >= 3 for item in dimensions):
        raise AssertionError("LOW_SCORE_PROFILE_TOO_HIGH")
    if generated.feedback["strengths"]:
        raise AssertionError("LOW_SCORE_FALSE_STRENGTH")


def assert_unique_case_identity(loaded_by_state: dict[str, Any]) -> None:
    case_ids = {loaded.profile.case_id for loaded in loaded_by_state.values()}
    target_ids = {
        loaded.profile.target_participant_id for loaded in loaded_by_state.values()
    }
    session_ids = {
        loaded.runtime.episode["session_id"] for loaded in loaded_by_state.values()
    }
    if len(case_ids) != 3 or len(target_ids) != 3 or len(session_ids) != 3:
        raise AssertionError("CASE_IDENTITY_COLLISION")
