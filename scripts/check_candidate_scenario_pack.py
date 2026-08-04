#!/usr/bin/env python3
"""Validate the hardened Candidate Assessment Scenario Pack v0.1."""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

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
        raise ValidationError(details)


def validate_scenario_semantics(
    scenario: dict[str, Any],
    move_vocabulary: set[str],
    rubric_rule_vocabulary: set[str],
    prohibited_rule_vocabulary: set[str],
    question_ids: set[str],
) -> Counter[str]:
    scenario_id = scenario["scenario_id"]
    if scenario["phase_plan"] != STANDARD_PHASES:
        raise AssertionError(f"{scenario_id}: phase order must equal the standard phase sequence")

    participants = scenario["ai_participants"]
    if len(participants) < 3:
        raise AssertionError(f"{scenario_id}: at least three AI roles are required")
    agent_ids = [item["agent_id"] for item in participants]
    if len(agent_ids) != len(set(agent_ids)):
        raise AssertionError(f"{scenario_id}: duplicate agent ID")
    concerns = [item.get("private_concern") for item in participants]
    if any(not str(item or "").strip() for item in concerns):
        raise AssertionError(f"{scenario_id}: every AI role requires a private concern")
    if len(concerns) != len(set(concerns)):
        raise AssertionError(f"{scenario_id}: private concerns must be distinct")
    for participant in participants:
        unknown = set(participant["allowed_moves"]) - move_vocabulary
        if unknown:
            raise AssertionError(f"{scenario_id}: unknown allowed moves {sorted(unknown)}")

    prohibited = scenario["prohibited_conditions"]
    prohibited_ids = [item["condition_id"] for item in prohibited]
    if len(prohibited_ids) != len(set(prohibited_ids)):
        raise AssertionError(f"{scenario_id}: duplicate prohibited condition ID")
    prohibited_id_set = set(prohibited_ids)
    for item in prohibited:
        if item["rule_id"] not in prohibited_rule_vocabulary:
            raise AssertionError(
                f"{scenario_id}: unknown prohibited rule {item['rule_id']}"
            )

    opportunities = scenario["evaluation_opportunities"]
    opportunity_ids = [item["opportunity_id"] for item in opportunities]
    if len(opportunity_ids) != len(set(opportunity_ids)):
        raise AssertionError(f"{scenario_id}: duplicate opportunity ID")
    counts: Counter[str] = Counter()
    for item in opportunities:
        counts[item["dimension"]] += 1
        if item["phase"] not in scenario["phase_plan"]:
            raise AssertionError(
                f"{scenario_id}: opportunity {item['opportunity_id']} uses an unknown phase"
            )
        unknown_invalidators = set(item["invalidated_by"]) - prohibited_id_set
        if unknown_invalidators:
            raise AssertionError(
                f"{scenario_id}: opportunity {item['opportunity_id']} references "
                f"unknown invalidators {sorted(unknown_invalidators)}"
            )

    action_ids = [item["action_id"] for item in scenario["required_actions"]]
    if len(action_ids) != len(set(action_ids)):
        raise AssertionError(f"{scenario_id}: duplicate required action ID")
    for action in scenario["required_actions"]:
        if action["move"] not in move_vocabulary:
            raise AssertionError(f"{scenario_id}: unknown required move {action['move']}")
        if action["phase"] not in scenario["phase_plan"]:
            raise AssertionError(f"{scenario_id}: required action uses an unknown phase")

    rubrics = scenario["instance_rubrics"]
    rubric_ids = [item["rubric_id"] for item in rubrics]
    if len(rubric_ids) != len(set(rubric_ids)):
        raise AssertionError(f"{scenario_id}: duplicate rubric ID")
    targets = {item["target"] for item in rubrics}
    if "candidate" not in targets or not ({"ai_system", "episode"} & targets):
        raise AssertionError(
            f"{scenario_id}: candidate and environment rubrics are both required"
        )

    for rubric in rubrics:
        rule = rubric["rule"]
        rule_type = rule["rule_type"]
        deterministic_id = rule["deterministic_rule_id"]
        judge_ids = set(rule["judge_question_ids"])
        if deterministic_id is not None and deterministic_id not in rubric_rule_vocabulary:
            raise AssertionError(
                f"{scenario_id}: rubric {rubric['rubric_id']} uses unknown deterministic "
                f"rule {deterministic_id}"
            )
        unknown_questions = judge_ids - question_ids
        if unknown_questions:
            raise AssertionError(
                f"{scenario_id}: rubric {rubric['rubric_id']} uses unknown judge "
                f"questions {sorted(unknown_questions)}"
            )
        if rule_type == "deterministic" and judge_ids:
            raise AssertionError(f"{scenario_id}: deterministic rubric cannot use judge questions")
        if rule_type == "judge" and deterministic_id is not None:
            raise AssertionError(f"{scenario_id}: judge rubric cannot use a deterministic rule")
        if rubric["target"] == "candidate" and not judge_ids:
            raise AssertionError(
                f"{scenario_id}: candidate rubric {rubric['rubric_id']} needs judge questions"
            )
        if rubric["target"] == "candidate" and not rubric["affected_dimensions"]:
            raise AssertionError(
                f"{scenario_id}: candidate rubric {rubric['rubric_id']} needs dimensions"
            )

    shared_text = json.dumps(scenario["shared_context"], ensure_ascii=False)
    if any(str(concern) in shared_text for concern in concerns):
        raise AssertionError(f"{scenario_id}: private concern leaked into shared context")
    return counts


