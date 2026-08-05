"""Build evidence-based feedback strictly after EvaluationResult."""
from __future__ import annotations

import re
from typing import Any

from gd_eval.rules.exercise_a import compose_next_action, strength_headline


def _slice_id(case_id: str) -> str:
    return re.sub(r"-\d+$", "-v0.1", case_id)


def build_feedback(
    case_id: str,
    evaluation_result: dict[str, Any],
    candidate_rubric: dict[str, Any],
) -> dict[str, Any]:
    dimensions = evaluation_result["candidate_dimensions"]
    rubric_by_dimension = {
        item["id"]: item for item in candidate_rubric.get("dimensions", [])
    }
    narratives = {
        item["dimension"]: {
            "positive": item["positive_behavior"],
            "missing": item["missing_behavior"],
            "improvement": item["improvement"],
        }
        for item in dimensions
    }
    not_evaluable_dimensions = {
        item["dimension"]: {
            "evaluation_status": "not_evaluable",
            "reason_code": item["not_evaluable_reason"]["code"],
            "reason": item["not_evaluable_reason"]["detail"],
        }
        for item in dimensions
        if item["score"] == "NE" and item["not_evaluable_reason"] is not None
    }

    numeric = [item for item in dimensions if item["score"] != "NE"]
    strength_candidates = [item for item in numeric if int(item["score"]) >= 3]
    ranked = sorted(
        enumerate(strength_candidates),
        key=lambda pair: (-int(pair[1]["score"]), pair[0]),
    )
    strengths: list[str] = []
    used_groups: set[str] = set()
    for _, item in ranked:
        group = rubric_by_dimension[item["dimension"]]["display_group"]
        if group in used_groups:
            continue
        strengths.append(
            strength_headline(item["dimension"], item["positive_behavior"])
        )
        used_groups.add(group)
        if len(strengths) == 2:
            break

    lowest_score = min((int(item["score"]) for item in numeric), default=None)
    low_dimensions = [
        item["dimension"]
        for item in numeric
        if lowest_score is not None and int(item["score"]) == lowest_score
    ]
    improvements = {
        item["dimension"]: item["improvement"] for item in numeric
    }
    feedback = {
        "contract_version": "0.1",
        "slice_id": _slice_id(case_id),
        "dimension_narratives": narratives,
        "display_groups": evaluation_result["display_groups"],
        "strengths": strengths,
        "next_action": compose_next_action(low_dimensions, improvements),
        "limitations": "合成Episodeに基づく校正用フィードバックであり、採用判断には使用しない。",
    }
    if not_evaluable_dimensions:
        feedback["not_evaluable_dimensions"] = not_evaluable_dimensions
    return feedback
