#!/usr/bin/env python3
"""Validate Exercise C medium vertical slice and fail-closed behavior."""
from __future__ import annotations

import copy
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_DIR = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision/medium"

from gd_eval.opportunities.resolver import (  # noqa: E402
    OpportunityResolutionError,
    resolve_opportunities,
)
from gd_eval.opportunities.stakeholder_conflict import (  # noqa: E402
    CONTEXT_HANDLERS as STAKEHOLDER_CONTEXT_HANDLERS,
    TRIGGER_HANDLERS as STAKEHOLDER_TRIGGER_HANDLERS,
)
from gd_eval.opportunities.time_boxed_decision import (  # noqa: E402
    CONTEXT_HANDLERS as TIME_CONTEXT_HANDLERS,
    TRIGGER_HANDLERS as TIME_TRIGGER_HANDLERS,
)
from gd_eval.quality.system_quality import build_system_quality  # noqa: E402
from gd_eval.rules.registry import evaluate_deterministic_rules  # noqa: E402
from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.manifest import build_manifest, validate_manifest  # noqa: E402
from gd_eval.vertical_slice.runner import compare_oracles, run_full_episode  # noqa: E402

EXPECTED_SCORES = {
    "issue_framing": 2,
    "logical_reasoning": 3,
    "listening_and_response": 3,
    "valuable_contribution": 2,
    "collaboration_and_relationship": 2,
    "decision_and_consensus": 3,
    "process_and_time_management": 3,
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


def evaluate_mutation(runtime, mutator: Callable[[dict], None]) -> dict[str, str]:
    mutated = copy.deepcopy(runtime)
    mutator(mutated.episode)
    result = evaluate_deterministic_rules(
        mutated.scenario,
        mutated.episode,
        mutated.target_participant_id,
        mutated.versions["deterministic_evaluator_version"],
    )
    return rule_outcomes(result)


def expect_rule_failure(
    runtime,
    rule_id: str,
    mutator: Callable[[dict], None],
) -> None:
    outcomes = evaluate_mutation(runtime, mutator)
    if outcomes.get(rule_id) != "fail":
        raise AssertionError(
            f"EXPECTED_RULE_FAILURE_NOT_RAISED: {rule_id}: {outcomes}"
        )


def expect_opportunity_failure(
    runtime,
    system_quality: dict,
    mutator: Callable[[dict], None],
    expected: str,
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



def expect_scenario_opportunity_failure(runtime, system_quality: dict, mutator: Callable[[dict], None], expected: str) -> None:
    scenario = json.loads(json.dumps(runtime.scenario))
    mutator(scenario)
    mutated = replace(runtime, scenario=scenario)
    try:
        resolve_opportunities(mutated.scenario, mutated.episode, system_quality, mutated.target_participant_id, mutated.versions["opportunity_resolver_version"])
    except OpportunityResolutionError as exc:
        if expected not in str(exc):
            raise AssertionError(f"WRONG_OPPORTUNITY_FAILURE: expected {expected}, got {exc}") from exc
        return
    raise AssertionError(f"EXPECTED_OPPORTUNITY_FAILURE_NOT_RAISED: {expected}")

def quality_for(runtime) -> dict:
    deterministic = evaluate_deterministic_rules(
        runtime.scenario,
        runtime.episode,
        runtime.target_participant_id,
        runtime.versions["deterministic_evaluator_version"],
    )
    return build_system_quality(
        runtime.scenario,
        runtime.episode,
        deterministic,
        runtime.target_participant_id,
        runtime.versions["deterministic_evaluator_version"],
    )


def remove_priority_events(episode: dict) -> None:
    for event_id in ("ev_priority_40", "ev_priority_75"):
        episode["events"].remove(event(episode, event_id))


def remove_priority_moves(episode: dict) -> None:
    for message_id in ("m018", "m032"):
        message(episode, message_id)["move"] = "propose_idea"


def main() -> None:
    loaded = load_case(CASE_DIR, ROOT)
    generated = run_full_episode(loaded.runtime)
    compare_oracles(generated, loaded.oracle_paths)
    if run_full_episode(loaded.runtime) != generated:
        raise AssertionError("NONDETERMINISTIC_EXERCISE_C_MEDIUM_OUTPUT")

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
        raise AssertionError("EXERCISE_C_MEDIUM_STATE_INVALID")
    if (
        loaded.profile.exercise_id
        != "candidate-assessment-c-time-boxed-decision"
    ):
        raise AssertionError("EXERCISE_C_ID_INVALID")

    generic_triggers = {"after_initial_positions", "after_goal_question", "before_idea_generation", "after_two_options_present", "after_constraint_reveal", "after_ai_question", "after_private_concern_reveal", "after_initial_ideas", "after_tradeoff_identified", "after_position_conflict", "before_final_selection", "before_session_close"}
    generic_contexts = {"priority_target_undefined", "success_metric_undefined", "scope_boundaries_undefined", "two_options_available", "constraint_requires_tradeoff", "ai_question_open", "concern_requires_response", "idea_space_open", "improvement_possible", "multiple_positions_active", "criteria_and_options_available", "remaining_time_visible"}
    if set(TIME_TRIGGER_HANDLERS) & (set(STAKEHOLDER_TRIGGER_HANDLERS) | generic_triggers):
        raise AssertionError("EXERCISE_C_TRIGGER_NAMESPACE_COLLISION")
    if set(TIME_CONTEXT_HANDLERS) & (set(STAKEHOLDER_CONTEXT_HANDLERS) | generic_contexts):
        raise AssertionError("EXERCISE_C_CONTEXT_NAMESPACE_COLLISION")
    scenario_opportunities = {item["opportunity_id"]: item for item in loaded.runtime.scenario["evaluation_opportunities"]}
    if scenario_opportunities["C-OP-VA-01"]["trigger"] != "after_training_initial_positions":
        raise AssertionError("EXERCISE_C_INITIAL_POSITION_TRIGGER_NOT_NAMESPACED")
    scenario_rubrics = {item["rubric_id"]: item for item in loaded.runtime.scenario["instance_rubrics"]}
    if scenario_rubrics["C-R02"]["rule"]["params"].get("allowed_trigger_moves") != ["ask_question"]:
        raise AssertionError("EXERCISE_C_RISK_TRIGGER_CONTRACT_INVALID")
    if scenario_rubrics["C-R05"]["rule"]["deterministic_rule_id"] != "candidate_summary_contains_fields":
        raise AssertionError("EXERCISE_C_SUMMARY_RULE_NOT_EVIDENCE_BOUND")

    deterministic = rule_outcomes(generated.deterministic_rules)
    if deterministic != {
        "C-R01": "pass",
        "C-R02": "pass",
        "C-R03": "pass",
        "C-R04": "pass",
        "C-R05": "pass",
    }:
        raise AssertionError(f"C_RULE_PROFILE_INVALID: {deterministic}")

    if generated.system_quality["status"] != "pass":
        raise AssertionError("EXERCISE_C_SYSTEM_QUALITY_NOT_PASS")
    quality = rule_outcomes(generated.system_quality)
    if quality != {
        "C-R01": "pass",
        "C-R02": "pass",
        "C-PROH-01": "pass",
        "C-PROH-02": "pass",
    }:
        raise AssertionError(f"C_QUALITY_PROFILE_INVALID: {quality}")

    if generated.opportunity_resolution["summary"] != EXPECTED_SUMMARY:
        raise AssertionError(
            "EXERCISE_C_OPPORTUNITY_SUMMARY_INVALID: "
            f"{generated.opportunity_resolution['summary']}"
        )
    items = generated.opportunity_resolution["items"]
    if len(items) != 15:
        raise AssertionError("EXERCISE_C_OPPORTUNITY_COUNT_INVALID")
    if any(
        item["status"] != "offered"
        or item["response_status"] != "observed"
        or not item["candidate_response_message_ids"]
        for item in items
    ):
        raise AssertionError("EXERCISE_C_OPPORTUNITY_NOT_FULLY_OBSERVED")

    scores = score_map(generated.evaluation_result)
    if scores != EXPECTED_SCORES:
        raise AssertionError(f"EXERCISE_C_SCORE_PROFILE_INVALID: {scores}")
    if generated.evaluation_result["status"] != "completed":
        raise AssertionError("EXERCISE_C_EVALUATION_NOT_COMPLETED")
    if any(score == "NE" for score in scores.values()):
        raise AssertionError("EXERCISE_C_MEDIUM_WRONGLY_NE")

    episode = loaded.runtime.episode
    if event(episode, "ev_checkpoint_40")["timestamp_ms"] != 290000:
        raise AssertionError("CHECKPOINT_40_TIMING_INVALID")
    if event(episode, "ev_checkpoint_75")["timestamp_ms"] != 544000:
        raise AssertionError("CHECKPOINT_75_TIMING_INVALID")
    if message(episode, "m018")["move"] != "prioritize":
        raise AssertionError("CHECKPOINT_40_PRIORITY_RESPONSE_INVALID")
    if message(episode, "m032")["move"] != "prioritize":
        raise AssertionError("CHECKPOINT_75_PRIORITY_RESPONSE_INVALID")
    if event(episode, "ev_late_risk_security")["timestamp_ms"] >= message(
        episode, "m033"
    )["start_ms"]:
        raise AssertionError("LATE_RISK_AFTER_DECISION")
    if message(episode, "m028")["start_ms"] < event(
        episode, "ev_late_risk_security"
    )["timestamp_ms"]:
        raise AssertionError("REVISION_BEFORE_RISK")
    for event_id, message_id in {"ev_options_presented": "m003", "ev_success_requirements": "m004", "ev_collision": "m021", "ev_revision": "m028", "ev_unresolved": "m030", "ev_summary": "m039", "ev_summary_fields": "m039"}.items():
        linked_event = event(episode, event_id)
        linked_message = message(episode, message_id)
        if linked_event.get("message_id") != message_id:
            raise AssertionError(f"EVENT_MESSAGE_BINDING_INVALID:{event_id}")
        if not linked_message["start_ms"] <= linked_event["timestamp_ms"] <= linked_message["end_ms"]:
            raise AssertionError(f"EVENT_TIMESTAMP_PROVENANCE_INVALID:{event_id}")

    summary = event(episode, "ev_summary")
    if any(not summary.get(field) for field in ("mode", "exception", "next_check")):
        raise AssertionError("SUMMARY_VALUE_MISSING")

    expect_rule_failure(
        loaded.runtime,
        "C-R01",
        lambda item: item["events"].remove(event(item, "ev_checkpoint_40")),
    )
    expect_rule_failure(
        loaded.runtime,
        "C-R01",
        lambda item: item["events"].remove(event(item, "ev_checkpoint_75")),
    )
    expect_rule_failure(
        loaded.runtime,
        "C-R01",
        lambda item: event(item, "ev_checkpoint_40").update(timestamp_ms=100000),
    )
    expect_rule_failure(
        loaded.runtime,
        "C-R02",
        lambda item: event(item, "ev_late_risk_security").update(
            timestamp_ms=590000
        ),
    )
    expect_rule_failure(
        loaded.runtime,
        "C-R02",
        lambda item: event(item, "ev_late_risk_security").update(
            concern="wrong"
        ),
    )
    expect_rule_failure(loaded.runtime, "C-R03", remove_priority_moves)
    expect_rule_failure(loaded.runtime, "C-R03", remove_priority_events)
    expect_rule_failure(
        loaded.runtime,
        "C-R04",
        lambda item: event(item, "ev_options_compared")["options"].remove(
            "オンライン"
        ),
    )
    expect_rule_failure(
        loaded.runtime,
        "C-R04",
        lambda item: item["events"].remove(event(item, "ev_revision")),
    )
    expect_rule_failure(
        loaded.runtime,
        "C-R04",
        lambda item: message(item, "m028").update(start_ms=470000),
    )
    for field in ("mode", "exception", "next_check"):
        expect_rule_failure(
            loaded.runtime,
            "C-R05",
            lambda item, target=field: event(
                item, "ev_summary_fields"
            )["fields"].remove(target),
        )

    mutated = copy.deepcopy(loaded.runtime)
    message(mutated.episode, "m015").update(move="propose_decision")
    if rule_outcomes(quality_for(mutated)).get("C-PROH-01") != "fail":
        raise AssertionError("C_PROH_01_NEGATIVE_NOT_CAUGHT")

    mutated = copy.deepcopy(loaded.runtime)
    mutated.episode["messages"].remove(message(mutated.episode, "m039"))
    if rule_outcomes(quality_for(mutated)).get("C-PROH-02") != "fail":
        raise AssertionError("C_PROH_02_NEGATIVE_NOT_CAUGHT")

    expect_opportunity_failure(
        loaded.runtime,
        generated.system_quality,
        lambda item: event(item, "ev_opp_c_op_li_01").update(
            timestamp_ms=130000
        ),
        "OPPORTUNITY_RESPONSE_BEFORE_TRIGGER",
    )
    expect_opportunity_failure(
        loaded.runtime,
        generated.system_quality,
        lambda item: event(item, "ev_opp_c_op_li_01").update(
            candidate_response_message_ids=["m007"]
        ),
        "EVIDENCE_OWNER_MISMATCH",
    )

    expect_rule_failure(loaded.runtime, "C-R01", lambda item: event(item, "ev_checkpoint_40").update(message_id="m016"))
    expect_rule_failure(loaded.runtime, "C-R01", lambda item: [candidate.update(participant_id="not_target") for candidate in item["messages"] if candidate.get("speaker_type") == "user" and 290000 <= candidate.get("start_ms", 0) <= 380000])
    expect_rule_failure(loaded.runtime, "C-R02", lambda item: event(item, "ev_late_risk_security").update(message_id="m025"))
    expect_rule_failure(loaded.runtime, "C-R02", lambda item: event(item, "ev_late_risk_security").update(trigger_move="unknown_move"))
    expect_rule_failure(loaded.runtime, "C-R03", lambda item: [event(item, event_id).update(timestamp_ms=400000) for event_id in ("ev_priority_40", "ev_priority_75")])
    expect_rule_failure(loaded.runtime, "C-R04", lambda item: event(item, "ev_options_compared").update(message_id="m019"))
    expect_rule_failure(loaded.runtime, "C-R04", lambda item: event(item, "ev_revision").update(before_message_id="m026"))
    expect_rule_failure(loaded.runtime, "C-R05", lambda item: event(item, "ev_summary_fields").update(message_id="m027"))
    expect_rule_failure(loaded.runtime, "C-R05", lambda item: event(item, "ev_summary").update(next_check=""))
    mutated = json.loads(json.dumps(loaded.runtime.episode))
    event(mutated, "ev_session_closed").update(timestamp_ms=650000)
    quality_runtime = replace(loaded.runtime, episode=mutated)
    if rule_outcomes(quality_for(quality_runtime)).get("C-PROH-02") != "fail":
        raise AssertionError("C_PROH_02_EARLY_CLOSE_NOT_CAUGHT")
    expect_scenario_opportunity_failure(loaded.runtime, generated.system_quality, lambda scenario: next(item for item in scenario["evaluation_opportunities"] if item["opportunity_id"] == "C-OP-IS-01").update(trigger="unknown_trigger"), "UNIMPLEMENTED_OPPORTUNITY_TRIGGER")
    expect_scenario_opportunity_failure(loaded.runtime, generated.system_quality, lambda scenario: next(item for item in scenario["evaluation_opportunities"] if item["opportunity_id"] == "C-OP-IS-01")["required_context"].append("unknown_context"), "UNIMPLEMENTED_OPPORTUNITY_CONTEXT")
    expect_opportunity_failure(loaded.runtime, generated.system_quality, lambda item: message(item, "m008").update(phase="option_comparison"), "OPPORTUNITY_PHASE_MISMATCH")
    expect_opportunity_failure(loaded.runtime, generated.system_quality, lambda item: event(item, "ev_opp_c_op_li_01").update(dimension="logical_reasoning"), "OPPORTUNITY_DIMENSION_MISMATCH")
    expect_opportunity_failure(loaded.runtime, generated.system_quality, lambda item: event(item, "ev_security_open").update(timestamp_ms=100000), "OPPORTUNITY_TRIGGER_INVALID")

    print("Exercise C medium vertical slice v0.1 OK")
    print("Golden replay: exact and deterministic")
    print("Rules: C-R01 through C-R05 pass")
    print("System Quality: C-PROH-01 and C-PROH-02 pass")
    print("Opportunities: 15 offered, 15 observed")
    print("Scores: 2/3/3/2/2/3/3, no NE")
    print("Negative tests: 32 passed")


if __name__ == "__main__":
    main()
