"""Opportunity trigger and context handlers for stakeholder conflict."""
from __future__ import annotations

from typing import Any, Callable

TriggerHandler = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], bool]
ContextHandler = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any], str], bool
]


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


def _before(episode: dict[str, Any], timestamp: int) -> list[dict[str, Any]]:
    return [
        message
        for message in _messages(episode)
        if message.get("end_ms", 0) <= timestamp
    ]


def _after(episode: dict[str, Any], timestamp: int) -> list[dict[str, Any]]:
    return [
        message
        for message in _messages(episode)
        if message.get("start_ms", 0) >= timestamp
    ]


def _event_before(
    episode: dict[str, Any], event_name: str, timestamp: int, **criteria: Any
) -> bool:
    return any(
        item.get("event") == event_name
        and item.get("timestamp_ms", 0) <= timestamp
        and all(item.get(key) == value for key, value in criteria.items())
        for item in episode.get("events", [])
    )


def _after_criteria_request(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "ai"
        and message.get("move") == "ask_question"
        and message.get("phase") == "option_comparison"
        for message in _before(episode, event["timestamp_ms"])
    )


def _after_mitigation_request(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "ai"
        and message.get("move") == "ask_question"
        and message.get("phase") == "decision"
        for message in _before(episode, event["timestamp_ms"])
    )


def _after_concern(concern_id: str) -> TriggerHandler:
    def handler(
        scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
    ) -> bool:
        del scenario
        return _event_before(
            episode,
            "PRIVATE_CONCERN_REVEALED",
            event["timestamp_ms"],
            concern_id=concern_id,
        )

    return handler


