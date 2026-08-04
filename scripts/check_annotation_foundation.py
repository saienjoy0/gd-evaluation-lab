#!/usr/bin/env python3
"""Validate the human annotation and adjudication foundation for GD evaluation."""

from __future__ import annotations

import copy
import json
from datetime import datetime
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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if errors:
        details = "\n".join(f"- {label} {list(e.absolute_path)}: {e.message}" for e in errors)
        raise AssertionError(details)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def episode_indexes(episode: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    messages = {m["message_id"]: m for m in episode["messages"]}
    events = {e["event_id"] for e in episode["events"]}
    return messages, events


def validate_rater_semantics(sheet: dict[str, Any], episode: dict[str, Any]) -> None:
    if sheet["episode_id"] != episode["session_id"]:
        raise AssertionError("rater sheet episode_id does not match episode session_id")
    if sheet["scenario_id"] != episode["scenario_id"]:
        raise AssertionError("rater sheet scenario_id does not match episode scenario_id")
    if parse_time(sheet["completed_at"]) < parse_time(sheet["started_at"]):
        raise AssertionError("rater sheet completed_at precedes started_at")

    messages, events = episode_indexes(episode)
    seen = set()
    for entry in sheet["dimensions"]:
        dimension = entry["dimension"]
        if dimension in seen:
            raise AssertionError(f"duplicate rater dimension: {dimension}")
        seen.add(dimension)
        for event_id in entry["opportunity_evidence_event_ids"]:
            if event_id not in events:
                raise AssertionError(f"unknown opportunity event ID: {event_id}")
        for message_id in entry["selected_evidence_message_ids"]:
            message = messages.get(message_id)
            if message is None:
                raise AssertionError(f"unknown evidence message ID: {message_id}")
            if message["speaker_type"] != "user":
                raise AssertionError(f"non-user evidence message ID: {message_id}")
    if seen != set(DIMENSIONS):
        raise AssertionError("rater sheet does not contain the exact seven dimensions")


def validate_adjudication_semantics(
    adjudication: dict[str, Any],
    sheets: list[dict[str, Any]],
    episode: dict[str, Any],
) -> None:
    sheet_by_id = {sheet["sheet_id"]: sheet for sheet in sheets}
    if set(adjudication["rater_sheet_ids"]) != set(sheet_by_id):
        raise AssertionError("adjudication rater_sheet_ids do not match supplied rater sheets")
    if adjudication["episode_id"] != episode["session_id"]:
        raise AssertionError("adjudication episode_id does not match episode")
    if adjudication["scenario_id"] != episode["scenario_id"]:
        raise AssertionError("adjudication scenario_id does not match episode")

    messages, _ = episode_indexes(episode)
    dimensions_by_sheet = {
        sheet_id: {entry["dimension"]: entry for entry in sheet["dimensions"]}
        for sheet_id, sheet in sheet_by_id.items()
    }
    ordered_sheet_ids = adjudication["rater_sheet_ids"]
    seen = set()
    for resolution in adjudication["dimension_resolutions"]:
        dimension = resolution["dimension"]
        if dimension in seen:
            raise AssertionError(f"duplicate adjudication dimension: {dimension}")
        seen.add(dimension)
        expected_scores = [dimensions_by_sheet[sid][dimension]["score"] for sid in ordered_sheet_ids]
        if resolution["rater_scores"] != expected_scores:
            raise AssertionError(f"rater score snapshot mismatch for {dimension}")
        for message_id in resolution["final_evidence_message_ids"]:
            message = messages.get(message_id)
            if message is None:
                raise AssertionError(f"unknown final evidence message ID: {message_id}")
            if message["speaker_type"] != "user":
                raise AssertionError(f"non-user final evidence message ID: {message_id}")
    if seen != set(DIMENSIONS):
        raise AssertionError("adjudication does not contain the exact seven dimensions")


def expect_failure(label: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception:
        return
    raise AssertionError(f"negative case unexpectedly passed: {label}")


def main() -> None:
    rater_schema = load_json(ROOT / "schemas/rater-sheet-v0.1.schema.json")
    adjudication_schema = load_json(ROOT / "schemas/adjudication-v0.1.schema.json")
    episode = load_json(ROOT / "fixtures/episodes/example-episode-v0.1.json")
    sheet_a = load_json(ROOT / "fixtures/annotations/example-rater-sheet-a-v0.1.json")
    sheet_b = load_json(ROOT / "fixtures/annotations/example-rater-sheet-b-v0.1.json")
    adjudication = load_json(ROOT / "fixtures/annotations/example-adjudication-v0.1.json")

    validate_schema(sheet_a, rater_schema, "sheet_a")
    validate_schema(sheet_b, rater_schema, "sheet_b")
    validate_schema(adjudication, adjudication_schema, "adjudication")
    validate_rater_semantics(sheet_a, episode)
    validate_rater_semantics(sheet_b, episode)
    validate_adjudication_semantics(adjudication, [sheet_a, sheet_b], episode)

    negative_cases: list[tuple[str, Callable[[], None]]] = []

    def schema_case(base: dict[str, Any], mutate: Callable[[dict[str, Any]], None], schema: dict[str, Any], label: str) -> None:
        item = copy.deepcopy(base)
        mutate(item)
        validate_schema(item, schema, label)

    negative_cases.extend([
        ("rater_ai_scores_visible", lambda: schema_case(sheet_a, lambda x: x["workflow_attestations"].__setitem__("ai_scores_hidden", False), rater_schema, "bad_rater")),
        ("rater_numeric_without_evidence", lambda: schema_case(sheet_a, lambda x: x["dimensions"][0].__setitem__("selected_evidence_message_ids", []), rater_schema, "bad_rater")),
        ("rater_score4_one_evidence", lambda: schema_case(sheet_a, lambda x: x["dimensions"][0].__setitem__("score", 4), rater_schema, "bad_rater")),
        ("rater_ne_without_reason", lambda: schema_case(sheet_a, lambda x: (x["dimensions"][0].__setitem__("score", "NE"), x["dimensions"][0].__setitem__("selected_evidence_message_ids", []), x["dimensions"][0].__setitem__("not_evaluable_reason", None)), rater_schema, "bad_rater")),
        ("rater_insufficient_with_numeric_score", lambda: schema_case(sheet_a, lambda x: x["dimensions"][0].__setitem__("opportunity_status", "insufficient"), rater_schema, "bad_rater")),
        ("rater_duplicate_dimension", lambda: schema_case(sheet_a, lambda x: x["dimensions"][1].__setitem__("dimension", x["dimensions"][0]["dimension"]), rater_schema, "bad_rater")),
        ("adjudication_one_sheet", lambda: schema_case(adjudication, lambda x: x.__setitem__("rater_sheet_ids", [x["rater_sheet_ids"][0]]), adjudication_schema, "bad_adjudication")),
        ("adjudication_numeric_without_evidence", lambda: schema_case(adjudication, lambda x: x["dimension_resolutions"][0].__setitem__("final_evidence_message_ids", []), adjudication_schema, "bad_adjudication")),
        ("adjudication_ne_with_evidence", lambda: schema_case(adjudication, lambda x: (x["dimension_resolutions"][4].__setitem__("final_evidence_message_ids", ["message_001"])), adjudication_schema, "bad_adjudication")),
        ("adjudication_duplicate_dimension", lambda: schema_case(adjudication, lambda x: x["dimension_resolutions"][1].__setitem__("dimension", x["dimension_resolutions"][0]["dimension"]), adjudication_schema, "bad_adjudication")),
    ])

    bad_time = copy.deepcopy(sheet_a)
    bad_time["completed_at"] = "2026-08-04T05:59:00Z"
    negative_cases.append(("rater_reversed_time", lambda: validate_rater_semantics(bad_time, episode)))

    bad_ai_evidence = copy.deepcopy(sheet_a)
    bad_ai_evidence["dimensions"][0]["selected_evidence_message_ids"] = ["message_002"]
    negative_cases.append(("rater_ai_message_as_evidence", lambda: validate_rater_semantics(bad_ai_evidence, episode)))

    bad_unknown_event = copy.deepcopy(sheet_a)
    bad_unknown_event["dimensions"][0]["opportunity_evidence_event_ids"] = ["event_missing"]
    negative_cases.append(("rater_unknown_opportunity_event", lambda: validate_rater_semantics(bad_unknown_event, episode)))

    bad_score_snapshot = copy.deepcopy(adjudication)
    bad_score_snapshot["dimension_resolutions"][0]["rater_scores"] = [1, 1]
    negative_cases.append(("adjudication_score_snapshot_mismatch", lambda: validate_adjudication_semantics(bad_score_snapshot, [sheet_a, sheet_b], episode)))

    bad_sheet_reference = copy.deepcopy(adjudication)
    bad_sheet_reference["rater_sheet_ids"][1] = "unknown_sheet"
    negative_cases.append(("adjudication_unknown_sheet", lambda: validate_adjudication_semantics(bad_sheet_reference, [sheet_a, sheet_b], episode)))

    for label, fn in negative_cases:
        expect_failure(label, fn)

    print("Human annotation foundation v0.1 OK")
    print("JSON Schema validation: Draft 2020-12 with format checking")
    print(f"Negative annotation contract tests: {len(negative_cases)} passed")


if __name__ == "__main__":
    main()
