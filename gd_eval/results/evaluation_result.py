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


def _target_message_ids(
    episode: dict[str, Any], target_participant_id: str
) -> set[str]:
    return {
        message["message_id"]
        for message in episode.get("messages", [])
        if message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
    }


def _rubric_dimension(
    candidate_rubric: dict[str, Any], dimension: str
) -> dict[str, Any]:
    rubric_dimension = next(
        (
            item
            for item in candidate_rubric.get("dimensions", [])
            if item.get("id") == dimension
        ),
        None,
    )
    if rubric_dimension is None:
        raise EvaluationBuildError(f"RUBRIC_DIMENSION_MISSING: {dimension}")
    return rubric_dimension


def _minimum_valid_opportunities(
    candidate_rubric: dict[str, Any], dimension: str
) -> int:
    rubric_dimension = _rubric_dimension(candidate_rubric, dimension)
    explicit = rubric_dimension.get("minimum_valid_opportunities")
    if explicit is not None:
        return max(1, int(explicit))
    evidence_policy = rubric_dimension.get("evidence_policy", {})
    return max(1, int(evidence_policy.get("minimum_for_scored_result", 1)))


def _minimum_selected_evidence(
    candidate_rubric: dict[str, Any], dimension: str, score: int
) -> int:
    rubric_dimension = _rubric_dimension(candidate_rubric, dimension)
    evidence_policy = rubric_dimension.get("evidence_policy", {})
    if score == 4:
        return max(2, int(evidence_policy.get("minimum_for_score_4", 2)))
    return max(1, int(evidence_policy.get("minimum_for_scored_result", 1)))


