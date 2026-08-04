#!/usr/bin/env python3
"""Cross-contract hardening checks for GD Evaluation Contract v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = [
    "schemas/annotation-v0.1.schema.json",
    "schemas/rater-sheet-v0.1.schema.json",
    "schemas/adjudication-v0.1.schema.json",
    "schemas/evaluation-result-v0.1.schema.json",
    "schemas/opportunity-case-v0.1.schema.json",
]
GROUPS = {
    "thinking": ["issue_framing", "logical_reasoning", "valuable_contribution"],
    "collaboration": ["listening_and_response", "collaboration_and_relationship"],
    "progress": ["decision_and_consensus", "process_and_time_management"],
}
PROBABILITY_KEYS = [
    "not_observed",
    "partially_observed",
    "observed",
    "strongly_observed",
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


def collect_enums(node: Any) -> list[list[Any]]:
    found: list[list[Any]] = []
    if isinstance(node, dict):
        enum = node.get("enum")
        if isinstance(enum, list):
            found.append(enum)
        for value in node.values():
            found.extend(collect_enums(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(collect_enums(value))
    return found


def validate_ne_registry() -> None:
    canonical = set(
        load_json(ROOT / "schemas/common/ne-reason-codes-v0.1.json")["codes"]
    )
    for schema_path in SCHEMA_FILES:
        schema = load_json(ROOT / schema_path)
        matching = [
            set(enum)
            for enum in collect_enums(schema)
            if canonical.intersection(enum)
        ]
        if not matching:
            raise AssertionError(f"{schema_path}: no NE reason enum found")
        for enum_set in matching:
            if enum_set != canonical:
                missing = sorted(canonical - enum_set)
                extra = sorted(enum_set - canonical)
                raise AssertionError(
                    f"{schema_path}: NE reason drift; missing={missing}, extra={extra}"
                )


def episode_indexes(
    episode: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    participants = {
        item["participant_id"]: item for item in episode["participants"]
    }
    messages = {item["message_id"]: item for item in episode["messages"]}
    return participants, messages


def validate_evidence_owner(
    message_id: str,
    target_participant_id: str,
    messages: dict[str, dict[str, Any]],
    label: str,
) -> None:
    message = messages.get(message_id)
    if message is None:
        raise AssertionError(f"{label}: unknown evidence message ID {message_id}")
    if message["speaker_type"] != "user":
        raise AssertionError(f"{label}: evidence message is not a user message")
    if message["participant_id"] != target_participant_id:
        raise AssertionError(f"{label}: evidence belongs to another participant")


def validate_display_groups(result: dict[str, Any]) -> None:
    scores = {
        entry["dimension"]: entry["score"]
        for entry in result["candidate_dimensions"]
    }
    for group_id, dimensions in GROUPS.items():
        group = result["display_groups"][group_id]
        numeric = [
            (dimension, scores[dimension])
            for dimension in dimensions
            if isinstance(scores[dimension], int)
            and not isinstance(scores[dimension], bool)
        ]
        expected_coverage = {"evaluated": len(numeric), "total": len(dimensions)}
        if group["coverage"] != expected_coverage:
            raise AssertionError(
                f"display group {group_id}: coverage does not match candidate dimensions"
            )
        if not numeric:
            if (
                group["aggregation_status"] != "not_evaluable"
                or group["score"] != "NE"
                or group["bottleneck_dimension"] is not None
            ):
                raise AssertionError(
                    f"display group {group_id}: zero coverage must be not_evaluable"
                )
            continue

        minimum_score = min(score for _, score in numeric)
        expected_bottleneck = next(
            dimension for dimension, score in numeric if score == minimum_score
        )
        if (
            group["aggregation_status"] != "not_calibrated"
            or group["score"] is not None
        ):
            raise AssertionError(
                f"display group {group_id}: uncalibrated groups cannot expose a numeric score"
            )
        if group["bottleneck_dimension"] != expected_bottleneck:
            raise AssertionError(
                f"display group {group_id}: bottleneck does not match the lowest child score"
            )


def validate_result_semantics(
    result: dict[str, Any], episode: dict[str, Any]
) -> None:
    if result["session_id"] != episode["session_id"]:
        raise AssertionError("evaluation result session_id does not match the episode")
    participants, messages = episode_indexes(episode)
    target = participants.get(result["target_participant_id"])
    if target is None:
        raise AssertionError("evaluation target participant does not exist")
    if target["speaker_type"] != "user":
        raise AssertionError("evaluation target participant is not a user")

    for entry in result["candidate_dimensions"]:
        dimension = entry["dimension"]
        evidence = entry["evidence_message_ids"]
        for message_id in evidence:
            validate_evidence_owner(
                message_id,
                result["target_participant_id"],
                messages,
                f"{dimension} dimension",
            )

        if entry["score"] == 4:
            phases = {messages[message_id]["phase"] for message_id in evidence}
            if len(phases) < 2:
                raise AssertionError(
                    f"{dimension}: score 4 requires evidence from two phases"
                )

        for question in entry["question_results"]:
            probabilities = question["probabilities"]
            total = sum(probabilities[key] for key in PROBABILITY_KEYS)
            if abs(total - 1.0) > 1e-6:
                raise AssertionError(
                    f"{dimension}/{question['question_id']}: probabilities must sum to 1"
                )
            for message_id in question["evidence_message_ids"]:
                validate_evidence_owner(
                    message_id,
                    result["target_participant_id"],
                    messages,
                    f"{dimension}/{question['question_id']}",
                )

    validate_display_groups(result)


def expected_agreement_class(first: Any, second: Any) -> str:
    if first == second:
        return "exact"
    if first == "NE" or second == "NE":
        return "ne_disagreement"
    if abs(first - second) == 1:
        return "adjacent"
    return "major_disagreement"


def validate_annotation_independence(
    sheet_a: dict[str, Any],
    sheet_b: dict[str, Any],
    adjudication: dict[str, Any],
) -> None:
    if sheet_a["annotator_id"] == sheet_b["annotator_id"]:
        raise AssertionError("independent rater sheets use the same annotator")
    if adjudication["adjudicator_id"] in {
        sheet_a["annotator_id"],
        sheet_b["annotator_id"],
    }:
        raise AssertionError("adjudicator must differ from both independent raters")

    scores_a = {
        item["dimension"]: item["score"] for item in sheet_a["dimensions"]
    }
    scores_b = {
        item["dimension"]: item["score"] for item in sheet_b["dimensions"]
    }
    for resolution in adjudication["dimension_resolutions"]:
        dimension = resolution["dimension"]
        expected = expected_agreement_class(
            scores_a[dimension], scores_b[dimension]
        )
        if resolution["agreement_class"] != expected:
            raise AssertionError(
                f"{dimension}: agreement_class should be {expected}"
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
    validate_ne_registry()

    episode = load_json(ROOT / "fixtures/episodes/example-episode-v0.1.json")
    result = load_json(ROOT / "fixtures/results/example-evaluation-result-v0.1.json")
    result_schema = load_json(ROOT / "schemas/evaluation-result-v0.1.schema.json")
    validate_schema(result, result_schema, "evaluation_result")
    validate_result_semantics(result, episode)

    sheet_a = load_json(
        ROOT / "fixtures/annotations/example-rater-sheet-a-v0.1.json"
    )
    sheet_b = load_json(
        ROOT / "fixtures/annotations/example-rater-sheet-b-v0.1.json"
    )
    adjudication = load_json(
        ROOT / "fixtures/annotations/example-adjudication-v0.1.json"
    )
    validate_annotation_independence(sheet_a, sheet_b, adjudication)

    negative_tests: list[tuple[str, str, Callable[[], None]]] = []

    ai_evidence = copy.deepcopy(result)
    ai_evidence["candidate_dimensions"][0]["evidence_message_ids"] = [
        "message_002"
    ]
    negative_tests.append(
        (
            "ai_evidence",
            "not a user message",
            lambda: validate_result_semantics(ai_evidence, episode),
        )
    )

    wrong_target = copy.deepcopy(result)
    wrong_target["target_participant_id"] = "ai_01"
    negative_tests.append(
        (
            "wrong_target",
            "target participant is not a user",
            lambda: validate_result_semantics(wrong_target, episode),
        )
    )

    bad_probability = copy.deepcopy(result)
    bad_probability["candidate_dimensions"][0]["question_results"][0][
        "probabilities"
    ]["observed"] = 0.9
    negative_tests.append(
        (
            "probability_sum",
            "probabilities must sum to 1",
            lambda: validate_result_semantics(bad_probability, episode),
        )
    )

    arbitrary_group_score = copy.deepcopy(result)
    arbitrary_group_score["display_groups"]["thinking"]["score"] = 3.0
    negative_tests.append(
        (
            "arbitrary_group_score",
            "uncalibrated groups cannot expose a numeric score",
            lambda: validate_result_semantics(arbitrary_group_score, episode),
        )
    )

    duplicate_rater = copy.deepcopy(sheet_b)
    duplicate_rater["annotator_id"] = sheet_a["annotator_id"]
    negative_tests.append(
        (
            "duplicate_rater",
            "same annotator",
            lambda: validate_annotation_independence(
                sheet_a, duplicate_rater, adjudication
            ),
        )
    )

    bad_agreement = copy.deepcopy(adjudication)
    bad_agreement["dimension_resolutions"][0]["agreement_class"] = "exact"
    negative_tests.append(
        (
            "agreement_class",
            "agreement_class should be adjacent",
            lambda: validate_annotation_independence(
                sheet_a, sheet_b, bad_agreement
            ),
        )
    )

    for label, expected, fn in negative_tests:
        expect_failure(label, expected, fn)

    status_text = (
        ROOT / "knowledge/current-status.md"
    ).read_text(encoding="utf-8")
    if "[in_progress] 標準演習A・B・C" in status_text:
        raise AssertionError(
            "current-status.md still marks the merged Scenario Pack as in progress"
        )

    print("Contract and scenario hardening v0.1 OK")
    print("NE reason registry: consistent across schemas")
    print("Evaluation evidence: target-user ownership verified")
    print("Question probabilities: normalized")
    print("Display groups: uncalibrated numeric scores blocked")
    print("Annotation independence and agreement classes: verified")
    print(f"Targeted negative tests: {len(negative_tests)} passed")


if __name__ == "__main__":
    main()
