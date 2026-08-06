"""Shared Micro Anchor v0.1 contract and semantic validation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

DIMENSION_SHORTS = {
    "issue_framing": "if",
    "logical_reasoning": "lr",
    "listening_and_response": "ls",
    "valuable_contribution": "vc",
    "collaboration_and_relationship": "cr",
    "decision_and_consensus": "dc",
    "process_and_time_management": "pt",
}
SCORE_ORDER = (1, 2, 3, 4, "NE")
FORBIDDEN_INFERENCE_PATTERNS = (
    "外向的",
    "内向的",
    "性格だから",
    "リーダー向き",
    "男性だから",
    "女性だから",
    "年齢だから",
    "障害があるから",
    "アクセントだから",
    "声が高いから",
    "視線が",
    "顔つき",
)
ANCHOR_RE = re.compile(
    r"^anchor-(if|lr|ls|vc|cr|dc|pt)-(1|2|3|4|ne)-([0-9]{3})$"
)


class AnchorValidationError(AssertionError):
    """Validation error carrying one stable machine-readable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def anchor_paths(root: Path) -> list[Path]:
    base = root / "fixtures" / "anchors"
    return sorted(
        path
        for path in base.glob("*/*.json")
        if path.parent.name not in {"blind"}
        and path.name != "anchor-set-v0.1.json"
    )


def validate_schema(
    document: dict[str, Any],
    schema_path: Path,
    code: str = "MICRO_ANCHOR_SCHEMA_INVALID",
) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(
            schema, format_checker=FormatChecker()
        ).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(item) for item in first.absolute_path)
        raise AnchorValidationError(code, f"{location}: {first.message}")


def score_token(score: int | str) -> str:
    return "ne" if score == "NE" else str(score)