def validate_pack_coverage(counts_by_scenario: list[Counter[str]]) -> dict[str, int]:
    totals = {dimension: 0 for dimension in DIMENSIONS}
    for counts in counts_by_scenario:
        for dimension in DIMENSIONS:
            totals[dimension] += counts[dimension]
    missing = {dimension: count for dimension, count in totals.items() if count < 2}
    if missing:
        raise AssertionError(f"insufficient opportunity coverage: {missing}")
    return totals


def trace_indexes(case: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    events: dict[str, dict[str, Any]] = {}
    messages: dict[str, dict[str, Any]] = {}
    all_ids: set[str] = set()
    for item in case["trace_excerpt"]:
        if item["id"] in all_ids:
            raise AssertionError(f"{case['case_id']}: duplicate trace ID {item['id']}")
        all_ids.add(item["id"])
        target = events if item["kind"] == "event" else messages
        target[item["id"]] = item
    return events, messages


def validate_case_semantics(
    case: dict[str, Any], scenarios_by_id: dict[str, dict[str, Any]]
) -> None:
    scenario = scenarios_by_id.get(case["scenario_id"])
    if scenario is None:
        raise AssertionError(f"{case['case_id']}: unknown scenario")
    opportunities = {item["opportunity_id"]: item for item in scenario["evaluation_opportunities"]}
    for opportunity_id in case["opportunity_ids"]:
        opportunity = opportunities.get(opportunity_id)
        if opportunity is None:
            raise AssertionError(
                f"{case['case_id']}: unknown opportunity ID {opportunity_id}"
            )
        if opportunity["dimension"] != case["dimension"]:
            raise AssertionError(
                f"{case['case_id']}: opportunity dimension does not match the case"
            )

    events, messages = trace_indexes(case)
    for event_id in case["opportunity_event_ids"]:
        if event_id not in events:
            raise AssertionError(f"{case['case_id']}: unknown opportunity event ID {event_id}")
    for message_id in case["candidate_message_ids"]:
        message = messages.get(message_id)
        if message is None:
            raise AssertionError(f"{case['case_id']}: unknown candidate message ID {message_id}")
        if message["speaker_type"] != "user":
            raise AssertionError(
                f"{case['case_id']}: candidate evidence is not a user message"
            )

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
            raise AssertionError(f"{case['case_id']}: positive case semantics are inconsistent")
    elif outcome == "scoreable_low":
        if not (
            case["scenario_integrity"] == "valid"
            and case["opportunity_status"] == "offered"
            and case["candidate_behavior"] in {"ineffective", "counterproductive"}
            and case["candidate_message_ids"]
            and case["expected_score_band"] == "1-2"
            and case["expected_ne_reason"] is None
        ):
            raise AssertionError(f"{case['case_id']}: negative case semantics are inconsistent")
    elif outcome == "NE":
        if case["candidate_message_ids"]:
            raise AssertionError(f"{case['case_id']}: NE case cannot contain score evidence")
        if case["expected_score_band"] is not None or not case["expected_ne_reason"]:
            raise AssertionError(
                f"{case['case_id']}: NE case needs a reason and no score band"
            )
        if case["scenario_integrity"] == "valid" and case["opportunity_status"] == "offered":
            raise AssertionError(
                f"{case['case_id']}: valid offered opportunity cannot be NE"
            )


def expect_failure(
    label: str,
    expected_text: str,
    fn: Callable[[], None],
) -> None:
    try:
        fn()
    except (AssertionError, ValidationError) as exc:
        if expected_text not in str(exc):
            raise AssertionError(
                f"{label}: failed for the wrong reason: {exc}"
            ) from exc
        return
    raise AssertionError(f"{label}: negative case unexpectedly passed")


def main() -> None:
    scenario_schema = load_json(ROOT / "schemas/scenario-v0.1.schema.json")
    case_schema = load_json(ROOT / "schemas/opportunity-case-v0.1.schema.json")
    move_vocabulary = set(load_json(ROOT / "contracts/move-vocabulary-v0.1.json")["moves"])
    rules = load_json(ROOT / "contracts/deterministic-rule-vocabulary-v0.1.json")
    rubric_rule_vocabulary = set(rules["rubric_rules"])
    prohibited_rule_vocabulary = set(rules["prohibited_rules"])
    candidate_rubric = load_json(ROOT / "rubrics/candidate-behavior/v0.1.json")
    question_ids = {
        question["id"]
        for dimension in candidate_rubric["dimensions"]
        for question in dimension["questions"]
    }

    scenarios = [
        load_json(ROOT / "fixtures/scenarios" / file_name)
        for file_name in SCENARIO_FILES
    ]
    counts_by_scenario = []
    for scenario in scenarios:
        validate_schema(scenario, scenario_schema, scenario["scenario_id"])
        counts_by_scenario.append(
            validate_scenario_semantics(
                scenario,
                move_vocabulary,
                rubric_rule_vocabulary,
                prohibited_rule_vocabulary,
                question_ids,
            )
        )
    totals = validate_pack_coverage(counts_by_scenario)
    scenarios_by_id = {scenario["scenario_id"]: scenario for scenario in scenarios}

    cases = [
        load_json(ROOT / "fixtures/opportunity-cases" / file_name)
        for file_name in CASE_FILES
    ]
    for case in cases:
        validate_schema(case, case_schema, case["case_id"])
        validate_case_semantics(case, scenarios_by_id)

    negative_tests: list[tuple[str, str, Callable[[], None]]] = []

    bad_duplicate_opportunity = copy.deepcopy(scenarios[0])
    bad_duplicate_opportunity["evaluation_opportunities"][1]["opportunity_id"] = (
        bad_duplicate_opportunity["evaluation_opportunities"][0]["opportunity_id"]
    )
    negative_tests.append(("duplicate_opportunity_id", "duplicate opportunity ID", lambda: validate_scenario_semantics(bad_duplicate_opportunity, move_vocabulary, rubric_rule_vocabulary, prohibited_rule_vocabulary, question_ids)))

    bad_unknown_invalidator = copy.deepcopy(scenarios[0])
    bad_unknown_invalidator["evaluation_opportunities"][0]["invalidated_by"] = ["missing"]
    negative_tests.append(("unknown_invalidator", "unknown invalidators", lambda: validate_scenario_semantics(bad_unknown_invalidator, move_vocabulary, rubric_rule_vocabulary, prohibited_rule_vocabulary, question_ids)))

    bad_unknown_move = copy.deepcopy(scenarios[0])
    bad_unknown_move["required_actions"][0]["move"] = "invented_move"
    negative_tests.append(("unknown_required_move", "unknown required move", lambda: validate_scenario_semantics(bad_unknown_move, move_vocabulary, rubric_rule_vocabulary, prohibited_rule_vocabulary, question_ids)))

    bad_natural_language_rule = copy.deepcopy(scenarios[0])
    bad_natural_language_rule["instance_rubrics"][0]["rule"]["deterministic_rule_id"] = "最初にユーザーが発言していれば合格"
    negative_tests.append(("unregistered_rule", "unknown deterministic rule", lambda: validate_scenario_semantics(bad_natural_language_rule, move_vocabulary, rubric_rule_vocabulary, prohibited_rule_vocabulary, question_ids)))

    bad_unknown_question = copy.deepcopy(scenarios[0])
    bad_unknown_question["instance_rubrics"][2]["rule"]["judge_question_ids"] = ["UNKNOWN"]
    negative_tests.append(("unknown_question", "unknown judge questions", lambda: validate_scenario_semantics(bad_unknown_question, move_vocabulary, rubric_rule_vocabulary, prohibited_rule_vocabulary, question_ids)))

    bad_coverage = copy.deepcopy(counts_by_scenario)
    for counts in bad_coverage:
        counts["process_and_time_management"] = 0
    negative_tests.append(("insufficient_pack_coverage", "insufficient opportunity coverage", lambda: validate_pack_coverage(bad_coverage)))

    bad_case_opportunity = copy.deepcopy(cases[0])
    bad_case_opportunity["opportunity_ids"] = ["missing"]
    negative_tests.append(("unknown_case_opportunity", "unknown opportunity ID", lambda: validate_case_semantics(bad_case_opportunity, scenarios_by_id)))

    bad_case_dimension = copy.deepcopy(cases[0])
    bad_case_dimension["dimension"] = "logical_reasoning"
    negative_tests.append(("case_dimension_mismatch", "opportunity dimension does not match", lambda: validate_case_semantics(bad_case_dimension, scenarios_by_id)))

    bad_ai_evidence = copy.deepcopy(cases[0])
    bad_ai_evidence["trace_excerpt"][1]["speaker_type"] = "ai"
    negative_tests.append(("ai_message_as_candidate_evidence", "not a user message", lambda: validate_case_semantics(bad_ai_evidence, scenarios_by_id)))

    bad_ne_evidence = copy.deepcopy(cases[2])
    bad_ne_evidence["trace_excerpt"].append({"id":"msg_ne_user","kind":"message","speaker_type":"user","text":"形式的な発言。"})
    bad_ne_evidence["candidate_message_ids"] = ["msg_ne_user"]
    negative_tests.append(("ne_with_candidate_evidence", "NE case cannot contain", lambda: validate_case_semantics(bad_ne_evidence, scenarios_by_id)))

    for label, expected, fn in negative_tests:
        expect_failure(label, expected, fn)

    print("Candidate assessment scenario pack v0.1 hardened OK")
    print(f"Scenarios: {len(scenarios)}")
    print("Opportunity totals: " + json.dumps(totals, ensure_ascii=False, sort_keys=True))
    print(f"Positive/negative/NE cases: {len(cases)} passed")
    print(f"Targeted negative tests: {len(negative_tests)} passed")


if __name__ == "__main__":
    main()
