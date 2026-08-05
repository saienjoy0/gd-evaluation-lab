"""Build AI/system quality without importing candidate-performance rules."""
from __future__ import annotations

from typing import Any, Callable

from .stakeholder_conflict import finalize_before_conflict, silence_minority_concern


class UnsupportedQualityRuleError(ValueError):
    pass


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


def _ai_defines_scope_before_candidate(
    episode: dict[str, Any], target_participant_id: str
) -> dict[str, Any]:
    messages = _messages(episode)
    first_user_start = min(
        (
            message["start_ms"]
            for message in messages
            if message.get("speaker_type") == "user"
            and message.get("participant_id") == target_participant_id
        ),
        default=float("inf"),
    )
    offenders = [
        message
        for message in messages
        if message.get("speaker_type") == "ai"
        and message.get("move") in {"define_scope", "define_criteria"}
        and message.get("start_ms", 0) < first_user_start
    ]
    return {
        "failed": bool(offenders),
        "message_ids": [message["message_id"] for message in offenders],
        "event_ids": [],
        "pass_detail": "AIによる先回りの課題定義は観察されない。",
    }


def _private_concern_revealed_without_trigger(
    episode: dict[str, Any], target_participant_id: str
) -> dict[str, Any]:
    del target_participant_id
    concerns = [
        event
        for event in episode.get("events", [])
        if event.get("event") == "PRIVATE_CONCERN_REVEALED"
    ]
    messages = {
        message["message_id"]: message for message in episode.get("messages", [])
    }
    invalid = [
        event
        for event in concerns
        if event.get("trigger_move")
        not in {"ask_question", "compare_options", "challenge"}
        or event.get("message_id") not in messages
        or not any(
            message.get("move") == event.get("trigger_move")
            and message.get("end_ms", 0) <= event.get("timestamp_ms", 0)
            and message.get("message_id") != event.get("message_id")
            for message in messages.values()
        )
    ]
    return {
        "failed": bool(invalid),
        "message_ids": [
            event["message_id"] for event in concerns if event.get("message_id")
        ],
        "event_ids": [event["event_id"] for event in concerns],
        "pass_detail": "triggerなしの非公開懸念開示は観察されない。",
    }


_PROHIBITED_HANDLERS: dict[
    str, Callable[[dict[str, Any], str], dict[str, Any]]
] = {
    "ai_defines_scope_before_candidate": _ai_defines_scope_before_candidate,
    "private_concern_revealed_without_trigger": _private_concern_revealed_without_trigger,
    "finalize_before_conflict": finalize_before_conflict,
    "silence_minority_concern": silence_minority_concern,
}


def _quality_status(results: list[dict[str, Any]]) -> str:
    failed = [result for result in results if result["outcome"] == "fail"]
    if any(result["severity"] == "critical" for result in failed):
        return "fail"
    return "warn" if failed else "pass"


def build_system_quality(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    deterministic_result: dict[str, Any],
    target_participant_id: str,
    evaluator_version: str,
) -> dict[str, Any]:
    results = [
        {key: value for key, value in result.items() if key != "target"}
        for result in deterministic_result["rule_results"]
        if result["target"] == "ai_system"
    ]

    explicit = {
        event.get("condition_id"): event
        for event in episode.get("events", [])
        if event.get("event") == "PROHIBITED_CONDITION_TRIGGERED"
    }
    for condition in scenario.get("prohibited_conditions", []):
        rule_id = condition.get("rule_id")
        handler = _PROHIBITED_HANDLERS.get(rule_id)
        if handler is None:
            raise UnsupportedQualityRuleError(
                f"UNIMPLEMENTED_QUALITY_RULE: {rule_id}"
            )
        outcome = handler(episode, target_participant_id)
        triggered = condition["condition_id"] in explicit
        failed = bool(outcome["failed"] or triggered)
        event_ids = list(outcome["event_ids"])
        if (
            triggered
            and explicit[condition["condition_id"]].get("event_id") not in event_ids
        ):
            event_ids.append(explicit[condition["condition_id"]]["event_id"])
        results.append(
            {
                "rule_id": condition["condition_id"],
                "outcome": "fail" if failed else "pass",
                "severity": condition["severity"],
                "evidence_message_ids": outcome["message_ids"],
                "evidence_event_ids": event_ids,
                "affected_dimensions": condition["affected_dimensions"],
                "detail": (
                    "禁止条件が発生した。" if failed else outcome["pass_detail"]
                ),
            }
        )

    status = _quality_status(results)
    agency_ok = not any(
        result["outcome"] == "fail" and result["severity"] == "critical"
        for result in results
    )
    dimension_scores = {
        "goal_progression": 4,
        "responsiveness": 4,
        "user_agency": 5 if agency_ok else 2,
        "role_believability": 4,
        "discussion_coherence": 4,
        "novelty_and_repetition": 4,
        "consensus_quality": 4,
        "natural_pacing": 4,
    }
    return {
        "contract_version": "0.1",
        "result_id": f"sq-{episode['session_id']}",
        "session_id": episode["session_id"],
        "scenario_id": episode["scenario_id"],
        "scenario_version": episode["scenario_version"],
        "evaluator_version": evaluator_version,
        "status": status,
        "rule_results": results,
        "dimension_scores": dimension_scores,
    }
