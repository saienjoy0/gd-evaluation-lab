"""Opportunity trigger/context handlers for time-boxed decisions."""
from __future__ import annotations

from typing import Any, Callable

TriggerHandler = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any]],
    bool,
]
ContextHandler = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any], str],
    bool,
]


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


def _message_map(
    episode: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        message["message_id"]: message
        for message in episode.get("messages", [])
    }


def _before(
    episode: dict[str, Any],
    timestamp: int,
) -> list[dict[str, Any]]:
    return [
        message
        for message in _messages(episode)
        if message.get("end_ms", 0) <= timestamp
    ]


def _after(
    episode: dict[str, Any],
    timestamp: int,
) -> list[dict[str, Any]]:
    return [
        message
        for message in _messages(episode)
        if message.get("start_ms", 0) >= timestamp
    ]


def _event_bound_to_message(
    episode: dict[str, Any],
    event: dict[str, Any],
) -> bool:
    message = _message_map(episode).get(event.get("message_id"))
    timestamp = event.get("timestamp_ms")
    if message is None or not isinstance(timestamp, int):
        return False
    if not (
        message.get("start_ms", 0)
        <= timestamp
        <= message.get("end_ms", -1)
    ):
        return False
    event_participant = event.get("participant_id")
    if event_participant is not None and event_participant != message.get(
        "participant_id"
    ):
        return False
    return True


def _events_before(
    episode: dict[str, Any],
    name: str,
    timestamp: int,
) -> list[dict[str, Any]]:
    return [
        event
        for event in episode.get("events", [])
        if event.get("event") == name
        and event.get("timestamp_ms", 0) <= timestamp
        and _event_bound_to_message(episode, event)
    ]


def _event_before(
    name: str,
    predicate: Callable[[dict[str, Any]], bool] = lambda event: True,
) -> TriggerHandler:
    def handler(
        scenario: dict[str, Any],
        episode: dict[str, Any],
        event: dict[str, Any],
    ) -> bool:
        del scenario
        return any(
            predicate(candidate)
            for candidate in _events_before(
                episode,
                name,
                event["timestamp_ms"],
            )
        )

    return handler


def _after_training_initial_positions(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
) -> bool:
    prior = {
        message.get("participant_id")
        for message in _before(episode, event["timestamp_ms"])
        if message.get("speaker_type") == "ai"
        and message.get("move") == "propose_idea"
    }
    expected = {
        participant["agent_id"]
        for participant in scenario.get("ai_participants", [])
    }
    return bool(expected) and expected <= prior


def _before_future(move: str) -> TriggerHandler:
    def handler(
        scenario: dict[str, Any],
        episode: dict[str, Any],
        event: dict[str, Any],
    ) -> bool:
        del scenario
        return any(
            message.get("speaker_type") == "user"
            and message.get("move") == move
            for message in _after(episode, event["timestamp_ms"])
        )

    return handler


def _checkpoint(percentage: int) -> TriggerHandler:
    def handler(
        scenario: dict[str, Any],
        episode: dict[str, Any],
        event: dict[str, Any],
    ) -> bool:
        duration_ms = scenario["duration_seconds"] * 1000
        tolerance = duration_ms * 0.05
        message_by_id = _message_map(episode)
        return any(
            int(candidate.get("checkpoint_percent", -1)) == percentage
            and abs(
                candidate["timestamp_ms"]
                - duration_ms * percentage / 100
            )
            <= tolerance
            and candidate["timestamp_ms"] <= event["timestamp_ms"]
            and _event_bound_to_message(episode, candidate)
            and message_by_id[candidate["message_id"]].get("speaker_type")
            == "ai"
            and message_by_id[candidate["message_id"]].get("move")
            == "time_check"
            for candidate in episode.get("events", [])
            if candidate.get("event") == "TIME_CHECKPOINT_REACHED"
        )

    return handler


