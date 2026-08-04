#!/usr/bin/env python3
"""Validate Candidate Assessment Scenario Pack v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = [
    "issue_framing",
    "logical_reasoning",
    "listening_and_response",
    "valuable_contribution",
    "collaboration_and_relationship",
    "decision_and_consensus",
    "process_and_time_management",
]
STANDARD_PHASES = [
    "problem_definition",
    "idea_generation",
    "option_comparison",
    "decision",
    "summary",
]
SCENARIO_FILES = [
    "candidate-assessment-a-ambiguous-structure-v0.1.json",
    "candidate-assessment-b-stakeholder-conflict-v0.1.json",
    "candidate-assessment-c-time-boxed-decision-v0.1.json",
]
CASE_FILES = [
    "opportunity-positive-a-issue-framing.json",
    "opportunity-negative-b-collaboration.json",
    "opportunity-ne-c-process.json",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        details = "\n".join(
            f"- {label} {list(error.absolute_path)}: {error.message}" for error in errors
        )
        raise AssertionError(details)


def validate_scenario_semantics(scenario: dict[str, Any]) -> None:
    if scenario["phase_plan"] != STANDARD_PHASES:
        raise AssertionError(f"non-standard phase order: {scenario['scenario_id']}")

    participants = scenario["ai_participants"]
    if len(participants) < 3:
        raise AssertionError(f"fewer than three AI roles: {scenario['scenario_id']}")
    agent_ids = [participant["agent_id"] for participant in participants]
    if len(agent_ids) != len(set(agent_ids)):
        raise AssertionError(f"duplicate agent ID: {scenario['scenario_id']}")
    private_concerns = [participant.get("private_concern") for participant in participants]
    if any(not str(concern or "").strip() for concern in private_concerns):
        raise AssertionError(f"missing private concern: {scenario['scenario_id']}")
    if len(private_concerns) != len(set(private_concerns)):
        raise AssertionError(f"duplicate private concern: {scenario['scenario_id']}")
    if any(not participant.get("allowed_moves") for participant in participants):
        raise AssertionError(f"participant without allowed moves: {scenario['scenario_id']}")

    required_moves = scenario.get("required_moves", [])
    forbidden_moves = scenario.get("forbidden_moves", [])
    if len(required_moves) != len(set(required_moves)):
        raise AssertionError(f"duplicate required move: {scenario['scenario_id']}")
    if len(forbidden_moves) != len(set(forbidden_moves)):
        raise AssertionError(f"duplicate forbidden move: {scenario['scenario_id']}")
    if set(required_moves) & set(forbidden_moves):
        raise AssertionError(f"required/forbidden move conflict: {scenario['scenario_id']}")

    rubrics = scenario["instance_rubrics"]
    rubric_ids = [rubric["rubric_id"] for rubric in rubrics]
    if len(rubric_ids) != len(set(rubric_ids)):
        raise AssertionError(f"duplicate rubric ID: {scenario['scenario_id']}")
    targets = {rubric["target"] for rubric in rubrics}
    if "candidate" not in targets:
        raise AssertionError(f"missing candidate rubric: {scenario['scenario_id']}")
    if not ({"ai_system", "episode"} & targets):
        raise AssertionError(f"missing environment rubric: {scenario['scenario_id']}")
    for rubric in rubrics:
        if rubric["target"] == "candidate" and not rubric["affected_dimensions"]:
            raise AssertionError(f"candidate rubric without dimension: {rubric['rubric_id']}")

    opportunities = scenario["evaluation_opportunities"]
    if set(opportunities) != set(DIMENSIONS):
        raise AssertionError(f"opportunity keys differ from seven dimensions: {scenario['scenario_id']}")

    shared_text = json.dumps(scenario["shared_context"], ensure_ascii=False)
    if any(str(concern) in shared_text for concern in private_concerns):
        raise AssertionError(f"private concern leaked into shared context: {scenario['scenario_id']}")


def validate_pack_coverage(scenarios: list[dict[str, Any]]) -> dict[str, int]:
    scenario_ids = [scenario["scenario_id"] for scenario in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise AssertionError("duplicate scenario ID in pack")
    totals = {dimension: 0 for dimension in DIMENSIONS}
    for scenario in scenarios:
        for dimension, count in scenario["evaluation_opportunities"].items():
            totals[dimension] += count
    missing = {dimension: count for dimension, count in totals.items() if count < 2}
    if missing:
        raise AssertionError(f"insufficient opportunity coverage: {missing}")
    return totals


def trace_indexes(case: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    events: dict[str, dict[str, Any]] = {}
    messages: dict[str, dict[str, Any]] = {}
    for item in case["trace_excerpt"]:
        target = events if item["kind"] == "event" else messages
        if item["id"] in target:
            raise AssertionError(f"duplicate trace ID: {item['id']}")
        target[item["id"]] = item
    return events, messages


def validate_case_semantics(case: dict[str, Any], scenario_ids: set[str]) -> None:
    if case["scenario_id"] not in scenario_ids:
        raise AssertionError(f"unknown scenario in opportunity case: {case['scenario_id']}")
    events, messages = trace_indexes(case)
    for event_id in case["opportunity_event_ids"]:
        if event_id not in events:
            raise AssertionError(f"unknown opportunity event ID: {event_id}")
    for message_id in case["candidate_message_ids"]:
        message = messages.get(message_id)
        if message is None:
            raise AssertionError(f"unknown candidate message ID: {message_id}")
        if message["speaker_type"] != "user":
            raise AssertionError(f"candidate evidence is not a user message: {message_id}")

    outcome = case["expected_outcome"]
    if outcome == "scoreable_positive":
        if not (
            case["scenario_integrity"] == "valid"
            and case["opportunity_status"] == "offered"
            and case["candidate_behavior"] == "effective"
            and case["candidate_message_ids"]
            and case["expected_score_band"] == "3-4"
            and case["expected_ne_reason"] is None
        ):
            raise AssertionError("positive case semantics are inconsistent")
    elif outcome == "scoreable_low":
        if not (
            case["scenario_integrity"] == "valid"
            and case["opportunity_status"] == "offered"
            and case["candidate_behavior"] in {"ineffective", "counterproductive"}
            and case["candidate_message_ids"]
            and case["expected_score_band"] == "1-2"
            and case["expected_ne_reason"] is None
        ):
            raise AssertionError("negative case semantics are inconsistent")
    elif outcome == "NE":
        if case["candidate_message_ids"]:
            raise AssertionError("NE case must not contain candidate score evidence")
        if case["expected_score_band"] is not None or not case["expected_ne_reason"]:
            raise AssertionError("NE case must have no score band and an NE reason")
        if case["scenario_integrity"] == "valid" and case["opportunity_status"] == "offered":
            raise AssertionError("valid offered opportunity cannot be NE in this fixture contract")


def expect_failure(label: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception:
        return
    raise AssertionError(f"negative case unexpectedly passed: {label}")


def main() -> None:
    scenario_schema = load_json(ROOT / "schemas/scenario-v0.1.schema.json")
    case_schema = load_json(ROOT / "schemas/opportunity-case-v0.1.schema.json")
    scenarios = [load_json(ROOT / "fixtures/scenarios" / name) for name in SCENARIO_FILES]
    cases = [load_json(ROOT / "fixtures/opportunity-cases" / name) for name in CASE_FILES]

    for scenario in scenarios:
        validate_schema(scenario, scenario_schema, scenario["scenario_id"])
        validate_scenario_semantics(scenario)
    totals = validate_pack_coverage(scenarios)

    scenario_ids = {scenario["scenario_id"] for scenario in scenarios}
    for case in cases:
        validate_schema(case, case_schema, case["case_id"])
        validate_case_semantics(case, scenario_ids)

    def schema_case(base: dict[str, Any], mutate: Callable[[dict[str, Any]], None], schema: dict[str, Any], label: str) -> None:
        item = copy.deepcopy(base)
        mutate(item)
        validate_schema(item, schema, label)

    negative_cases: list[tuple[str, Callable[[], None]]] = []

    bad_missing_concern = copy.deepcopy(scenarios[0])
    bad_missing_concern["ai_participants"][0]["private_concern"] = None
    negative_cases.append(("missing_private_concern", lambda: validate_scenario_semantics(bad_missing_concern)))

    bad_duplicate_agent = copy.deepcopy(scenarios[0])
    bad_duplicate_agent["ai_participants"][1]["agent_id"] = bad_duplicate_agent["ai_participants"][0]["agent_id"]
    negative_cases.append(("duplicate_agent_id", lambda: validate_scenario_semantics(bad_duplicate_agent)))

    bad_phase_order = copy.deepcopy(scenarios[0])
    bad_phase_order["phase_plan"][1], bad_phase_order["phase_plan"][2] = bad_phase_order["phase_plan"][2], bad_phase_order["phase_plan"][1]
    negative_cases.append(("phase_order", lambda: validate_scenario_semantics(bad_phase_order)))

    bad_no_candidate_rubric = copy.deepcopy(scenarios[0])
    bad_no_candidate_rubric["instance_rubrics"] = [rubric for rubric in bad_no_candidate_rubric["instance_rubrics"] if rubric["target"] != "candidate"]
    negative_cases.append(("missing_candidate_rubric", lambda: validate_scenario_semantics(bad_no_candidate_rubric)))

    bad_move_conflict = copy.deepcopy(scenarios[0])
    bad_move_conflict["forbidden_moves"].append(bad_move_conflict["required_moves"][0])
    negative_cases.append(("required_forbidden_conflict", lambda: validate_scenario_semantics(bad_move_conflict)))

    bad_coverage = copy.deepcopy(scenarios)
    for scenario in bad_coverage:
        scenario["evaluation_opportunities"]["process_and_time_management"] = 0
    negative_cases.append(("insufficient_pack_coverage", lambda: validate_pack_coverage(bad_coverage)))

    positive = cases[0]
    negative = cases[1]
    ne_case = cases[2]
    negative_cases.extend([
        ("positive_without_candidate_evidence", lambda: schema_case(positive, lambda x: x.__setitem__("candidate_message_ids", []), case_schema, "bad_positive")),
        ("negative_marked_ne", lambda: schema_case(negative, lambda x: x.__setitem__("expected_outcome", "NE"), case_schema, "bad_negative")),
        ("ne_with_candidate_evidence", lambda: schema_case(ne_case, lambda x: x.__setitem__("candidate_message_ids", ["msg_missing"]), case_schema, "bad_ne")),
    ])

    bad_unknown_trace = copy.deepcopy(positive)
    bad_unknown_trace["candidate_message_ids"] = ["unknown_message"]
    negative_cases.append(("unknown_candidate_message", lambda: validate_case_semantics(bad_unknown_trace, scenario_ids)))

    bad_ai_message = copy.deepcopy(positive)
    bad_ai_message["trace_excerpt"][1]["speaker_type"] = "ai"
    negative_cases.append(("ai_message_as_candidate_evidence", lambda: validate_case_semantics(bad_ai_message, scenario_ids)))

    bad_valid_offered_ne = copy.deepcopy(ne_case)
    bad_valid_offered_ne["scenario_integrity"] = "valid"
    bad_valid_offered_ne["opportunity_status"] = "offered"
    negative_cases.append(("valid_offered_ne", lambda: validate_case_semantics(bad_valid_offered_ne, scenario_ids)))

    for label, fn in negative_cases:
        expect_failure(label, fn)

    print("Candidate assessment scenario pack v0.1 OK")
    print(f"Scenarios: {len(scenarios)}")
    print("Opportunity totals: " + json.dumps(totals, ensure_ascii=False, sort_keys=True))
    print(f"Positive/negative/NE cases: {len(cases)} passed")
    print(f"Negative scenario pack tests: {len(negative_cases)} passed")


if __name__ == "__main__":
    main()
