"""Build final EvaluationResult from human calibration and verified opportunities."""
from __future__ import annotations

from typing import Any

from gd_eval.rules.exercise_a import group_summary, narrative


class EvaluationBuildError(ValueError):
    pass


def _agreement_class(left: int | str, right: int | str) -> str:
    if left == right:
        return "exact"
    if "NE" in (left, right):
        return "ne_disagreement"
    return "adjacent" if abs(int(left) - int(right)) == 1 else "major_disagreement"


def _target_message_ids(episode: dict[str, Any], target_participant_id: str) -> set[str]:
    return {
        message["message_id"]
        for message in episode.get("messages", [])
        if message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
    }


def _validate_human_inputs(
    episode: dict[str, Any],
    target_participant_id: str,
    rater_sheets: tuple[dict[str, Any], ...],
    adjudication: dict[str, Any],
    opportunities: dict[str, Any],
    system_quality: dict[str, Any],
) -> None:
    target_messages = _target_message_ids(episode, target_participant_id)
    event_to_opportunity: dict[str, dict[str, Any]] = {}
    by_dimension: dict[str, list[dict[str, Any]]] = {}
    for item in opportunities["items"]:
        by_dimension.setdefault(item["dimension"], []).append(item)
        for event_id in item["trigger_event_ids"]:
            event_to_opportunity[event_id] = item

    score_maps: list[dict[str, int | str]] = []
    for sheet in rater_sheets:
        dimensions = {item["dimension"]: item for item in sheet["dimensions"]}
        score_maps.append({key: item["score"] for key, item in dimensions.items()})
        for dimension, item in dimensions.items():
            if any(mid not in target_messages for mid in item["selected_evidence_message_ids"]):
                raise EvaluationBuildError(f"EVIDENCE_OWNER_MISMATCH: {sheet['sheet_id']}:{dimension}")
            for event_id in item["opportunity_evidence_event_ids"]:
                opportunity = event_to_opportunity.get(event_id)
                if opportunity is None:
                    raise EvaluationBuildError(f"UNKNOWN_OPPORTUNITY_EVENT: {event_id}")
                if opportunity["dimension"] != dimension or opportunity["status"] != "offered":
                    raise EvaluationBuildError(
                        f"INVALIDATED_OPPORTUNITY_NUMERIC_SCORE: {dimension}"
                    )

    failed_dimensions = {
        dimension
        for result in system_quality["rule_results"]
        if result["outcome"] == "fail"
        for dimension in result["affected_dimensions"]
    }
    for resolution in adjudication["dimension_resolutions"]:
        dimension = resolution["dimension"]
        expected_scores = [score_maps[0][dimension], score_maps[1][dimension]]
        if resolution["rater_scores"] != expected_scores:
            raise EvaluationBuildError(f"RATER_SCORE_MISMATCH: {dimension}")
        if resolution["agreement_class"] != _agreement_class(*expected_scores):
            raise EvaluationBuildError(f"AGREEMENT_CLASS_MISMATCH: {dimension}")
        if any(mid not in target_messages for mid in resolution["final_evidence_message_ids"]):
            raise EvaluationBuildError(f"EVIDENCE_OWNER_MISMATCH: adjudication:{dimension}")

        score = resolution["final_score"]
        offered = [
            item
            for item in by_dimension.get(dimension, [])
            if item["status"] == "offered" and item["response_status"] == "observed"
        ]
        if score != "NE" and (dimension in failed_dimensions or not offered):
            raise EvaluationBuildError(
                f"INVALIDATED_OPPORTUNITY_NUMERIC_SCORE: {dimension}"
            )
        if score == "NE" and not resolution.get("not_evaluable_reason"):
            raise EvaluationBuildError(f"NE_REASON_MISSING: {dimension}")
        if score == 4:
            message_by_id = {
                message["message_id"]: message for message in episode.get("messages", [])
            }
            phases = {
                message_by_id[mid]["phase"]
                for mid in resolution["final_evidence_message_ids"]
            }
            if len(phases) < 2:
                raise EvaluationBuildError(f"SCORE4_PHASE_DIVERSITY: {dimension}")