def _after_tourism_challenge(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    concerns = [
        item
        for item in episode.get("events", [])
        if item.get("event") == "PRIVATE_CONCERN_REVEALED"
        and item.get("concern_id") == "tourism_seasonality"
        and item.get("timestamp_ms", 0) <= event["timestamp_ms"]
    ]
    messages = {
        message["message_id"]: message for message in episode.get("messages", [])
    }
    return any(
        item.get("message_id") in messages
        and messages[item["message_id"]].get("speaker_type") == "ai"
        and messages[item["message_id"]].get("move") == "challenge"
        for item in concerns
    )


def _after_three_proposals(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    prior = {
        message.get("participant_id")
        for message in _before(episode, event["timestamp_ms"])
        if message.get("speaker_type") == "ai"
        and message.get("move") == "propose_idea"
    }
    return len(prior) >= min(3, len(scenario.get("ai_participants", [])))


def _after_conflict_summary(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return _event_before(
        episode, "CONFLICT_SUMMARY_RECORDED", event["timestamp_ms"]
    )


def _after_first_challenge(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "ai"
        and message.get("move") == "challenge"
        for message in _before(episode, event["timestamp_ms"])
    )


def _after_minority_view(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return _event_before(episode, "MINORITY_VIEW_PRESENT", event["timestamp_ms"])


def _before_final_alignment(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "user"
        and message.get("move") == "confirm_consensus"
        for message in _after(episode, event["timestamp_ms"])
    )


def _after_criteria_defined(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "user"
        and message.get("move") == "define_criteria"
        and message.get("phase") == "option_comparison"
        for message in _before(episode, event["timestamp_ms"])
    )


def _after_budget_split_proposal(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return _event_before(episode, "BUDGET_SPLIT_PROPOSED", event["timestamp_ms"])


def _after_extended_conflict(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    challenges = [
        message
        for message in _before(episode, event["timestamp_ms"])
        if message.get("speaker_type") == "ai"
        and message.get("move") == "challenge"
    ]
    return len(challenges) >= 3


def _resolved_before(episode: dict[str, Any], key: str, timestamp: int) -> bool:
    return any(
        event.get("event") == "CONTEXT_RESOLVED"
        and event.get("key") == key
        and event.get("timestamp_ms", 0) <= timestamp
        for event in episode.get("events", [])
    )


def _concern_open(
    episode: dict[str, Any], concern_id: str, timestamp: int
) -> bool:
    revealed = _event_before(
        episode,
        "PRIVATE_CONCERN_REVEALED",
        timestamp,
        concern_id=concern_id,
    )
    addressed = _event_before(
        episode,
        "MINORITY_CONCERN_STATUS",
        timestamp,
        concern_id=concern_id,
        status="addressed",
    )
    return revealed and not addressed


def _three_stakeholder_goals_visible(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del target_participant_id
    prior = {
        message.get("participant_id")
        for message in _before(episode, event["timestamp_ms"])
        if message.get("speaker_type") == "ai"
        and message.get("move") == "propose_idea"
    }
    return len(prior) >= min(3, len(scenario.get("ai_participants", [])))


def _criteria_not_yet_fixed(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return not _resolved_before(
        episode, "comparison_criteria", event["timestamp_ms"]
    )


def _unselected_priority_exists(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return any(
        item.get("event")
        in {"BUDGET_SPLIT_RECORDED", "DECISION_ALLOCATION_RECORDED"}
        and item.get("unselected_priorities")
        and item.get("timestamp_ms", 0) <= event["timestamp_ms"]
        for item in episode.get("events", [])
    )


def _open_concern_context(concern_id: str) -> ContextHandler:
    def handler(
        scenario: dict[str, Any],
        episode: dict[str, Any],
        event: dict[str, Any],
        target_participant_id: str,
    ) -> bool:
        del scenario, target_participant_id
        return _concern_open(episode, concern_id, event["timestamp_ms"])

    return handler


def _integration_space_open(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario
    return not any(
        message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
        and message.get("move") == "confirm_consensus"
        for message in _before(episode, event["timestamp_ms"])
    )


def _conflict_active(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario
    prior = _before(episode, event["timestamp_ms"])
    return any(
        message.get("speaker_type") == "ai"
        and message.get("move") == "challenge"
        for message in prior
    ) and not any(
        message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
        and message.get("move") == "confirm_consensus"
        for message in prior
    )


def _minority_view_present(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return _event_before(episode, "MINORITY_VIEW_PRESENT", event["timestamp_ms"])


def _allocation_tradeoff_visible(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return _event_before(
        episode, "BUDGET_SPLIT_PROPOSED", event["timestamp_ms"]
    )


def _mitigation_required(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return _event_before(episode, "MITIGATION_REQUIRED", event["timestamp_ms"])


TRIGGER_HANDLERS: dict[str, TriggerHandler] = {
    "after_criteria_request": _after_criteria_request,
    "after_mitigation_request": _after_mitigation_request,
    "after_childcare_concern": _after_concern("childcare_low_utilization"),
    "after_transport_concern": _after_concern("transport_driver_shortage"),
    "after_tourism_challenge": _after_tourism_challenge,
    "after_three_proposals": _after_three_proposals,
    "after_conflict_summary": _after_conflict_summary,
    "after_first_challenge": _after_first_challenge,
    "after_minor_position_ignored": _after_minority_view,
    "before_final_alignment": _before_final_alignment,
    "after_criteria_defined": _after_criteria_defined,
    "after_budget_split_proposal": _after_budget_split_proposal,
    "before_consensus_confirmation": _before_final_alignment,
    "after_extended_conflict": _after_extended_conflict,
}

CONTEXT_HANDLERS: dict[str, ContextHandler] = {
    "three_stakeholder_goals_visible": _three_stakeholder_goals_visible,
    "criteria_not_yet_fixed": _criteria_not_yet_fixed,
    "unselected_priority_exists": _unselected_priority_exists,
    "childcare_concern_open": _open_concern_context(
        "childcare_low_utilization"
    ),
    "transport_concern_open": _open_concern_context(
        "transport_driver_shortage"
    ),
    "tourism_concern_open": _open_concern_context("tourism_seasonality"),
    "three_options_available": _three_stakeholder_goals_visible,
    "integration_space_open": _integration_space_open,
    "conflict_active": _conflict_active,
    "minority_view_present": _minority_view_present,
    "disagreement_remaining": _conflict_active,
    "allocation_tradeoff_visible": _allocation_tradeoff_visible,
    "mitigation_required": _mitigation_required,
}