def semantic_validate_anchor(
    anchor: dict[str, Any],
    path: Path,
    root: Path,
) -> None:
    anchor_id = anchor["anchor_id"]
    match = ANCHOR_RE.fullmatch(anchor_id)
    if match is None:
        raise AnchorValidationError("ANCHOR_ID_INVALID", anchor_id)

    dimension = anchor["target_dimension"]
    expected_short = DIMENSION_SHORTS[dimension]
    if match.group(1) != expected_short:
        raise AnchorValidationError(
            "ANCHOR_ID_DIMENSION_MISMATCH",
            f"{anchor_id}: expected {expected_short}",
        )
    expected_score_token = score_token(anchor["target_score"])
    if match.group(2) != expected_score_token:
        raise AnchorValidationError(
            "ANCHOR_ID_SCORE_MISMATCH",
            f"{anchor_id}: expected {expected_score_token}",
        )
    if path.parent.name != dimension:
        raise AnchorValidationError(
            "DIMENSION_PATH_MISMATCH",
            f"{path.parent.name} != {dimension}",
        )
    if path.stem != anchor_id:
        raise AnchorValidationError(
            "ANCHOR_FILENAME_MISMATCH",
            f"{path.stem} != {anchor_id}",
        )

    scenario_family = anchor["scenario_context"]["scenario_family_id"]
    if not scenario_family.startswith(f"anchor-family-{expected_short}-"):
        raise AnchorValidationError(
            "SCENARIO_FAMILY_DIMENSION_MISMATCH", scenario_family
        )
    opportunity_id = anchor["opportunity_description"]["opportunity_id"]
    if not opportunity_id.startswith(f"ANCHOR-{expected_short.upper()}-OP-"):
        raise AnchorValidationError(
            "OPPORTUNITY_DIMENSION_MISMATCH", opportunity_id
        )

    participants = anchor["participants"]
    participant_ids = [item["participant_id"] for item in participants]
    if len(participant_ids) != len(set(participant_ids)):
        raise AnchorValidationError("DUPLICATE_PARTICIPANT_ID")
    participant_by_id = {item["participant_id"]: item for item in participants}
    target_id = anchor["target_participant_id"]
    if target_id not in participant_by_id:
        raise AnchorValidationError("TARGET_PARTICIPANT_NOT_FOUND", target_id)
    target = participant_by_id[target_id]
    if target["speaker_type"] != "user" or target["role"] != "evaluation_target":
        raise AnchorValidationError("TARGET_PARTICIPANT_INVALID", target_id)

    messages = anchor["micro_episode"]
    message_ids = [message["message_id"] for message in messages]
    if len(message_ids) != len(set(message_ids)):
        raise AnchorValidationError("DUPLICATE_MESSAGE_ID")
    expected_sequence = list(range(1, len(messages) + 1))
    actual_sequence = [message["sequence_index"] for message in messages]
    if actual_sequence != expected_sequence:
        raise AnchorValidationError(
            "MESSAGE_SEQUENCE_INVALID",
            f"{actual_sequence} != {expected_sequence}",
        )

    moves = set(
        load_json(root / "contracts" / "move-vocabulary-v0.1.json")["moves"]
    )
    message_by_id = {message["message_id"]: message for message in messages}
    for message in messages:
        participant_id = message["participant_id"]
        if participant_id not in participant_by_id:
            raise AnchorValidationError(
                "MESSAGE_PARTICIPANT_NOT_FOUND", message["message_id"]
            )
        if (
            participant_by_id[participant_id]["speaker_type"]
            != message["speaker_type"]
        ):
            raise AnchorValidationError(
                "MESSAGE_SPEAKER_TYPE_MISMATCH", message["message_id"]
            )
        if message["move"] not in moves:
            raise AnchorValidationError(
                "MOVE_NOT_IN_VOCABULARY", message["move"]
            )

    for trigger_id in anchor["opportunity_description"]["trigger_message_ids"]:
        if trigger_id not in message_by_id:
            raise AnchorValidationError(
                "TRIGGER_MESSAGE_NOT_FOUND", trigger_id
            )

    evidence_ids = anchor["expected_evidence_message_ids"]
    for evidence_id in evidence_ids:
        if evidence_id not in message_by_id:
            raise AnchorValidationError(
                "EVIDENCE_MESSAGE_NOT_FOUND", evidence_id
            )
        evidence = message_by_id[evidence_id]
        if (
            evidence["participant_id"] != target_id
            or evidence["speaker_type"] != "user"
        ):
            raise AnchorValidationError(
                "EVIDENCE_OWNER_INVALID", evidence_id
            )

    score = anchor["target_score"]
    reason = anchor["expected_not_evaluable_reason"]
    opportunity_status = anchor["opportunity_description"]["status"]
    if isinstance(score, int):
        if not evidence_ids:
            raise AnchorValidationError("NUMERIC_EVIDENCE_REQUIRED")
        if reason is not None:
            raise AnchorValidationError("NUMERIC_NE_REASON_FORBIDDEN")
        if opportunity_status != "sufficient":
            if score == 1:
                raise AnchorValidationError(
                    "SCORE_1_REQUIRES_SUFFICIENT_OPPORTUNITY"
                )
            raise AnchorValidationError(
                "NUMERIC_REQUIRES_SUFFICIENT_OPPORTUNITY"
            )
        if score == 4:
            if len(evidence_ids) < 2:
                raise AnchorValidationError(
                    "SCORE_4_REQUIRES_TWO_EVIDENCE"
                )
            phases = {message_by_id[item]["phase"] for item in evidence_ids}
            if len(phases) < 2:
                raise AnchorValidationError(
                    "SCORE_4_REQUIRES_INDEPENDENT_PHASES"
                )
    else:
        if evidence_ids:
            raise AnchorValidationError("NE_EVIDENCE_MUST_BE_EMPTY")
        if reason is None:
            raise AnchorValidationError("NE_REASON_REQUIRED")
        if opportunity_status == "sufficient":
            raise AnchorValidationError(
                "NE_REQUIRES_NON_SUFFICIENT_OPPORTUNITY"
            )

    review_required_statuses = {
        "content_reviewed",
        "blind_calibration_pending",
        "approved",
    }
    if (
        anchor["approval_status"] in review_required_statuses
        and not anchor["reviewer"]
    ):
        raise AnchorValidationError("APPROVAL_REVIEWER_REQUIRED")

    searchable_text = "\n".join(
        [
            anchor["rationale"],
            json.dumps(anchor["boundary_note"], ensure_ascii=False),
            *[message["text"] for message in messages],
        ]
    )
    for pattern in FORBIDDEN_INFERENCE_PATTERNS:
        if pattern in searchable_text:
            raise AnchorValidationError(
                "FORBIDDEN_INFERENCE_FOUND", pattern
            )


def validate_anchor(
    anchor: dict[str, Any],
    path: Path,
    root: Path,
) -> None:
    validate_schema(
        anchor,
        root / "schemas" / "micro-anchor-v0.1.schema.json",
    )
    semantic_validate_anchor(anchor, path, root)
