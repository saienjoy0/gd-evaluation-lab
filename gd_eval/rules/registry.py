"""Fail-closed deterministic rule registry."""
from __future__ import annotations

from typing import Any

from .common import (
    RuleHandler,
    candidate_move_types,
    private_concern_triggered_release,
    resolved_context_keys,
    summary_contains_fields,
    user_message_before_action,
)
from .numeric import numeric_constraint_preserved
from .stakeholder_conflict import (
    candidate_integrates_positions,
    candidate_response_to_concern,
    challenge_after_first_candidate_proposal,
    decision_contains_fields,
    positions_and_challenge_before_phase,
)
from .time_boxed_decision import (
    candidate_compares_and_revises,
    candidate_prioritizes_after_time_check,
    private_concern_revealed_before_phase,
    time_checkpoints_followed_by_candidate_turn,
)


class UnsupportedRuleError(ValueError):
    pass


RULE_HANDLERS: dict[str, RuleHandler] = {
    "user_message_before_action": user_message_before_action,
    "resolved_context_keys": resolved_context_keys,
    "candidate_move_types": candidate_move_types,
    "private_concern_triggered_release": private_concern_triggered_release,
    "summary_contains_fields": summary_contains_fields,
    "positions_and_challenge_before_phase": positions_and_challenge_before_phase,
    "candidate_response_to_concern": candidate_response_to_concern,
    "candidate_integrates_positions": candidate_integrates_positions,
    "decision_contains_fields": decision_contains_fields,
    "challenge_after_first_candidate_proposal": challenge_after_first_candidate_proposal,
    "numeric_constraint_preserved": numeric_constraint_preserved,
    "time_checkpoints_followed_by_candidate_turn": (
        time_checkpoints_followed_by_candidate_turn
    ),
    "private_concern_revealed_before_phase": private_concern_revealed_before_phase,
    "candidate_prioritizes_after_time_check": candidate_prioritizes_after_time_check,
    "candidate_compares_and_revises": candidate_compares_and_revises,
}


def evaluate_deterministic_rules(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    target_participant_id: str,
    evaluator_version: str,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for rubric in scenario.get("instance_rubrics", []):
        rule = rubric.get("rule", {})
        deterministic_rule_id = rule.get("deterministic_rule_id")
        if not deterministic_rule_id:
            raise UnsupportedRuleError(f"RULE_ID_MISSING: {rubric.get('rubric_id')}")
        handler = RULE_HANDLERS.get(deterministic_rule_id)
        if handler is None:
            raise UnsupportedRuleError(f"UNIMPLEMENTED_RULE_ID: {deterministic_rule_id}")
        params = dict(rule.get("params", {}))
        params["target_participant_id"] = target_participant_id
        outcome = handler(scenario, episode, params)
        results.append(
            {
                "rule_id": rubric["rubric_id"],
                "target": rubric["target"],
                "outcome": "pass" if outcome["ok"] else "fail",
                "severity": rubric["severity"],
                "evidence_message_ids": outcome["evidence_message_ids"],
                "evidence_event_ids": outcome["evidence_event_ids"],
                "affected_dimensions": rubric["affected_dimensions"],
                "detail": outcome["detail"]
                if outcome["ok"]
                else "決定論的条件を満たさなかった。",
            }
        )

    return {
        "contract_version": "0.1",
        "result_id": f"dr-{episode['session_id']}",
        "session_id": episode["session_id"],
        "scenario_id": episode["scenario_id"],
        "scenario_version": episode["scenario_version"],
        "evaluator_version": evaluator_version,
        "rule_results": results,
    }
