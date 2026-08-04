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
    "issue_framing",
    "logical_reasoning",
    "listening_and_response",
    "valuable_contribution",
    "collaboration_and_relationship",
    "decision_and_consensus",
    "process_and_time_management",
}
AI_DIMENSIONS = {
    "goal_progression",
    "responsiveness",
    "user_agency",
    "role_believability",
    "discussion_coherence",
    "novelty_and_repetition",
    "consensus_quality",
    "natural_pacing",
}
FILES = [
    "docs/EVALUATION_PURPOSE.md",
    "docs/COMPETENCY_MODEL.md",
    "docs/RUBRIC_DESIGN.md",
    "docs/EVALUATION_CONTRACT_V0.1.md",
    "rubrics/candidate-behavior/v0.1.json",
    "rubrics/ai-participant/v0.1.json",
    "schemas/scenario-v0.1.schema.json",
    "schemas/episode-v0.1.schema.json",
    "schemas/annotation-v0.1.schema.json",
    "schemas/evaluation-result-v0.1.schema.json",
    "fixtures/scenarios/market-entry-001.json",
    "fixtures/episodes/example-episode-v0.1.json",
    "fixtures/annotations/example-human-annotation-v0.1.json",
    "fixtures/results/example-evaluation-result-v0.1.json",
]
FIXTURE_SCHEMAS = {
    "fixtures/scenarios/market-entry-001.json": "schemas/scenario-v0.1.schema.json",
    "fixtures/episodes/example-episode-v0.1.json": "schemas/episode-v0.1.schema.json",
    "fixtures/annotations/example-human-annotation-v0.1.json": "schemas/annotation-v0.1.schema.json",
    "fixtures/results/example-evaluation-result-v0.1.json": "schemas/evaluation-result-v0.1.schema.json",
}

JsonObject = dict[str, Any]
SemanticValidator = Callable[[JsonObject, str], list[str]]


def load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def json_path(parts: Any) -> str:
    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


def schema_errors(instance: Any, schema: JsonObject, label: str) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    return [f"{label}{json_path(error.absolute_path)}: {error.message}" for error in errors]


