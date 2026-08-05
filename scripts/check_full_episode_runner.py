#!/usr/bin/env python3
"""Validate the generic full-Episode runner and fail-closed behavior."""
from __future__ import annotations

import ast
import copy
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_DIR = ROOT / "fixtures/calibration/full-episodes/ambiguous-structure/medium"

from gd_eval.opportunities.resolver import OpportunityResolutionError  # noqa: E402
from gd_eval.rules.registry import RULE_HANDLERS  # noqa: E402
from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.manifest import (  # noqa: E402
    build_manifest,
    validate_manifest,
)
from gd_eval.vertical_slice.runner import (  # noqa: E402
    compare_oracles,
    run_full_episode,
)


def expect_failure(code: str, action: Callable[[], object]) -> None:
    try:
        action()
    except Exception as exc:
        if code not in str(exc):
            raise AssertionError(f"expected {code}, got {type(exc).__name__}: {exc}") from exc
        return
    raise AssertionError(f"{code} unexpectedly passed")


def schema(instance: dict, filename: str) -> None:
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


def assert_deterministic(runtime) -> None:
    first = run_full_episode(runtime)
    second = run_full_episode(runtime)
    if first != second:
        raise AssertionError("NONDETERMINISTIC_OUTPUT")


def assert_no_state_branch_source(source: str, label: str) -> None:
    tree = ast.parse(source, filename=label)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "state":
            raise AssertionError(f"STATE_BRANCH_FORBIDDEN: {label}")
        if isinstance(node, ast.Subscript):
            value = node.slice
            if isinstance(value, ast.Constant) and value.value == "state":
                raise AssertionError(f"STATE_BRANCH_FORBIDDEN: {label}")