def _validate_human_inputs(
    episode: dict[str, Any],
    target_participant_id: str,
    candidate_rubric: dict[str, Any],
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

    failed_rules_by_dimension: dict[str, set[str]] = {}
    for result in system_quality["rule_results"]:
        if result["outcome"] != "fail":
            continue
        for dimension in result["affected_dimensions"]:
            failed_rules_by_dimension.setdefault(dimension, set()).add(result["rule_id"])

    score_maps: list[dict[str, int | str]] = []
    rater_linked_response_ids: dict[str, set[str]] = {}
    for sheet in rater_sheets:
        dimensions = {item["dimension"]: item for item in sheet["dimensions"]}
        score_maps.append({key: item["score"] for key, item in dimensions.items()})
        for dimension, item in dimensions.items():
            selected_evidence = set(item["selected_evidence_message_ids"])
            if any(message_id not in target_messages for message_id in selected_evidence):
                raise EvaluationBuildError(
                    f"EVIDENCE_OWNER_MISMATCH: {sheet['sheet_id']}:{dimension}"
                )

            referenced_opportunities: list[dict[str, Any]] = []
            for event_id in item["opportunity_evidence_event_ids"]:
                opportunity = event_to_opportunity.get(event_id)
                if opportunity is None:
                    raise EvaluationBuildError(
                        f"UNKNOWN_OPPORTUNITY_EVENT: {event_id}"
                    )
                referenced_opportunities.append(opportunity)

            if item["score"] == "NE":
                if selected_evidence:
                    raise EvaluationBuildError(
                        f"NE_EVIDENCE_NOT_EMPTY: {sheet['sheet_id']}:{dimension}"
                    )
                continue

            if not referenced_opportunities:
                raise EvaluationBuildError(
                    f"NUMERIC_OPPORTUNITY_EVIDENCE_MISSING: {sheet['sheet_id']}:{dimension}"
                )
            if any(
                opportunity["status"] != "offered"
                or opportunity["response_status"] != "observed"
                for opportunity in referenced_opportunities
            ):
                raise EvaluationBuildError(
                    f"INVALIDATED_OPPORTUNITY_NUMERIC_SCORE: {dimension}"
                )

            minimum_primary = _minimum_valid_opportunities(
                candidate_rubric, dimension
            )
            primary_opportunities = [
                opportunity
                for opportunity in referenced_opportunities
                if opportunity["dimension"] == dimension
            ]
            if len(primary_opportunities) < minimum_primary:
                raise EvaluationBuildError(
                    f"PRIMARY_OPPORTUNITY_EVIDENCE_INSUFFICIENT: "
                    f"{sheet['sheet_id']}:{dimension}"
                )

            eligible_response_ids = {
                message_id
                for opportunity in referenced_opportunities
                for message_id in opportunity["candidate_response_message_ids"]
            }
            required_evidence = _minimum_selected_evidence(
                candidate_rubric, dimension, int(item["score"])
            )
            if len(selected_evidence) < required_evidence:
                raise EvaluationBuildError(
                    f"INSUFFICIENT_SELECTED_EVIDENCE: {sheet['sheet_id']}:{dimension}"
                )
            if not selected_evidence.issubset(eligible_response_ids):
                raise EvaluationBuildError(
                    f"EVIDENCE_NOT_LINKED_TO_OPPORTUNITY: {sheet['sheet_id']}:{dimension}"
                )
            rater_linked_response_ids.setdefault(dimension, set()).update(
                eligible_response_ids
            )

    for resolution in adjudication["dimension_resolutions"]:
        dimension = resolution["dimension"]
        expected_scores = [score_maps[0][dimension], score_maps[1][dimension]]
        if resolution["rater_scores"] != expected_scores:
            raise EvaluationBuildError(f"RATER_SCORE_MISMATCH: {dimension}")
        if resolution["agreement_class"] != _agreement_class(*expected_scores):
            raise EvaluationBuildError(f"AGREEMENT_CLASS_MISMATCH: {dimension}")

        final_evidence = set(resolution["final_evidence_message_ids"])
        if any(message_id not in target_messages for message_id in final_evidence):
            raise EvaluationBuildError(
                f"EVIDENCE_OWNER_MISMATCH: adjudication:{dimension}"
            )

        score = resolution["final_score"]
        valid = [
            item
            for item in by_dimension.get(dimension, [])
            if item["status"] == "offered"
            and item["response_status"] == "observed"
        ]
        failed_rule_ids = failed_rules_by_dimension.get(dimension, set())
        causal_invalid = [
            item
            for item in by_dimension.get(dimension, [])
            if item["status"] == "invalid"
            and failed_rule_ids.intersection(item.get("invalidated_by", []))
        ]
        minimum_valid = _minimum_valid_opportunities(candidate_rubric, dimension)
        has_sufficient_valid = len(valid) >= minimum_valid

        if score != "NE":
            if not has_sufficient_valid:
                raise EvaluationBuildError(
                    f"INSUFFICIENT_VALID_OPPORTUNITY_NUMERIC_SCORE: {dimension}"
                )
            required_evidence = _minimum_selected_evidence(
                candidate_rubric, dimension, int(score)
            )
            if len(final_evidence) < required_evidence:
                raise EvaluationBuildError(
                    f"INSUFFICIENT_ADJUDICATION_EVIDENCE: {dimension}"
                )
            eligible_response_ids = rater_linked_response_ids.get(dimension, set())
            if not final_evidence.issubset(eligible_response_ids):
                raise EvaluationBuildError(
                    f"ADJUDICATION_EVIDENCE_NOT_LINKED_TO_OPPORTUNITY: {dimension}"
                )
        else:
            if final_evidence:
                raise EvaluationBuildError(
                    f"NE_EVIDENCE_NOT_EMPTY: adjudication:{dimension}"
                )
            reason = resolution.get("not_evaluable_reason")
            if not reason:
                raise EvaluationBuildError(f"NE_REASON_MISSING: {dimension}")
            allowed_reasons = set(
                _rubric_dimension(candidate_rubric, dimension).get("ne_conditions", [])
            )
            if reason not in allowed_reasons:
                raise EvaluationBuildError(
                    f"NE_REASON_NOT_ALLOWED_BY_RUBRIC: {dimension}:{reason}"
                )
            if reason == "AI_QUALITY_FAILURE":
                if not failed_rule_ids or not causal_invalid or has_sufficient_valid:
                    raise EvaluationBuildError(
                        f"AI_QUALITY_NE_WITHOUT_CAUSAL_INSUFFICIENCY: {dimension}"
                    )
            elif reason == "INSUFFICIENT_OPPORTUNITY":
                if has_sufficient_valid:
                    raise EvaluationBuildError(
                        f"INSUFFICIENT_OPPORTUNITY_WITH_SUFFICIENT_VALID: {dimension}"
                    )
            else:
                raise EvaluationBuildError(
                    f"UNSUPPORTED_NE_REASON: {dimension}:{reason}"
                )

        if score == 4:
            message_by_id = {
                message["message_id"]: message
                for message in episode.get("messages", [])
            }
            phases = {
                message_by_id[message_id]["phase"]
                for message_id in resolution["final_evidence_message_ids"]
            }
            if len(phases) < 2:
                raise EvaluationBuildError(
                    f"SCORE4_PHASE_DIVERSITY: {dimension}"
                )


def _display_groups(
    candidate_dimensions: list[dict[str, Any]],
    candidate_rubric: dict[str, Any],
) -> dict[str, Any]:
    dimension_map = {item["dimension"]: item for item in candidate_dimensions}
    groups: dict[str, Any] = {}
    for group_id, definition in candidate_rubric["display_groups"].items():
        group_dimensions = [
            dimension_map[dimension] for dimension in definition["dimensions"]
        ]
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
            "coverage": {
                "evaluated": len(numeric),
                "total": len(group_dimensions),
            },
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
        candidate_rubric,
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