def _decision_criteria_incomplete(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return not _events_before(
        episode,
        "CRITERIA_RECORDED",
        event["timestamp_ms"],
    )


def _three_options_available(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del target_participant_id
    expected = set(
        scenario.get("shared_context", {}).get("options", [])
    )
    return any(
        expected <= set(candidate.get("options", []))
        for candidate in _events_before(
            episode,
            "OPTIONS_PRESENTED",
            event["timestamp_ms"],
        )
    )


def _risk_requires_reassessment(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    timestamp = event["timestamp_ms"]
    return bool(
        _events_before(
            episode,
            "PRIVATE_CONCERN_REVEALED",
            timestamp,
        )
    ) and not _events_before(
        episode,
        "DECISION_REVISION_RECORDED",
        timestamp,
    )


def _security_open(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return any(
        candidate.get("status") == "open"
        for candidate in _events_before(
            episode,
            "SECURITY_CONCERN_STATUS",
            event["timestamp_ms"],
        )
    )


def _risk_response(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario
    return bool(
        _events_before(
            episode,
            "PRIVATE_CONCERN_REVEALED",
            event["timestamp_ms"],
        )
    ) and any(
        message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
        for message in _after(episode, event["timestamp_ms"])
    )


def _solution_open(
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


def _hybrid_possible(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return any(
        "ハイブリッド" in candidate.get("candidate_modes", [])
        for candidate in _events_before(
            episode,
            "CONSTRAINT_COLLISION_RECORDED",
            event["timestamp_ms"],
        )
    )


def _regional_open(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return any(
        candidate.get("status") == "open"
        for candidate in _events_before(
            episode,
            "REGIONAL_ACCESS_CONCERN_STATUS",
            event["timestamp_ms"],
        )
    )


def _decision_requires_revision(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    timestamp = event["timestamp_ms"]
    return bool(
        _events_before(
            episode,
            "PRELIMINARY_DECISION_RECORDED",
            timestamp,
        )
    ) and bool(
        _events_before(
            episode,
            "PRIVATE_CONCERN_REVEALED",
            timestamp,
        )
    ) and not _events_before(
        episode,
        "DECISION_REVISION_RECORDED",
        timestamp,
    )


def _implementation_required(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario
    return not _events_before(
        episode,
        "IMPLEMENTATION_CONDITION_RECORDED",
        event["timestamp_ms"],
    ) and any(
        message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
        and message.get("move") == "confirm_consensus"
        for message in _after(episode, event["timestamp_ms"])
    )


def _unresolved(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    return any(
        candidate.get("items")
        for candidate in _events_before(
            episode,
            "UNRESOLVED_ITEMS_RECORDED",
            event["timestamp_ms"],
        )
    )


def _summary_required(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    del scenario, target_participant_id
    timestamp = event["timestamp_ms"]
    return bool(
        _events_before(
            episode,
            "FINAL_DECISION_RECORDED",
            timestamp,
        )
    ) and not _events_before(
        episode,
        "SUMMARY_RECORDED",
        timestamp,
    )


TRIGGER_HANDLERS: dict[str, TriggerHandler] = {
    "after_success_requirements": _event_before(
        "SUCCESS_REQUIREMENTS_PRESENTED",
        lambda event: len(event.get("requirements", [])) >= 3,
    ),
    "after_three_options_present": _event_before(
        "OPTIONS_PRESENTED",
        lambda event: len(event.get("options", [])) >= 3,
    ),
    "after_late_risk_reveal": _event_before(
        "PRIVATE_CONCERN_REVEALED",
        lambda event: bool(event.get("late_risk")),
    ),
    "after_security_question": _event_before(
        "SECURITY_CONCERN_STATUS",
        lambda event: event.get("status") == "open",
    ),
    "after_constraint_collision": _event_before(
        "CONSTRAINT_COLLISION_RECORDED",
        lambda event: len(event.get("constraints", [])) >= 2,
    ),
    "after_training_initial_positions": _after_training_initial_positions,
    "before_training_final_alignment": _before_future(
        "confirm_consensus"
    ),
    "after_training_criteria_defined": _event_before(
        "CRITERIA_RECORDED"
    ),
    "before_training_consensus_confirmation": _before_future(
        "confirm_consensus"
    ),
    "at_40_percent_time_checkpoint": _checkpoint(40),
    "at_75_percent_time_checkpoint": _checkpoint(75),
}

CONTEXT_HANDLERS: dict[str, ContextHandler] = {
    "decision_criteria_incomplete": _decision_criteria_incomplete,
    "training_three_options_available": _three_options_available,
    "risk_requires_reassessment": _risk_requires_reassessment,
    "security_concern_open": _security_open,
    "risk_requires_response": _risk_response,
    "solution_space_open": _solution_open,
    "hybrid_solution_possible": _hybrid_possible,
    "regional_access_concern_present": _regional_open,
    "decision_requires_revision": _decision_requires_revision,
    "implementation_condition_required": _implementation_required,
    "unresolved_items_visible": _unresolved,
    "summary_required": _summary_required,
}