def main() -> None:
    loaded = load_case(CASE_DIR, ROOT)
    generated = run_full_episode(loaded.runtime)
    compare_oracles(generated, loaded.oracle_paths)
    assert_deterministic(loaded.runtime)
    manifest = build_manifest(
        loaded.profile, loaded.runtime, generated, loaded.oracle_paths
    )
    validate_manifest(manifest)

    schema(generated.deterministic_rules, "deterministic-rule-result-v0.1.schema.json")
    schema(generated.system_quality, "system-quality-result-v0.1.schema.json")
    schema(generated.opportunity_resolution, "opportunity-resolution-v0.1.schema.json")
    schema(generated.evaluation_result, "evaluation-result-v0.1.schema.json")
    schema(manifest, "full-episode-manifest-v0.1.schema.json")

    candidate_rule_ids = {
        item["rule_id"]
        for item in generated.deterministic_rules["rule_results"]
        if item["target"] == "candidate"
    }
    system_rule_ids = {
        item["rule_id"] for item in generated.system_quality["rule_results"]
    }
    if candidate_rule_ids & system_rule_ids:
        raise AssertionError("SYSTEM_QUALITY_SCOPE_MISMATCH")

    high_profile = replace(loaded.profile, state="high")
    if run_full_episode(loaded.runtime) != generated:
        raise AssertionError("STATE_AFFECTED_GENERATION")
    high_manifest = build_manifest(
        high_profile, loaded.runtime, generated, loaded.oracle_paths
    )
    if high_manifest["state"] != "high":
        raise AssertionError("MANIFEST_STATE_METADATA_MISSING")

    generation_paths = [
        path
        for path in (ROOT / "gd_eval").rglob("*.py")
        if path.name not in {"models.py", "loader.py", "manifest.py"}
        and "calibration" not in path.parts
    ]
    for path in generation_paths:
        assert_no_state_branch_source(path.read_text(encoding="utf-8"), str(path))

    negatives = 0

    scenario = copy.deepcopy(loaded.runtime.scenario)
    scenario["instance_rubrics"][0]["rule"]["deterministic_rule_id"] = "unknown_rule"
    expect_failure(
        "UNIMPLEMENTED_RULE_ID",
        lambda: run_full_episode(replace(loaded.runtime, scenario=scenario)),
    )
    negatives += 1

    episode = copy.deepcopy(loaded.runtime.episode)
    episode["scenario_version"] = "wrong"
    expect_failure(
        "VERSION_MISMATCH",
        lambda: run_full_episode(replace(loaded.runtime, episode=episode)),
    )
    negatives += 1

    expect_failure(
        "TARGET_PARTICIPANT_MISSING",
        lambda: run_full_episode(
            replace(loaded.runtime, target_participant_id="missing_target")
        ),
    )
    negatives += 1

    sheets = copy.deepcopy(loaded.runtime.rater_sheets)
    ai_message = next(
        message["message_id"]
        for message in loaded.runtime.episode["messages"]
        if message["speaker_type"] == "ai"
    )
    sheets[0]["dimensions"][0]["selected_evidence_message_ids"] = [ai_message]
    expect_failure(
        "EVIDENCE_OWNER_MISMATCH",
        lambda: run_full_episode(replace(loaded.runtime, rater_sheets=sheets)),
    )
    negatives += 1

    sheets = copy.deepcopy(loaded.runtime.rater_sheets)
    sheets[1]["annotator_id"] = sheets[0]["annotator_id"]
    expect_failure(
        "DUPLICATE_RATER",
        lambda: run_full_episode(replace(loaded.runtime, rater_sheets=sheets)),
    )
    negatives += 1

    adjudication = copy.deepcopy(loaded.runtime.adjudication)
    adjudication["adjudicator_id"] = loaded.runtime.rater_sheets[0]["annotator_id"]
    expect_failure(
        "ADJUDICATOR_OVERLAP",
        lambda: run_full_episode(replace(loaded.runtime, adjudication=adjudication)),
    )
    negatives += 1

    episode = copy.deepcopy(loaded.runtime.episode)
    episode["transcript_hash"] = "0" * 64
    expect_failure(
        "TRANSCRIPT_HASH_MISMATCH",
        lambda: run_full_episode(replace(loaded.runtime, episode=episode)),
    )
    negatives += 1

    scenario = copy.deepcopy(loaded.runtime.scenario)
    scenario["evaluation_opportunities"][0]["trigger"] = "unknown_trigger"
    expect_failure(
        "UNIMPLEMENTED_OPPORTUNITY_TRIGGER",
        lambda: run_full_episode(replace(loaded.runtime, scenario=scenario)),
    )
    negatives += 1

    scenario = copy.deepcopy(loaded.runtime.scenario)
    scenario["evaluation_opportunities"][0]["required_context"] = ["unknown_context"]
    expect_failure(
        "UNIMPLEMENTED_OPPORTUNITY_CONTEXT",
        lambda: run_full_episode(replace(loaded.runtime, scenario=scenario)),
    )
    negatives += 1

    episode = copy.deepcopy(loaded.runtime.episode)
    offered = next(
        event
        for event in episode["events"]
        if event.get("event") == "OPPORTUNITY_OFFERED"
    )
    offered["dimension"] = "logical_reasoning"
    expect_failure(
        "OPPORTUNITY_DIMENSION_MISMATCH",
        lambda: run_full_episode(replace(loaded.runtime, episode=episode)),
    )
    negatives += 1

    scenario = copy.deepcopy(loaded.runtime.scenario)
    scenario["instance_rubrics"].append(
        {
            "rubric_id": "UNSUPPORTED-CANDIDATE-RULE",
            "target": "candidate",
            "description": "unsupported",
            "severity": "major",
            "affected_dimensions": ["issue_framing"],
            "rule": {
                "rule_type": "deterministic",
                "deterministic_rule_id": "unknown_rule",
                "judge_question_ids": [],
                "params": {},
            },
        }
    )
    expect_failure(
        "UNIMPLEMENTED_RULE_ID",
        lambda: run_full_episode(replace(loaded.runtime, scenario=scenario)),
    )
    negatives += 1

    episode = copy.deepcopy(loaded.runtime.episode)
    opportunity = next(
        event
        for event in episode["events"]
        if event.get("event") == "OPPORTUNITY_OFFERED"
    )
    opportunity["candidate_response_message_ids"] = [ai_message]
    expect_failure(
        "EVIDENCE_OWNER_MISMATCH",
        lambda: run_full_episode(replace(loaded.runtime, episode=episode)),
    )
    negatives += 1

    if not RULE_HANDLERS:
        raise AssertionError("RULE_REGISTRY_EMPTY")
    if negatives != 12:
        raise AssertionError(f"NEGATIVE_COUNT_MISMATCH: {negatives}")

    print("Generic full-Episode runner v0.1 OK")
    print("Golden replay: exact")
    print("Determinism: exact")
    print("State metadata separated from generation")
    print("Negative runner tests: 12 passed")


if __name__ == "__main__":
    main()