def duplicate_values(values: list[Any]) -> set[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates


def validate_dimension_results(data: JsonObject, field: str, label: str) -> list[str]:
    errors: list[str] = []
    entries = data.get(field, [])
    dimensions = [entry.get("dimension") for entry in entries if isinstance(entry, dict)]
    if len(dimensions) != 7 or set(dimensions) != CANDIDATE_DIMENSIONS:
        errors.append(f"{label}.{field}: must contain every candidate dimension exactly once")
    duplicates = duplicate_values(dimensions)
    if duplicates:
        errors.append(f"{label}.{field}: duplicate dimensions: {sorted(duplicates)}")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        location = f"{label}.{field}[{index}]"
        score = entry.get("score")
        evidence = entry.get("evidence_message_ids", [])
        reason = entry.get("not_evaluable_reason")
        if len(evidence) != len(set(evidence)):
            errors.append(f"{location}.evidence_message_ids: IDs must be unique")
        if score == "NE":
            if field == "dimensions":
                valid_reason = isinstance(reason, str) and bool(reason.strip())
            else:
                valid_reason = (
                    isinstance(reason, dict)
                    and isinstance(reason.get("code"), str)
                    and isinstance(reason.get("detail"), str)
                    and bool(reason["detail"].strip())
                )
            if not valid_reason:
                errors.append(f"{location}: NE requires a non-empty reason")
            if evidence:
                errors.append(f"{location}: NE must not contain evidence IDs")
        elif isinstance(score, int) and not isinstance(score, bool):
            if reason is not None:
                errors.append(f"{location}: numeric scores require a null NE reason")
            if not evidence:
                errors.append(f"{location}: numeric scores require evidence")
            if score == 4 and len(set(evidence)) < 2:
                errors.append(f"{location}: score 4 requires two distinct evidence messages")
    return errors


def validate_episode_integrity(episode: JsonObject, label: str) -> list[str]:
    errors: list[str] = []
    participants = episode.get("participants", [])
    participant_ids = [item.get("participant_id") for item in participants if isinstance(item, dict)]
    participant_types = {
        item.get("participant_id"): item.get("speaker_type")
        for item in participants
        if isinstance(item, dict) and item.get("participant_id")
    }
    duplicates = duplicate_values(participant_ids)
    if duplicates:
        errors.append(f"{label}.participants: duplicate participant IDs: {sorted(duplicates)}")
    speaker_types = [item.get("speaker_type") for item in participants if isinstance(item, dict)]
    if "user" not in speaker_types:
        errors.append(f"{label}.participants: at least one user is required")
    if "ai" not in speaker_types:
        errors.append(f"{label}.participants: at least one AI participant is required")

    messages = episode.get("messages", [])
    if not messages:
        errors.append(f"{label}.messages: at least one message is required")
    message_ids = [item.get("message_id") for item in messages if isinstance(item, dict)]
    duplicates = duplicate_values(message_ids)
    if duplicates:
        errors.append(f"{label}.messages: duplicate message IDs: {sorted(duplicates)}")
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        location = f"{label}.messages[{index}]"
        participant_id = message.get("participant_id")
        if participant_id not in participant_types:
            errors.append(f"{location}.participant_id: unknown participant {participant_id!r}")
        elif participant_types[participant_id] != message.get("speaker_type"):
            errors.append(f"{location}.speaker_type: does not match participant declaration")
        start_ms = message.get("start_ms")
        end_ms = message.get("end_ms")
        if isinstance(start_ms, int) and isinstance(end_ms, int) and end_ms < start_ms:
            errors.append(f"{location}: end_ms must be greater than or equal to start_ms")

    events = episode.get("events", [])
    event_ids = [item.get("event_id") for item in events if isinstance(item, dict)]
    duplicates = duplicate_values(event_ids)
    if duplicates:
        errors.append(f"{label}.events: duplicate event IDs: {sorted(duplicates)}")
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        participant_id = event.get("participant_id")
        if participant_id is not None and participant_id not in participant_types:
            errors.append(f"{label}.events[{index}].participant_id: unknown participant {participant_id!r}")

    try:
        started_at = datetime.fromisoformat(str(episode.get("started_at", "")).replace("Z", "+00:00"))
        ended_at = datetime.fromisoformat(str(episode.get("ended_at", "")).replace("Z", "+00:00"))
        if ended_at < started_at:
            errors.append(f"{label}: ended_at must not precede started_at")
    except ValueError:
        pass
    return errors


def validate_evidence_references(
    data: JsonObject, field: str, message_ids: set[str], label: str
) -> list[str]:
    errors: list[str] = []
    for index, entry in enumerate(data.get(field, [])):
        if not isinstance(entry, dict):
            continue
        referenced = set(entry.get("evidence_message_ids", []))
        unknown = referenced - message_ids
        if unknown:
            errors.append(f"{label}.{field}[{index}]: unknown evidence IDs: {sorted(unknown)}")
        for question_index, question in enumerate(entry.get("question_results", [])):
            question_unknown = set(question.get("evidence_message_ids", [])) - message_ids
            if question_unknown:
                errors.append(
                    f"{label}.{field}[{index}].question_results[{question_index}]: "
                    f"unknown evidence IDs: {sorted(question_unknown)}"
                )
    return errors


def expect_invalid(
    name: str,
    instance: JsonObject,
    schema: JsonObject,
    semantic_validator: SemanticValidator | None = None,
) -> list[str]:
    detected = schema_errors(instance, schema, name)
    if semantic_validator is not None:
        detected.extend(semantic_validator(instance, name))
    if detected:
        return []
    return [f"negative test was incorrectly accepted: {name}"]


def run_negative_tests(fixtures: dict[str, JsonObject], schemas: dict[str, JsonObject]) -> list[str]:
    failures: list[str] = []
    scenario = fixtures["scenario"]
    episode = fixtures["episode"]
    annotation = fixtures["annotation"]
    result = fixtures["result"]

    broken = copy.deepcopy(scenario)
    del broken["topic"]
    failures += expect_invalid("negative/scenario-missing-topic", broken, schemas["scenario"])

    broken = copy.deepcopy(annotation)
    broken["created_at"] = "not-a-date"
    failures += expect_invalid("negative/annotation-invalid-date", broken, schemas["annotation"])

    broken = copy.deepcopy(result)
    duplicate_dimension = broken["candidate_dimensions"][0]["dimension"]
    for entry in broken["candidate_dimensions"]:
        entry["dimension"] = duplicate_dimension
    failures += expect_invalid(
        "negative/result-duplicate-dimensions",
        broken,
        schemas["result"],
        lambda item, label: validate_dimension_results(item, "candidate_dimensions", label),
    )

    broken = copy.deepcopy(result)
    ne_entry = next(item for item in broken["candidate_dimensions"] if item["score"] == "NE")
    ne_entry["not_evaluable_reason"] = None
    failures += expect_invalid(
        "negative/result-ne-without-reason",
        broken,
        schemas["result"],
        lambda item, label: validate_dimension_results(item, "candidate_dimensions", label),
    )

    broken = copy.deepcopy(result)
    numeric_entry = next(item for item in broken["candidate_dimensions"] if isinstance(item["score"], int))
    numeric_entry["evidence_message_ids"] = []
    failures += expect_invalid(
        "negative/result-numeric-without-evidence",
        broken,
        schemas["result"],
        lambda item, label: validate_dimension_results(item, "candidate_dimensions", label),
    )

    broken = copy.deepcopy(result)
    numeric_entry = next(item for item in broken["candidate_dimensions"] if isinstance(item["score"], int))
    numeric_entry["score"] = 4
    numeric_entry["evidence_message_ids"] = ["message_001"]
    failures += expect_invalid(
        "negative/result-score-4-one-evidence",
        broken,
        schemas["result"],
        lambda item, label: validate_dimension_results(item, "candidate_dimensions", label),
    )

    broken = copy.deepcopy(annotation)
    duplicate_dimension = broken["dimensions"][0]["dimension"]
    for entry in broken["dimensions"]:
        entry["dimension"] = duplicate_dimension
    failures += expect_invalid(
        "negative/annotation-duplicate-dimensions",
        broken,
        schemas["annotation"],
        lambda item, label: validate_dimension_results(item, "dimensions", label),
    )

    broken = copy.deepcopy(annotation)
    ne_entry = next(item for item in broken["dimensions"] if item["score"] == "NE")
    ne_entry["not_evaluable_reason"] = None
    failures += expect_invalid(
        "negative/annotation-ne-without-reason",
        broken,
        schemas["annotation"],
        lambda item, label: validate_dimension_results(item, "dimensions", label),
    )

    broken = copy.deepcopy(annotation)
    numeric_entry = next(item for item in broken["dimensions"] if isinstance(item["score"], int))
    numeric_entry["evidence_message_ids"] = []
    failures += expect_invalid(
        "negative/annotation-numeric-without-evidence",
        broken,
        schemas["annotation"],
        lambda item, label: validate_dimension_results(item, "dimensions", label),
    )

    broken = copy.deepcopy(annotation)
    numeric_entry = next(item for item in broken["dimensions"] if isinstance(item["score"], int))
    numeric_entry["score"] = 4
    numeric_entry["evidence_message_ids"] = ["message_001"]
    failures += expect_invalid(
        "negative/annotation-score-4-one-evidence",
        broken,
        schemas["annotation"],
        lambda item, label: validate_dimension_results(item, "dimensions", label),
    )

    broken = copy.deepcopy(episode)
    broken["messages"] = []
    failures += expect_invalid(
        "negative/episode-empty-messages", broken, schemas["episode"], validate_episode_integrity
    )

    broken = copy.deepcopy(episode)
    broken["participants"] = [item for item in broken["participants"] if item["speaker_type"] == "ai"]
    failures += expect_invalid(
        "negative/episode-no-user", broken, schemas["episode"], validate_episode_integrity
    )

    broken = copy.deepcopy(episode)
    broken["participants"] = [item for item in broken["participants"] if item["speaker_type"] == "user"]
    failures += expect_invalid(
        "negative/episode-no-ai", broken, schemas["episode"], validate_episode_integrity
    )

    broken = copy.deepcopy(episode)
    broken["participants"][1]["participant_id"] = broken["participants"][0]["participant_id"]
    failures += expect_invalid(
        "negative/episode-duplicate-participant-id",
        broken,
        schemas["episode"],
        validate_episode_integrity,
    )

    broken = copy.deepcopy(episode)
    broken["events"][1]["event_id"] = broken["events"][0]["event_id"]
    failures += expect_invalid(
        "negative/episode-duplicate-event-id", broken, schemas["episode"], validate_episode_integrity
    )

    broken = copy.deepcopy(episode)
    broken["messages"][0]["participant_id"] = "missing_participant"
    failures += expect_invalid(
        "negative/episode-unknown-message-participant",
        broken,
        schemas["episode"],
        validate_episode_integrity,
    )

    broken = copy.deepcopy(episode)
    broken["messages"][0]["end_ms"] = broken["messages"][0]["start_ms"] - 1
    failures += expect_invalid(
        "negative/episode-reversed-message-time",
        broken,
        schemas["episode"],
        validate_episode_integrity,
    )

    broken = copy.deepcopy(episode)
    broken["ended_at"] = "2026-08-04T04:59:00Z"
    failures += expect_invalid(
        "negative/episode-reversed-session-time",
        broken,
        schemas["episode"],
        validate_episode_integrity,
    )
    return failures


def main() -> int:
    errors: list[str] = []

    for path in FILES:
        if not (ROOT / path).is_file():
            errors.append(f"missing: {path}")
    if errors:
        print("\n".join(errors))
        return 1

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

    schema_paths = [path for path in FILES if path.startswith("schemas/")]
    schema_documents: dict[str, JsonObject] = {}
    for path in schema_paths:
        schema = load(path)
        schema_documents[path] = schema
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{path}: schema version mismatch")
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            errors.append(f"{path}{json_path(error.absolute_path)}: invalid schema: {error.message}")

    fixtures_by_path: dict[str, JsonObject] = {}
    for fixture_path, schema_path in FIXTURE_SCHEMAS.items():
        fixture = load(fixture_path)
        fixtures_by_path[fixture_path] = fixture
        errors.extend(schema_errors(fixture, schema_documents[schema_path], fixture_path))

    scenario = fixtures_by_path["fixtures/scenarios/market-entry-001.json"]
    if set(scenario.get("evaluation_opportunities", {})) != CANDIDATE_DIMENSIONS:
        errors.append("scenario must declare seven evaluation opportunities")
    if not scenario.get("instance_rubrics"):
        errors.append("scenario requires instance rubrics")

    episode = fixtures_by_path["fixtures/episodes/example-episode-v0.1.json"]
    errors.extend(validate_episode_integrity(episode, "fixtures/episodes/example-episode-v0.1.json"))
    message_ids = {item["message_id"] for item in episode.get("messages", []) if "message_id" in item}

    annotation = fixtures_by_path["fixtures/annotations/example-human-annotation-v0.1.json"]
    errors.extend(
        validate_dimension_results(
            annotation, "dimensions", "fixtures/annotations/example-human-annotation-v0.1.json"
        )
    )
    errors.extend(
        validate_evidence_references(
            annotation,
            "dimensions",
            message_ids,
            "fixtures/annotations/example-human-annotation-v0.1.json",
        )
    )

    result = fixtures_by_path["fixtures/results/example-evaluation-result-v0.1.json"]
    errors.extend(
        validate_dimension_results(
            result, "candidate_dimensions", "fixtures/results/example-evaluation-result-v0.1.json"
        )
    )
    errors.extend(
        validate_evidence_references(
            result,
            "candidate_dimensions",
            message_ids,
            "fixtures/results/example-evaluation-result-v0.1.json",
        )
    )

    negative_fixtures = {
        "scenario": scenario,
        "episode": episode,
        "annotation": annotation,
        "result": result,
    }
    negative_schemas = {
        "scenario": schema_documents["schemas/scenario-v0.1.schema.json"],
        "episode": schema_documents["schemas/episode-v0.1.schema.json"],
        "annotation": schema_documents["schemas/annotation-v0.1.schema.json"],
        "result": schema_documents["schemas/evaluation-result-v0.1.schema.json"],
    }
    errors.extend(run_negative_tests(negative_fixtures, negative_schemas))

    if errors:
        print("Evaluation contract validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print("Evaluation contract v0.1 OK")
    print("JSON Schema validation: Draft 2020-12 with format checking")
    print("Negative contract tests: 18 passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