def _display_groups(
    candidate_dimensions: list[dict[str, Any]],
    candidate_rubric: dict[str, Any],
) -> dict[str, Any]:
    dimension_map = {item["dimension"]: item for item in candidate_dimensions}
    groups: dict[str, Any] = {}
    for group_id, definition in candidate_rubric["display_groups"].items():
        group_dimensions = [dimension_map[dimension] for dimension in definition["dimensions"]]
        numeric = [item for item in group_dimensions if item["score"] != "NE"]
        if numeric:
            bottleneck = min(
                numeric,
                key=lambda item: (
                    int(item["score"]),
                    len(item["evidence_message_ids"]),
                    definition["dimensions"].index(item["dimension"]),
                ),
            )["dimension"]
            fallback = dimension_map[bottleneck]["missing_behavior"]
        else:
            bottleneck = None
            fallback = "有効な評価機会が不足したため、この領域は評価不能だった。"
        groups[group_id] = {
            "aggregation_status": "not_calibrated",
            "score": None,
            "coverage": {"evaluated": len(numeric), "total": len(group_dimensions)},
            "bottleneck_dimension": bottleneck,
            "summary": group_summary(bottleneck or "", fallback),
        }
    return groups


def build_evaluation_result(
    exercise_id: str,
    episode: dict[str, Any],
    target_participant_id: str,
    candidate_rubric: dict[str, Any],
    ai_quality_rubric: dict[str, Any],
    system_quality: dict[str, Any],
    opportunities: dict[str, Any],
    rater_sheets: tuple[dict[str, Any], ...],
    adjudication: dict[str, Any],
    deterministic_evaluator_version: str,
) -> dict[str, Any]:
    _validate_human_inputs(
        episode,
        target_participant_id,
        rater_sheets,
        adjudication,
        opportunities,
        system_quality,
    )
    rubric_dimensions = {
        item["id"]: item for item in candidate_rubric.get("dimensions", [])
    }
    candidate_dimensions: list[dict[str, Any]] = []
    for resolution in adjudication["dimension_resolutions"]:
        dimension = resolution["dimension"]
        score = resolution["final_score"]
        if score == "NE":
            positive = missing = improvement = ""
            not_evaluable = {
                "code": resolution["not_evaluable_reason"],
                "detail": resolution["resolution_reason"],
            }
            confidence = 0
        else:
            positive, missing, improvement = narrative(
                exercise_id,
                dimension,
                int(score),
                resolution,
                rubric_dimensions[dimension],
            )
            not_evaluable = None
            confidence = 0.9
        candidate_dimensions.append(
            {
                "dimension": dimension,
                "score": score,
                "confidence": confidence,
                "evidence_message_ids": resolution["final_evidence_message_ids"],
                "positive_behavior": positive,
                "missing_behavior": missing,
                "improvement": improvement,
                "not_evaluable_reason": not_evaluable,
                "question_results": [],
            }
        )

    violations = [
        {
            "rule_id": result["rule_id"],
            "severity": result["severity"],
            "message_ids": result["evidence_message_ids"],
            "affected_candidate_dimensions": result["affected_dimensions"],
        }
        for result in system_quality["rule_results"]
        if result["outcome"] == "fail"
    ]
    status = (
        "completed"
        if all(item["score"] != "NE" for item in candidate_dimensions)
        else "partial"
    )
    return {
        "contract_version": "0.1",
        "session_id": episode["session_id"],
        "target_participant_id": target_participant_id,
        "status": status,
        "ai_quality": {
            "status": system_quality["status"],
            "violations": violations,
            "dimension_scores": system_quality["dimension_scores"],
        },
        "candidate_dimensions": candidate_dimensions,
        "display_groups": _display_groups(candidate_dimensions, candidate_rubric),
        "version_info": {
            "rubric_version": candidate_rubric["version"],
            "ai_quality_rubric_version": ai_quality_rubric["version"],
            "scenario_version": episode["scenario_version"],
            "orchestrator_version": episode["versions"]["orchestrator_version"],
            "prompt_version": episode["versions"]["prompt_version"],
            "judge_model": "human-adjudication",
            "judge_version": "not-applied-v0.1",
            "deterministic_evaluator_version": deterministic_evaluator_version,
            "transcript_hash": episode["transcript_hash"],
        },
        "review_status": "completed",
        "legacy_evaluation": None,
        "evaluation_disagreement": None,
    }
