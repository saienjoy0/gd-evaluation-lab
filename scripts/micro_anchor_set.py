"""Micro Anchor set manifest and ladder validation."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from micro_anchor_contract import (
    DIMENSION_SHORTS,
    SCORE_ORDER,
    AnchorValidationError,
    anchor_paths,
    load_json,
    validate_schema,
)


def content_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score_sort_key(score: int | str) -> int:
    return SCORE_ORDER.index(score)


def derive_coverage(anchors: list[dict[str, Any]]) -> dict[str, list[int | str]]:
    coverage = {dimension: [] for dimension in DIMENSION_SHORTS}
    for anchor in anchors:
        coverage[anchor["target_dimension"]].append(anchor["target_score"])
    return {
        dimension: sorted(values, key=score_sort_key)
        for dimension, values in coverage.items()
    }


def validate_anchor_collection(
    anchors: list[dict[str, Any]],
) -> None:
    ids = [anchor["anchor_id"] for anchor in anchors]
    if len(ids) != len(set(ids)):
        raise AnchorValidationError("ANCHOR_SET_ID_DUPLICATED")

    cells = [
        (anchor["target_dimension"], anchor["target_score"])
        for anchor in anchors
    ]
    if len(cells) != len(set(cells)):
        raise AnchorValidationError("ANCHOR_SET_CELL_DUPLICATED")

    coverage = derive_coverage(anchors)
    expected_ladder = list(SCORE_ORDER)
    for dimension, values in coverage.items():
        if values and values != expected_ladder:
            raise AnchorValidationError(
                "ANCHOR_SET_LADDER_INCOMPLETE",
                f"{dimension}: {values}",
            )

    by_dimension: dict[str, list[dict[str, Any]]] = {
        dimension: [] for dimension in DIMENSION_SHORTS
    }
    for anchor in anchors:
        by_dimension[anchor["target_dimension"]].append(anchor)

    for dimension, dimension_anchors in by_dimension.items():
        if not dimension_anchors:
            continue
        numeric = {
            anchor["target_score"]: anchor
            for anchor in dimension_anchors
            if isinstance(anchor["target_score"], int)
        }
        reference = numeric[1]
        reference_context = reference["scenario_context"]
        reference_opportunity = reference["opportunity_description"][
            "opportunity_id"
        ]
        reference_participants = reference["participants"]
        reference_target = reference["target_participant_id"]

        def non_target_signature(anchor: dict[str, Any]) -> list[tuple[Any, ...]]:
            target_id = anchor["target_participant_id"]
            return [
                (
                    message["message_id"],
                    message["sequence_index"],
                    message["participant_id"],
                    message["speaker_type"],
                    message["phase"],
                    message["move"],
                    message["text"],
                )
                for message in anchor["micro_episode"]
                if message["participant_id"] != target_id
            ]

        def target_control_signature(anchor: dict[str, Any]) -> list[tuple[Any, ...]]:
            target_id = anchor["target_participant_id"]
            return [
                (
                    message["message_id"],
                    message["sequence_index"],
                    message["participant_id"],
                    message["speaker_type"],
                    message["phase"],
                )
                for message in anchor["micro_episode"]
                if message["participant_id"] == target_id
            ]

        reference_non_target = non_target_signature(reference)
        reference_target_control = target_control_signature(reference)
        candidate_lengths: list[int] = []

        for score in (1, 2, 3, 4):
            anchor = numeric[score]
            if anchor["scenario_context"] != reference_context:
                raise AnchorValidationError(
                    "LADDER_SCENARIO_CONTEXT_DIFFER", f"{dimension}:{score}"
                )
            if (
                anchor["opportunity_description"]["opportunity_id"]
                != reference_opportunity
            ):
                raise AnchorValidationError(
                    "LADDER_OPPORTUNITY_ID_DIFFER", f"{dimension}:{score}"
                )
            if anchor["participants"] != reference_participants:
                raise AnchorValidationError(
                    "LADDER_PARTICIPANTS_DIFFER", f"{dimension}:{score}"
                )
            if non_target_signature(anchor) != reference_non_target:
                raise AnchorValidationError(
                    "LADDER_NON_TARGET_MESSAGES_DIFFER",
                    f"{dimension}:{score}",
                )
            if target_control_signature(anchor) != reference_target_control:
                raise AnchorValidationError(
                    "LADDER_TARGET_TURN_CONTROL_DIFFER",
                    f"{dimension}:{score}",
                )
            candidate_lengths.append(
                sum(
                    len(message["text"])
                    for message in anchor["micro_episode"]
                    if message["participant_id"] == reference_target
                )
            )

        shortest = min(candidate_lengths)
        longest = max(candidate_lengths)
        if shortest == 0 or longest / shortest > 1.8:
            raise AnchorValidationError(
                "LADDER_TEXT_LENGTH_IMBALANCED",
                f"{dimension}: {candidate_lengths}",
            )


def validate_manifest(
    root: Path,
    manifest: dict[str, Any] | None = None,
    anchors: list[dict[str, Any]] | None = None,
) -> None:
    manifest_path = root / "fixtures" / "anchors" / "anchor-set-v0.1.json"
    if manifest is None:
        manifest = load_json(manifest_path)
    validate_schema(
        manifest,
        root / "schemas" / "micro-anchor-set-v0.1.schema.json",
        code="MICRO_ANCHOR_SET_SCHEMA_INVALID",
    )

    actual_paths = anchor_paths(root)
    if anchors is None:
        anchors = [load_json(path) for path in actual_paths]
    validate_anchor_collection(anchors)

    entries = manifest["anchors"]
    if manifest["implemented_anchor_count"] != len(entries):
        raise AnchorValidationError("ANCHOR_SET_COUNT_MISMATCH")
    if len(entries) != len(anchors):
        raise AnchorValidationError("ANCHOR_SET_FILE_COUNT_MISMATCH")

    entry_ids = [entry["anchor_id"] for entry in entries]
    if len(entry_ids) != len(set(entry_ids)):
        raise AnchorValidationError("ANCHOR_SET_MANIFEST_ID_DUPLICATED")

    actual_by_id = {anchor["anchor_id"]: anchor for anchor in anchors}
    path_by_id = {
        load_json(path)["anchor_id"]: path
        for path in actual_paths
    }
    if set(entry_ids) != set(actual_by_id):
        raise AnchorValidationError("ANCHOR_SET_MANIFEST_MEMBERSHIP_MISMATCH")

    for entry in entries:
        anchor_id = entry["anchor_id"]
        anchor = actual_by_id[anchor_id]
        path = path_by_id[anchor_id]
        expected_relative = path.relative_to(root).as_posix()
        if entry["path"] != expected_relative:
            raise AnchorValidationError(
                "ANCHOR_SET_PATH_MISMATCH", anchor_id
            )
        if entry["target_dimension"] != anchor["target_dimension"]:
            raise AnchorValidationError(
                "ANCHOR_SET_DIMENSION_MISMATCH", anchor_id
            )
        if entry["target_score"] != anchor["target_score"]:
            raise AnchorValidationError(
                "ANCHOR_SET_SCORE_MISMATCH", anchor_id
            )
        if entry["sha256"] != content_sha256(path):
            raise AnchorValidationError(
                "ANCHOR_SET_HASH_MISMATCH", anchor_id
            )

    actual_coverage = derive_coverage(anchors)
    if manifest["coverage"] != actual_coverage:
        raise AnchorValidationError("ANCHOR_SET_COVERAGE_MISMATCH")
    if manifest["implemented_anchor_count"] != len(anchors):
        raise AnchorValidationError("ANCHOR_SET_IMPLEMENTED_COUNT_INVALID")

    if len(anchors) < manifest["expected_anchor_count"]:
        if manifest["status"] != "partial":
            raise AnchorValidationError(
                "ANCHOR_SET_PARTIAL_STATUS_REQUIRED"
            )
    elif len(anchors) == manifest["expected_anchor_count"]:
        if manifest["status"] == "partial":
            raise AnchorValidationError(
                "ANCHOR_SET_COMPLETION_STATUS_REQUIRED"
            )
    else:
        raise AnchorValidationError("ANCHOR_SET_TOO_MANY_ANCHORS")
