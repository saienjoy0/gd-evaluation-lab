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
        lambda: run_full_episode(replace(loaded.runtime, rater_sheets=tuple(sheets))),
    )
    negatives += 1

    oracle_manifest = copy.deepcopy(manifest)
    oracle_path = next(
        entry["path"]
        for entry in oracle_manifest["artifacts"]
        if entry["role"] == "test_oracle"
    )
    next(
        entry
        for entry in oracle_manifest["artifacts"]
        if entry["path"] == "deterministic-rule-result.json"
    )["depends_on"].append(oracle_path)
    expect_failure(
        "TEST_ORACLE_GENERATION_DEPENDENCY",
        lambda: validate_manifest(oracle_manifest),
    )
    negatives += 1

    cyclic = copy.deepcopy(manifest)
    next(
        entry
        for entry in cyclic["artifacts"]
        if entry["path"] == "deterministic-rule-result.json"
    )["depends_on"].append("feedback.json")
    expect_failure("MANIFEST_CYCLE", lambda: validate_manifest(cyclic))
    negatives += 1

    episode = copy.deepcopy(loaded.runtime.episode)
    next(
        event
        for event in episode["events"]
        if event.get("opportunity_id") == "A-OP-IS-01"
    )["timestamp_ms"] = 0
    expect_failure(
        "OPPORTUNITY_TRIGGER_INVALID",
        lambda: run_full_episode(replace(loaded.runtime, episode=episode)),
    )
    negatives += 1

    episode = copy.deepcopy(loaded.runtime.episode)
    episode["events"].append(
        {
            "event_id": "ev_forced_failure",
            "event": "PROHIBITED_CONDITION_TRIGGERED",
            "timestamp_ms": 38000,
            "condition_id": "A-PROH-01",
        }
    )
    expect_failure(
        "INVALIDATED_OPPORTUNITY_NUMERIC_SCORE",
        lambda: run_full_episode(replace(loaded.runtime, episode=episode)),
    )
    negatives += 1

    sheets = copy.deepcopy(loaded.runtime.rater_sheets)
    sheets[1]["annotator_id"] = sheets[0]["annotator_id"]
    expect_failure(
        "DUPLICATE_RATER",
        lambda: run_full_episode(replace(loaded.runtime, rater_sheets=tuple(sheets))),
    )
    negatives += 1

    adjudication = copy.deepcopy(loaded.runtime.adjudication)
    adjudication["dimension_resolutions"][0]["rater_scores"] = [1, 1]
    expect_failure(
        "RATER_SCORE_MISMATCH",
        lambda: run_full_episode(replace(loaded.runtime, adjudication=adjudication)),
    )
    negatives += 1

    same_phase: dict[str, list[str]] = {}
    for message in loaded.runtime.episode["messages"]:
        if (
            message["speaker_type"] == "user"
            and message["participant_id"] == loaded.runtime.target_participant_id
        ):
            same_phase.setdefault(message["phase"], []).append(message["message_id"])
    evidence = next(ids[:2] for ids in same_phase.values() if len(ids) >= 2)
    sheets = copy.deepcopy(loaded.runtime.rater_sheets)
    for sheet in sheets:
        sheet["dimensions"][0]["score"] = 4
        sheet["dimensions"][0]["selected_evidence_message_ids"] = evidence
    adjudication = copy.deepcopy(loaded.runtime.adjudication)
    adjudication["dimension_resolutions"][0].update(
        rater_scores=[4, 4],
        agreement_class="exact",
        final_score=4,
        final_evidence_message_ids=evidence,
    )
    expect_failure(
        "SCORE4_PHASE_DIVERSITY",
        lambda: run_full_episode(
            replace(
                loaded.runtime,
                rater_sheets=tuple(sheets),
                adjudication=adjudication,
            )
        ),
    )
    negatives += 1

    backwards = copy.deepcopy(manifest)
    next(
        entry
        for entry in backwards["artifacts"]
        if entry["path"] == "evaluation-result.json"
    )["depends_on"].append("feedback.json")
    expect_failure(
        "EVALUATION_DEPENDS_ON_FEEDBACK",
        lambda: validate_manifest(backwards),
    )
    negatives += 1

    original = RULE_HANDLERS["resolved_context_keys"]
    counter = {"value": 0}

    def unstable(scenario, episode, params):
        result = original(scenario, episode, params)
        counter["value"] += 1
        result["detail"] = f"{result['detail']}#{counter['value']}"
        return result

    RULE_HANDLERS["resolved_context_keys"] = unstable
    try:
        expect_failure(
            "NONDETERMINISTIC_OUTPUT",
            lambda: assert_deterministic(loaded.runtime),
        )
    finally:
        RULE_HANDLERS["resolved_context_keys"] = original
    negatives += 1

    expect_failure(
        "STATE_BRANCH_FORBIDDEN",
        lambda: assert_no_state_branch_source(
            "def bad(profile):\n    return 4 if profile.state == 'high' else 2\n",
            "synthetic_state_branch.py",
        ),
    )
    negatives += 1

    scenario = copy.deepcopy(loaded.runtime.scenario)
    scenario["evaluation_opportunities"][0]["required_context"] = ["unknown_context"]
    expect_failure(
        "UNIMPLEMENTED_OPPORTUNITY_CONTEXT",
        lambda: run_full_episode(replace(loaded.runtime, scenario=scenario)),
    )
    negatives += 1

    print("Generic full-Episode runner v0.1 OK")
    print("Medium golden replay: exact")
    print("Two-run determinism: exact")
    print("Manifest role/DAG checks: passed")
    print(f"Negative runner tests: {negatives} passed")


if __name__ == "__main__":
    main()
