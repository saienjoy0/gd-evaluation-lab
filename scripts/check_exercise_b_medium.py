#!/usr/bin/env python3
"""Validate the Exercise B medium vertical slice and fail-closed rules."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_DIR = (
    ROOT
    / "fixtures/calibration/full-episodes/stakeholder-conflict/medium"
)

from gd_eval.opportunities.resolver import (  # noqa: E402
    OpportunityResolutionError,
    resolve_opportunities,
)
from gd_eval.rules.registry import evaluate_deterministic_rules  # noqa: E402
from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.manifest import build_manifest, validate_manifest  # noqa: E402
from gd_eval.vertical_slice.runner import compare_oracles, run_full_episode  # noqa: E402


EXPECTED_SCORES = {
    "issue_framing": 3,
    "logical_reasoning": 3,
    "listening_and_response": 3,
    "valuable_contribution": 3,
    "collaboration_and_relationship": 3,
    "decision_and_consensus": 3,
    "process_and_time_management": 2,
}
EXPECTED_SUMMARY = {
    "offered": 15,
    "not_offered": 0,
    "invalid": 0,
    "with_candidate_response": 15,
}


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
            f"SCHEMA_INVALID: {filename}: "
            f"{list(first.absolute_path)} {first.message}"
        )


def rule_outcomes(result: dict) -> dict[str, str]:
    return {
        item["rule_id"]: item["outcome"]
        for item in result["rule_results"]
    }


def score_map(result: dict) -> dict[str, int | str]:
    return {
        item["dimension"]: item["score"]
        for item in result["candidate_dimensions"]
    }


def event(episode: dict, event_id: str) -> dict:
    return next(
        item for item in episode["events"] if item["event_id"] == event_id
    )


def message(episode: dict, message_id: str) -> dict:
    return next(
        item for item in episode["messages"] if item["message_id"] == message_id
    )


def evaluate_mutation(runtime, mutator) -> dict[str, str]:
    mutated = copy.deepcopy(runtime)
    mutator(mutated.episode)
    result = evaluate_deterministic_rules(
        mutated.scenario,
        mutated.episode,
        mutated.target_participant_id,
        mutated.versions["deterministic_evaluator_version"],
    )
    return rule_outcomes(result)


def expect_rule_failure(runtime, rule_id: str, mutator) -> None:
    outcomes = evaluate_mutation(runtime, mutator)
    if outcomes.get(rule_id) != "fail":
        raise AssertionError(
            f"EXPECTED_RULE_FAILURE_NOT_RAISED: {rule_id}: {outcomes}"
        )


def expect_opportunity_failure(
    runtime, system_quality: dict, mutator, expected: str
) -> None:
    mutated = copy.deepcopy(runtime)
    mutator(mutated.episode)
    try:
        resolve_opportunities(
            mutated.scenario,
            mutated.episode,
            system_quality,
            mutated.target_participant_id,
            mutated.versions["opportunity_resolver_version"],
        )
    except OpportunityResolutionError as exc:
        if expected not in str(exc):
            raise AssertionError(
                f"WRONG_OPPORTUNITY_FAILURE: expected {expected}, got {exc}"
            ) from exc
        return
    raise AssertionError(f"EXPECTED_OPPORTUNITY_FAILURE_NOT_RAISED: {expected}")


def main() -> None:
    loaded = load_case(CASE_DIR, ROOT)
    generated = run_full_episode(loaded.runtime)
    compare_oracles(generated, loaded.oracle_paths)
    if run_full_episode(loaded.runtime) != generated:
        raise AssertionError("NONDETERMINISTIC_EXERCISE_B_MEDIUM_OUTPUT")

    manifest = build_manifest(
        loaded.profile,
        loaded.runtime,
        generated,
        loaded.oracle_paths,
    )
    validate_manifest(manifest)
    validate_schema(
        generated.deterministic_rules,
        "deterministic-rule-result-v0.1.schema.json",
    )
    validate_schema(
        generated.system_quality,
        "system-quality-result-v0.1.schema.json",
    )
    validate_schema(
        generated.opportunity_resolution,
        "opportunity-resolution-v0.1.schema.json",
    )
    validate_schema(
        generated.evaluation_result,
        "evaluation-result-v0.1.schema.json",
    )
    validate_schema(manifest, "full-episode-manifest-v0.1.schema.json")

    if loaded.profile.state != "medium":
        raise AssertionError("EXERCISE_B_MEDIUM_STATE_INVALID")
    if loaded.profile.exercise_id != "candidate-assessment-b-stakeholder-conflict":
        raise AssertionError("EXERCISE_B_ID_INVALID")

    deterministic = rule_outcomes(generated.deterministic_rules)
    if deterministic != {
        "B-R01": "pass",
        "B-R02": "pass",
        "B-R03": "pass",
        "B-R04": "pass",
        "B-R05": "pass",
        "B-R06": "pass",
    }:
        raise AssertionError(f"B_RULE_PROFILE_INVALID: {deterministic}")

    if generated.system_quality["status"] != "pass":
        raise AssertionError("EXERCISE_B_SYSTEM_QUALITY_NOT_PASS")
    quality = rule_outcomes(generated.system_quality)
    if quality != {
        "B-R01": "pass",
        "B-R05": "pass",
        "B-PROH-01": "pass",
        "B-PROH-02": "pass",
    }:
        raise AssertionError(f"B_QUALITY_PROFILE_INVALID: {quality}")

    if generated.opportunity_resolution["summary"] != EXPECTED_SUMMARY:
        raise AssertionError(
            "EXERCISE_B_OPPORTUNITY_SUMMARY_INVALID: "
            f"{generated.opportunity_resolution['summary']}"
        )
    items = generated.opportunity_resolution["items"]
    if len(items) != 15:
        raise AssertionError("EXERCISE_B_OPPORTUNITY_COUNT_INVALID")
    if any(
        item["status"] != "offered"
        or item["response_status"] != "observed"
        or not item["candidate_response_message_ids"]
        for item in items
    ):
        raise AssertionError("EXERCISE_B_OPPORTUNITY_NOT_FULLY_OBSERVED")

    scores = score_map(generated.evaluation_result)
    if scores != EXPECTED_SCORES:
        raise AssertionError(f"EXERCISE_B_SCORE_PROFILE_INVALID: {scores}")
    if generated.evaluation_result["status"] != "completed":
        raise AssertionError("EXERCISE_B_EVALUATION_NOT_COMPLETED")
    if any(score == "NE" for score in scores.values()):
        raise AssertionError("EXERCISE_B_MEDIUM_WRONGLY_NE")

    decision = event(loaded.runtime.episode, "ev_decision_allocation")
    if decision["allocation_total_yen"] != 30000000:
        raise AssertionError("EXERCISE_B_BUDGET_TOTAL_INVALID")
    if decision["priority_count"] > 2:
        raise AssertionError("EXERCISE_B_PRIORITY_COUNT_INVALID")
    if decision["selected_priorities"] != ["childcare", "transport"]:
        raise AssertionError("EXERCISE_B_SELECTED_PRIORITIES_INVALID")
    if decision["unselected_priorities"] != ["tourism"]:
        raise AssertionError("EXERCISE_B_UNSELECTED_PRIORITY_INVALID")
    if not decision.get("mitigation", {}).get("tourism"):
        raise AssertionError("EXERCISE_B_MITIGATION_MISSING")

    def remove_third_position(episode: dict) -> None:
        message(episode, "m003")["move"] = "support"
        message(episode, "m012")["move"] = "support"

    expect_rule_failure(loaded.runtime, "B-R01", remove_third_position)

    def remove_post_proposal_challenges(episode: dict) -> None:
        message(episode, "m014")["move"] = "support"
        message(episode, "m020")["move"] = "support"

    expect_rule_failure(
        loaded.runtime, "B-R05", remove_post_proposal_challenges
    )

    def clear_concern_responses(episode: dict) -> None:
        for event_id in (
            "ev_concern_childcare",
            "ev_concern_transport",
            "ev_concern_tourism",
        ):
            event(episode, event_id)["candidate_response_message_ids"] = []

    expect_rule_failure(loaded.runtime, "B-R02", clear_concern_responses)

    expect_rule_failure(
        loaded.runtime,
        "B-R03",
        lambda episode: episode["events"].remove(
            event(episode, "ev_positions_integrated")
        ),
    )

    def remove_mitigation_field(episode: dict) -> None:
        event(episode, "ev_decision_allocation")["fields"].remove("mitigation")

    expect_rule_failure(loaded.runtime, "B-R04", remove_mitigation_field)

    expect_rule_failure(
        loaded.runtime,
        "B-R06",
        lambda episode: event(episode, "ev_decision_allocation").update(
            allocation_total_yen=31000000
        ),
    )
    expect_rule_failure(
        loaded.runtime,
        "B-R06",
        lambda episode: event(episode, "ev_decision_allocation").update(
            priority_count=3
        ),
    )

    expect_opportunity_failure(
        loaded.runtime,
        generated.system_quality,
        lambda episode: event(episode, "ev_concern_childcare").update(
            concern_id="wrong_concern"
        ),
        "OPPORTUNITY_TRIGGER_INVALID: B-OP-LI-01",
    )
    expect_opportunity_failure(
        loaded.runtime,
        generated.system_quality,
        lambda episode: event(episode, "ev_opp_b_li_01").update(
            timestamp_ms=87000
        ),
        "OPPORTUNITY_RESPONSE_BEFORE_TRIGGER: B-OP-LI-01:m008",
    )

    print("Exercise B medium vertical slice v0.1 OK")
    print("Golden replay: exact and deterministic")
    print("Rules: B-R01 through B-R06 pass")
    print("System Quality: B-PROH-01 and B-PROH-02 pass")
    print("Opportunities: 15 offered, 15 observed")
    print("Scores: 3/3/3/3/3/3/2, no NE")
    print("Budget: 30,000,000 yen, two priorities, tourism mitigation")
    print("Negative tests: 9 passed")


if __name__ == "__main__":
    main()
