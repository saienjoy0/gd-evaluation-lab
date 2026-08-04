#!/usr/bin/env python3
"""Validate GD Evaluation Contract v0.1 and its canonical fixtures."""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_DIMENSIONS = {
    "issue_framing", "logical_reasoning", "listening_and_response",
    "valuable_contribution", "collaboration_and_relationship",
    "decision_and_consensus", "process_and_time_management",
}
AI_DIMENSIONS = {
    "goal_progression", "responsiveness", "user_agency", "role_believability",
    "discussion_coherence", "novelty_and_repetition", "consensus_quality", "natural_pacing",
}
REQUIRED_FILES = [
    "docs/EVALUATION_PURPOSE.md", "docs/COMPETENCY_MODEL.md",
    "docs/RUBRIC_DESIGN.md", "docs/EVALUATION_CONTRACT_V0.1.md",
    "rubrics/candidate-behavior/v0.1.json", "rubrics/ai-participant/v0.1.json",
    "schemas/scenario-v0.1.schema.json", "schemas/episode-v0.1.schema.json",
    "schemas/annotation-v0.1.schema.json", "schemas/evaluation-result-v0.1.schema.json",
    "fixtures/scenarios/market-entry-001.json", "fixtures/episodes/example-episode-v0.1.json",
    "fixtures/annotations/example-human-annotation-v0.1.json",
    "fixtures/results/example-evaluation-result-v0.1.json",
]

JsonObject = dict[str, Any]


def load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def schema_errors(instance: Any, schema: JsonObject, label: str) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    return [f"{label} {list(error.absolute_path)}: {error.message}" for error in errors]


