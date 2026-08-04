#!/usr/bin/env python3
"""Validate Exercise A medium vertical slice and deterministic replay."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "fixtures/calibration/full-episodes/ambiguous-structure/medium"
DIMENSIONS = [
    "issue_framing",
    "logical_reasoning",
    "listening_and_response",
    "valuable_contribution",
    "collaboration_and_relationship",
    "decision_and_consensus",
    "process_and_time_management",
]
PIPELINE_ORDER = [
    "scenario",
    "episode",
    "system_quality",
    "opportunity_resolution",
    "rater_a",
    "rater_b",
    "adjudication",
    "evaluation_result",
    "feedback",
]


class ContractError(AssertionError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_evaluator():
    spec = importlib.util.spec_from_file_location(
        "exercise_a", ROOT / "scripts/evaluate_exercise_a_medium.py"
    )
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("could not load Exercise A evaluator")
    spec.loader.exec_module(module)
    return module


def validate_schema(
    instance: Any, schema_document: dict[str, Any], label: str
) -> None:
    Draft202012Validator.check_schema(schema_document)
    validator = Draft202012Validator(
        schema_document, format_checker=FormatChecker()
    )
    errors = sorted(
        validator.iter_errors(instance), key=lambda error: list(error.absolute_path)
    )
    if errors:
        error = errors[0]
        raise ContractError(
            "SCHEMA_INVALID",
            f"{label}: {list(error.absolute_path)} {error.message}",
        )


def agreement_class(first: int | str, second: int | str) -> str:
    if first == second:
        return "exact"
    if "NE" in (first, second):
        return "ne_disagreement"
    return "adjacent" if abs(first - second) == 1 else "major_disagreement"


def expected_quality_status(rule_results: list[dict[str, Any]]) -> str:
    failed = [result for result in rule_results if result["outcome"] == "fail"]
    if any(result["severity"] == "critical" for result in failed):
        return "fail"
    return "warn" if failed else "pass"


def validate_bundle(bundle: dict[str, Any], evaluator) -> None:
    manifest = bundle["manifest"]
    scenario = bundle["scenario"]
    episode = bundle["episode"]
    system_quality = bundle["system_quality"]
    opportunities = bundle["opportunities"]
    rater_a = bundle["rater_a"]
    rater_b = bundle["rater_b"]
    adjudication = bundle["adjudication"]
    evaluation = bundle["evaluation"]
    expected_feedback = bundle["feedback"]

    if manifest["pipeline_order"] != PIPELINE_ORDER:
        raise ContractError("PIPELINE_ORDER_MISMATCH", "manifest pipeline order")

    if (
        manifest["scenario_ref"]["scenario_id"] != scenario["scenario_id"]
        or manifest["scenario_ref"]["version"] != scenario["version"]
        or episode["scenario_id"] != scenario["scenario_id"]
        or episode["scenario_version"] != scenario["version"]
        or opportunities["scenario_id"] != scenario["scenario_id"]
        or opportunities["scenario_version"] != scenario["version"]
        or system_quality["scenario_id"] != scenario["scenario_id"]
        or system_quality["scenario_version"] != scenario["version"]
    ):
        raise ContractError("VERSION_MISMATCH", "Scenario and derived artifacts")

    calculated_hash = evaluator.transcript_hash(episode["messages"])
    if (
        episode["transcript_hash"] != calculated_hash
        or evaluation["version_info"]["transcript_hash"] != calculated_hash
    ):
        raise ContractError("TRANSCRIPT_HASH_MISMATCH", "transcript hash")

    messages = {message["message_id"]: message for message in episode["messages"]}
    event_ids = {event["event_id"] for event in episode["events"]}
    target = evaluation["target_participant_id"]
    target_messages = {
        message_id
        for message_id, message in messages.items()
        if message["speaker_type"] == "user"
        and message["participant_id"] == target
    }
    if opportunities["target_participant_id"] != target:
        raise ContractError(
            "TARGET_PARTICIPANT_MISMATCH", "opportunity and evaluation targets"
        )

    scenario_opportunity_ids = {
        item["opportunity_id"] for item in scenario["evaluation_opportunities"]
    }
    resolved_opportunity_ids = {
        item["opportunity_id"] for item in opportunities["items"]
    }
    if scenario_opportunity_ids != resolved_opportunity_ids:
        raise ContractError("OPPORTUNITY_ID_MISMATCH", "opportunity set")

    def validate_target_evidence(message_ids: list[str], label: str) -> None:
        for message_id in message_ids:
            if message_id not in target_messages:
                raise ContractError(
                    "EVIDENCE_OWNER_MISMATCH", f"{label}: {message_id}"
                )

    opportunity_by_dimension = {dimension: [] for dimension in DIMENSIONS}
    summary = {
        "offered": 0,
        "not_offered": 0,
        "invalid": 0,
        "with_candidate_response": 0,
    }
    for item in opportunities["items"]:
        opportunity_by_dimension[item["dimension"]].append(item)
        if any(event_id not in event_ids for event_id in item["trigger_event_ids"]):
            raise ContractError("UNKNOWN_EVENT_ID", item["opportunity_id"])
        validate_target_evidence(
            item["candidate_response_message_ids"], item["opportunity_id"]
        )
        summary[item["status"]] += 1
        if item["response_status"] == "observed":
            summary["with_candidate_response"] += 1
        if item["status"] == "offered" and (
            not item["trigger_event_ids"] or item["invalidated_by"]
        ):
            raise ContractError(
                "OPPORTUNITY_STATUS_INCONSISTENT", item["opportunity_id"]
            )
        if item["status"] == "not_offered" and (
            item["trigger_event_ids"]
            or item["candidate_response_message_ids"]
            or item["invalidated_by"]
            or item["response_status"] != "not_applicable"
        ):
            raise ContractError(
                "OPPORTUNITY_STATUS_INCONSISTENT", item["opportunity_id"]
            )
        if item["status"] == "invalid" and (
            not item["invalidated_by"]
            or item["candidate_response_message_ids"]
            or item["response_status"] != "not_applicable"
        ):
            raise ContractError(
                "OPPORTUNITY_STATUS_INCONSISTENT", item["opportunity_id"]
            )
    if opportunities["summary"] != summary:
        raise ContractError("OPPORTUNITY_SUMMARY_MISMATCH", "derived counts")

    for sheet in (rater_a, rater_b):
        for dimension in sheet["dimensions"]:
            validate_target_evidence(
                dimension["selected_evidence_message_ids"], sheet["sheet_id"]
            )
            if any(
                event_id not in event_ids
                for event_id in dimension["opportunity_evidence_event_ids"]
            ):
                raise ContractError("UNKNOWN_EVENT_ID", dimension["dimension"])
            if (
                not any(
                    item["status"] == "offered"
                    for item in opportunity_by_dimension[dimension["dimension"]]
                )
                and dimension["score"] != "NE"
            ):
                raise ContractError(
                    "SCORE_WITHOUT_OPPORTUNITY", dimension["dimension"]
                )

    for resolution in adjudication["dimension_resolutions"]:
        validate_target_evidence(
            resolution["final_evidence_message_ids"], "adjudication"
        )

    for dimension in evaluation["candidate_dimensions"]:
        validate_target_evidence(dimension["evidence_message_ids"], "evaluation")
        for question in dimension["question_results"]:
            validate_target_evidence(question["evidence_message_ids"], "question")
            if abs(sum(question["probabilities"].values()) - 1) > 1e-6:
                raise ContractError(
                    "PROBABILITY_SUM_INVALID", dimension["dimension"]
                )

    if rater_a["annotator_id"] == rater_b["annotator_id"]:
        raise ContractError("DUPLICATE_RATER", "annotator ID")
    if adjudication["adjudicator_id"] in {
        rater_a["annotator_id"],
        rater_b["annotator_id"],
    }:
        raise ContractError("ADJUDICATOR_OVERLAP", "annotator ID")

    rater_scores = [
        {item["dimension"]: item["score"] for item in sheet["dimensions"]}
        for sheet in (rater_a, rater_b)
    ]
    adjudication_by_dimension = {}
    for resolution in adjudication["dimension_resolutions"]:
        scores = [
            rater_scores[0][resolution["dimension"]],
            rater_scores[1][resolution["dimension"]],
        ]
        if resolution["rater_scores"] != scores:
            raise ContractError(
                "RATER_SCORE_MISMATCH", resolution["dimension"]
            )
        if resolution["agreement_class"] != agreement_class(*scores):
            raise ContractError(
                "AGREEMENT_CLASS_MISMATCH", resolution["dimension"]
            )
        adjudication_by_dimension[resolution["dimension"]] = resolution

    feedback_narratives = expected_feedback["dimension_narratives"]
    for dimension in evaluation["candidate_dimensions"]:
        resolution = adjudication_by_dimension[dimension["dimension"]]
        if (
            dimension["score"] != resolution["final_score"]
            or dimension["evidence_message_ids"]
            != resolution["final_evidence_message_ids"]
        ):
            raise ContractError(
                "FINAL_RESULT_MISMATCH", dimension["dimension"]
            )
        if dimension["score"] == 4 and len(
            {
                messages[message_id]["phase"]
                for message_id in dimension["evidence_message_ids"]
            }
        ) < 2:
            raise ContractError(
                "SCORE4_PHASE_DIVERSITY", dimension["dimension"]
            )
        narrative = feedback_narratives[dimension["dimension"]]
        if (
            narrative["positive"] != dimension["positive_behavior"]
            or narrative["missing"] != dimension["missing_behavior"]
            or narrative["improvement"] != dimension["improvement"]
        ):
            raise ContractError(
                "FEEDBACK_RESULT_MISMATCH", dimension["dimension"]
            )

    if any(
        group["aggregation_status"] == "not_calibrated"
        and group["score"] is not None
        for group in evaluation["display_groups"].values()
    ):
        raise ContractError("UNCALIBRATED_GROUP_SCORE", "display group score")
    if evaluation["display_groups"] != expected_feedback["display_groups"]:
        raise ContractError("FEEDBACK_RESULT_MISMATCH", "display groups")

    derived_quality_status = expected_quality_status(system_quality["rule_results"])
    if system_quality["status"] != derived_quality_status:
        raise ContractError(
            "SYSTEM_QUALITY_STATUS_MISMATCH", "rule results and status"
        )
    if (
        system_quality["status"] != evaluation["ai_quality"]["status"]
        or system_quality["dimension_scores"]
        != evaluation["ai_quality"]["dimension_scores"]
    ):
        raise ContractError("SYSTEM_QUALITY_MISMATCH", "evaluation result")

    generated_quality = evaluator.system_quality(scenario, episode)
    generated_opportunities = evaluator.opportunities(scenario, episode)
    generated_evaluation = evaluator.evaluation(
        episode, generated_quality, adjudication
    )
    generated_feedback = evaluator.feedback(generated_evaluation)
    if (
        generated_quality != system_quality
        or generated_opportunities != opportunities
        or generated_evaluation != evaluation
        or generated_feedback != expected_feedback
        or evaluator.system_quality(scenario, episode) != generated_quality
    ):
        raise ContractError("NONDETERMINISTIC_OUTPUT", "golden replay")


def expect_failure(code: str, function: Callable[[], None]) -> None:
    try:
        function()
    except ContractError as error:
        if error.code != code:
            raise AssertionError(f"expected {code}, got {error.code}") from error
        return
    raise AssertionError(f"{code} unexpectedly passed")


def main() -> None:
    evaluator = load_evaluator()
    bundle = {
        "manifest": load(BASE / "manifest.json"),
        "scenario": load(
            ROOT
            / "fixtures/scenarios/candidate-assessment-a-ambiguous-structure-v0.1.json"
        ),
        "episode": load(BASE / "episode.json"),
        "system_quality": load(BASE / "system-quality-result.json"),
        "opportunities": load(BASE / "opportunity-resolution.json"),
        "rater_a": load(BASE / "rater-sheet-a.json"),
        "rater_b": load(BASE / "rater-sheet-b.json"),
        "adjudication": load(BASE / "adjudication.json"),
        "evaluation": load(BASE / "evaluation-result.json"),
        "feedback": load(BASE / "expected-feedback.json"),
    }
    schema_documents = {
        "manifest": "vertical-slice-manifest-v0.1.schema.json",
        "episode": "episode-v0.1.schema.json",
        "system_quality": "system-quality-result-v0.1.schema.json",
        "opportunities": "opportunity-resolution-v0.1.schema.json",
        "rater_a": "rater-sheet-v0.1.schema.json",
        "rater_b": "rater-sheet-v0.1.schema.json",
        "adjudication": "adjudication-v0.1.schema.json",
        "evaluation": "evaluation-result-v0.1.schema.json",
    }
    for key, schema_name in schema_documents.items():
        validate_schema(bundle[key], load(ROOT / "schemas" / schema_name), key)

    for artifact_name, artifact in bundle["manifest"]["artifacts"].items():
        path = ROOT / artifact["path"]
        if not path.is_file():
            raise ContractError("MANIFEST_PATH_MISSING", artifact_name)
        if file_sha256(path) != artifact["sha256"]:
            raise ContractError("MANIFEST_HASH_MISMATCH", artifact_name)

    validate_bundle(bundle, evaluator)

    tests: list[tuple[str, Callable[[], None]]] = []

    invalid = copy.deepcopy(bundle)
    invalid["episode"]["scenario_version"] = "wrong"
    tests.append(
        ("VERSION_MISMATCH", lambda invalid=invalid: validate_bundle(invalid, evaluator))
    )

    invalid = copy.deepcopy(bundle)
    invalid["episode"]["transcript_hash"] = "0" * 64
    tests.append(
        (
            "TRANSCRIPT_HASH_MISMATCH",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["opportunities"]["items"][0]["opportunity_id"] = "UNKNOWN"
    tests.append(
        (
            "OPPORTUNITY_ID_MISMATCH",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["opportunities"]["items"][0]["candidate_response_message_ids"] = [
        "m001"
    ]
    tests.append(
        (
            "EVIDENCE_OWNER_MISMATCH",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["rater_a"]["dimensions"][0]["selected_evidence_message_ids"] = [
        "m001"
    ]
    tests.append(
        (
            "EVIDENCE_OWNER_MISMATCH",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    for item in invalid["opportunities"]["items"]:
        if item["dimension"] == "issue_framing":
            item["status"] = "invalid"
            item["response_status"] = "not_applicable"
            item["candidate_response_message_ids"] = []
            item["invalidated_by"] = ["A-PROH-01"]
    invalid["opportunities"]["summary"] = {
        "offered": 9,
        "not_offered": 0,
        "invalid": 3,
        "with_candidate_response": 9,
    }
    tests.append(
        (
            "SCORE_WITHOUT_OPPORTUNITY",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["evaluation"]["candidate_dimensions"][0]["score"] = 4
    invalid["evaluation"]["candidate_dimensions"][0][
        "evidence_message_ids"
    ] = ["m004", "m006"]
    invalid["adjudication"]["dimension_resolutions"][0]["final_score"] = 4
    invalid["adjudication"]["dimension_resolutions"][0][
        "final_evidence_message_ids"
    ] = ["m004", "m006"]
    tests.append(
        (
            "SCORE4_PHASE_DIVERSITY",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["evaluation"]["candidate_dimensions"][0]["question_results"] = [
        {
            "question_id": "IF01",
            "probabilities": {
                "not_observed": 0.5,
                "partially_observed": 0.5,
                "observed": 0.5,
                "strongly_observed": 0,
            },
            "evidence_message_ids": ["m004"],
        }
    ]
    tests.append(
        (
            "PROBABILITY_SUM_INVALID",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["adjudication"]["dimension_resolutions"][0]["rater_scores"] = [1, 1]
    tests.append(
        (
            "RATER_SCORE_MISMATCH",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["evaluation"]["display_groups"]["thinking"]["score"] = 3.0
    tests.append(
        (
            "UNCALIBRATED_GROUP_SCORE",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["system_quality"]["status"] = "warn"
    tests.append(
        (
            "SYSTEM_QUALITY_STATUS_MISMATCH",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["feedback"]["dimension_narratives"]["issue_framing"][
        "positive"
    ] = "changed"
    tests.append(
        (
            "FEEDBACK_RESULT_MISMATCH",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    invalid = copy.deepcopy(bundle)
    invalid["system_quality"]["rule_results"][0]["detail"] = "changed"
    tests.append(
        (
            "NONDETERMINISTIC_OUTPUT",
            lambda invalid=invalid: validate_bundle(invalid, evaluator),
        )
    )

    for code, function in tests:
        expect_failure(code, function)

    preempted_episode = copy.deepcopy(bundle["episode"])
    preempted_episode["messages"].append(
        {
            "message_id": "m_preempt",
            "participant_id": "ai_a_operations",
            "speaker_type": "ai",
            "text": "対象と基準はこちらで決めます。",
            "phase": "problem_definition",
            "move": "define_scope",
            "start_ms": 38000,
            "end_ms": 39000,
            "generation_id": "g_preempt",
        }
    )
    preemption_result = evaluator.system_quality(
        bundle["scenario"], preempted_episode
    )
    r01 = next(
        result
        for result in preemption_result["rule_results"]
        if result["rule_id"] == "A-R01"
    )
    if r01["outcome"] != "fail" or preemption_result["status"] != "fail":
        raise AssertionError("preemptive AI scope definition was not detected")

    print("Exercise A medium vertical slice v0.1 OK")
    print(f"Artifacts: {len(bundle['manifest']['artifacts'])}")
    print(f"Opportunities: {len(bundle['opportunities']['items'])} offered")
    print("Raters: 2 independent + 1 adjudication")
    print(f"Negative vertical-slice tests: {len(tests)} passed")
    print("Evaluator behavior tests: 1 passed")


if __name__ == "__main__":
    main()