def duplicate_values(values: list[Any]) -> set[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates


def dimension_errors(data: JsonObject, field: str, label: str) -> list[str]:
    errors: list[str] = []
    entries = data.get(field, [])
    dimensions = [item.get("dimension") for item in entries if isinstance(item, dict)]
    if len(dimensions) != 7 or set(dimensions) != CANDIDATE_DIMENSIONS:
        errors.append(f"{label}.{field}: must contain every candidate dimension exactly once")
    duplicates = duplicate_values(dimensions)
    if duplicates:
        errors.append(f"{label}.{field}: duplicate dimensions {sorted(duplicates)}")

    evidence_field = "evidence_message_ids"
    if field == "dimensions" and entries and "selected_evidence_message_ids" in entries[0]:
        evidence_field = "selected_evidence_message_ids"
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        score = entry.get("score")
        evidence = entry.get(evidence_field, [])
        reason = entry.get("not_evaluable_reason")
        location = f"{label}.{field}[{index}]"
        if len(evidence) != len(set(evidence)):
            errors.append(f"{location}: evidence IDs must be unique")
        if score == "NE":
            valid_reason = isinstance(reason, str) and bool(reason.strip())
            if field == "candidate_dimensions":
                valid_reason = (
                    isinstance(reason, dict)
                    and isinstance(reason.get("code"), str)
                    and isinstance(reason.get("detail"), str)
                    and bool(reason["detail"].strip())
                )
            if not valid_reason:
                errors.append(f"{location}: NE requires a non-empty reason")
            if evidence:
                errors.append(f"{location}: NE cannot contain score evidence")
        elif isinstance(score, int) and not isinstance(score, bool):
            if reason is not None:
                errors.append(f"{location}: numeric score requires null NE reason")
            if not evidence:
                errors.append(f"{location}: numeric score requires evidence")
            if score == 4 and len(set(evidence)) < 2:
                errors.append(f"{location}: score 4 requires two evidence messages")
    return errors


def episode_errors(episode: JsonObject, label: str) -> list[str]:
    errors: list[str] = []
    participants = episode.get("participants", [])
    participant_ids = [item.get("participant_id") for item in participants]
    participant_types = {item.get("participant_id"): item.get("speaker_type") for item in participants}
    duplicates = duplicate_values(participant_ids)
    if duplicates:
        errors.append(f"{label}: duplicate participant IDs {sorted(duplicates)}")
    if "user" not in participant_types.values():
        errors.append(f"{label}: at least one user is required")
    if "ai" not in participant_types.values():
        errors.append(f"{label}: at least one AI is required")

    messages = episode.get("messages", [])
    if not messages:
        errors.append(f"{label}: at least one message is required")
    message_ids = [item.get("message_id") for item in messages]
    duplicates = duplicate_values(message_ids)
    if duplicates:
        errors.append(f"{label}: duplicate message IDs {sorted(duplicates)}")
    for index, message in enumerate(messages):
        participant_id = message.get("participant_id")
        if participant_id not in participant_types:
            errors.append(f"{label}.messages[{index}]: unknown participant")
        elif participant_types[participant_id] != message.get("speaker_type"):
            errors.append(f"{label}.messages[{index}]: speaker type mismatch")
        if message.get("end_ms", 0) < message.get("start_ms", 0):
            errors.append(f"{label}.messages[{index}]: reversed message time")

    event_ids = [item.get("event_id") for item in episode.get("events", [])]
    duplicates = duplicate_values(event_ids)
    if duplicates:
        errors.append(f"{label}: duplicate event IDs {sorted(duplicates)}")
    try:
        started = datetime.fromisoformat(episode["started_at"].replace("Z", "+00:00"))
        ended = datetime.fromisoformat(episode["ended_at"].replace("Z", "+00:00"))
        if ended < started:
            errors.append(f"{label}: reversed session time")
    except (KeyError, ValueError):
        pass
    return errors


def evidence_reference_errors(
    data: JsonObject, field: str, messages: dict[str, JsonObject],
    target_participant_id: str | None, label: str,
) -> list[str]:
    errors: list[str] = []
    evidence_field = "evidence_message_ids"
    entries = data.get(field, [])
    if field == "dimensions" and entries and "selected_evidence_message_ids" in entries[0]:
        evidence_field = "selected_evidence_message_ids"
    for index, entry in enumerate(entries):
        for message_id in entry.get(evidence_field, []):
            message = messages.get(message_id)
            if message is None:
                errors.append(f"{label}.{field}[{index}]: unknown evidence {message_id}")
                continue
            if message.get("speaker_type") != "user":
                errors.append(f"{label}.{field}[{index}]: evidence must be a user message")
            if target_participant_id and message.get("participant_id") != target_participant_id:
                errors.append(f"{label}.{field}[{index}]: evidence belongs to another participant")
        for q_index, question in enumerate(entry.get("question_results", [])):
            for message_id in question.get("evidence_message_ids", []):
                message = messages.get(message_id)
                if message is None:
                    errors.append(f"{label}.{field}[{index}].question_results[{q_index}]: unknown evidence")
                elif message.get("speaker_type") != "user":
                    errors.append(f"{label}.{field}[{index}].question_results[{q_index}]: evidence must be a user message")
                elif target_participant_id and message.get("participant_id") != target_participant_id:
                    errors.append(f"{label}.{field}[{index}].question_results[{q_index}]: evidence belongs to another participant")
    return errors


def expect_invalid(
    label: str, instance: JsonObject, schema: JsonObject,
    semantic: Callable[[JsonObject], list[str]] | None = None,
) -> list[str]:
    detected = schema_errors(instance, schema, label)
    if semantic:
        detected.extend(semantic(instance))
    return [] if detected else [f"negative test incorrectly accepted: {label}"]


def run_negative_tests(fixtures: dict[str, JsonObject], schemas: dict[str, JsonObject]) -> list[str]:
    failures: list[str] = []
    scenario, episode = fixtures["scenario"], fixtures["episode"]
    annotation, result = fixtures["annotation"], fixtures["result"]

    broken = copy.deepcopy(scenario)
    del broken["topic"]
    failures += expect_invalid("scenario-missing-topic", broken, schemas["scenario"])

    broken = copy.deepcopy(annotation)
    broken["created_at"] = "not-a-date"
    failures += expect_invalid("annotation-invalid-date", broken, schemas["annotation"])

    for key, field, schema_key in [
        ("annotation", "dimensions", "annotation"),
        ("result", "candidate_dimensions", "result"),
    ]:
        original = fixtures[key]
        broken = copy.deepcopy(original)
        duplicate = broken[field][0]["dimension"]
        for entry in broken[field]:
            entry["dimension"] = duplicate
        failures += expect_invalid(
            f"{key}-duplicate-dimensions", broken, schemas[schema_key],
            lambda item, f=field, k=key: dimension_errors(item, f, k),
        )

        broken = copy.deepcopy(original)
        next(item for item in broken[field] if item["score"] == "NE")["not_evaluable_reason"] = None
        failures += expect_invalid(
            f"{key}-ne-without-reason", broken, schemas[schema_key],
            lambda item, f=field, k=key: dimension_errors(item, f, k),
        )

        broken = copy.deepcopy(original)
        next(item for item in broken[field] if isinstance(item["score"], int))["evidence_message_ids"] = []
        failures += expect_invalid(
            f"{key}-numeric-without-evidence", broken, schemas[schema_key],
            lambda item, f=field, k=key: dimension_errors(item, f, k),
        )

        broken = copy.deepcopy(original)
        numeric = next(item for item in broken[field] if isinstance(item["score"], int))
        numeric["score"] = 4
        numeric["evidence_message_ids"] = ["message_001"]
        failures += expect_invalid(
            f"{key}-score4-one-evidence", broken, schemas[schema_key],
            lambda item, f=field, k=key: dimension_errors(item, f, k),
        )

    episode_cases: list[tuple[str, JsonObject]] = []
    broken = copy.deepcopy(episode); broken["messages"] = []; episode_cases.append(("episode-empty-messages", broken))
    broken = copy.deepcopy(episode); broken["participants"] = [p for p in broken["participants"] if p["speaker_type"] == "ai"]; episode_cases.append(("episode-no-user", broken))
    broken = copy.deepcopy(episode); broken["participants"] = [p for p in broken["participants"] if p["speaker_type"] == "user"]; episode_cases.append(("episode-no-ai", broken))
    broken = copy.deepcopy(episode); broken["participants"][1]["participant_id"] = broken["participants"][0]["participant_id"]; episode_cases.append(("episode-duplicate-participant", broken))
    broken = copy.deepcopy(episode); broken["events"][1]["event_id"] = broken["events"][0]["event_id"]; episode_cases.append(("episode-duplicate-event", broken))
    broken = copy.deepcopy(episode); broken["messages"][0]["participant_id"] = "missing"; episode_cases.append(("episode-unknown-participant", broken))
    broken = copy.deepcopy(episode); broken["messages"][0]["end_ms"] = broken["messages"][0]["start_ms"] - 1; episode_cases.append(("episode-reversed-message-time", broken))
    broken = copy.deepcopy(episode); broken["ended_at"] = "2026-08-04T04:59:00Z"; episode_cases.append(("episode-reversed-session-time", broken))
    for label, item in episode_cases:
        failures += expect_invalid(label, item, schemas["episode"], lambda value, l=label: episode_errors(value, l))
    return failures


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not (ROOT / path).exists():
            errors.append(f"missing required file: {path}")

    candidate = load("rubrics/candidate-behavior/v0.1.json")
    dimensions = candidate.get("dimensions", [])
    if {item.get("id") for item in dimensions} != CANDIDATE_DIMENSIONS:
        errors.append("candidate dimension set mismatch")
    for item in dimensions:
        if set(item.get("anchors", {})) != {"1", "2", "3", "4"}:
            errors.append(f"{item.get('id')}: anchors must be 1-4")
        if len(item.get("questions", [])) < 4:
            errors.append(f"{item.get('id')}: four questions required")
        if item.get("evidence_policy", {}).get("minimum_for_score_4") != 2:
            errors.append(f"{item.get('id')}: score 4 requires two evidence items")

    ai = load("rubrics/ai-participant/v0.1.json")
    if {item.get("id") for item in ai.get("dimensions", [])} != AI_DIMENSIONS:
        errors.append("AI dimension set mismatch")
    if not any(rule.get("severity") == "critical" for rule in ai.get("deterministic_rules", [])):
        errors.append("critical AI quality rule required")

    schemas = {
        "scenario": load("schemas/scenario-v0.1.schema.json"),
        "episode": load("schemas/episode-v0.1.schema.json"),
        "annotation": load("schemas/annotation-v0.1.schema.json"),
        "result": load("schemas/evaluation-result-v0.1.schema.json"),
    }
    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            errors.append(f"{name} schema invalid: {exc.message}")

    fixture_specs = [
        ("scenario", "fixtures/scenarios/market-entry-001.json"),
        ("episode", "fixtures/episodes/example-episode-v0.1.json"),
        ("annotation", "fixtures/annotations/example-human-annotation-v0.1.json"),
        ("result", "fixtures/results/example-evaluation-result-v0.1.json"),
    ]
    fixtures: dict[str, JsonObject] = {}
    for name, path in fixture_specs:
        fixture = load(path)
        fixtures[name] = fixture
        errors.extend(schema_errors(fixture, schemas[name], path))

    scenario = fixtures["scenario"]
    opportunity_dimensions = {item.get("dimension") for item in scenario.get("evaluation_opportunities", [])}
    if opportunity_dimensions != CANDIDATE_DIMENSIONS:
        errors.append("scenario opportunities must cover all seven dimensions")
    opportunity_ids = [item.get("opportunity_id") for item in scenario.get("evaluation_opportunities", [])]
    if duplicate_values(opportunity_ids):
        errors.append("scenario opportunity IDs must be unique")
    if not scenario.get("instance_rubrics"):
        errors.append("scenario requires instance rubrics")

    episode = fixtures["episode"]
    errors.extend(episode_errors(episode, "example episode"))
    messages = {item["message_id"]: item for item in episode.get("messages", [])}

    annotation = fixtures["annotation"]
    errors.extend(dimension_errors(annotation, "dimensions", "example annotation"))
    errors.extend(evidence_reference_errors(annotation, "dimensions", messages, None, "example annotation"))

    result = fixtures["result"]
    errors.extend(dimension_errors(result, "candidate_dimensions", "example result"))
    errors.extend(evidence_reference_errors(result, "candidate_dimensions", messages, result.get("target_participant_id"), "example result"))
    errors.extend(run_negative_tests(fixtures, schemas))

    if errors:
        print("Evaluation contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Evaluation contract v0.1 OK")
    print("Canonical fixtures and negative contract tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
