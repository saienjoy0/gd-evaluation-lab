"""Resolve evaluation opportunities from verified Episode evidence."""
from __future__ import annotations

from typing import Any, Callable

from .stakeholder_conflict import (
    CONTEXT_HANDLERS as STAKEHOLDER_CONTEXT_HANDLERS,
)
from .stakeholder_conflict import (
    TRIGGER_HANDLERS as STAKEHOLDER_TRIGGER_HANDLERS,
)
from .time_boxed_decision import CONTEXT_HANDLERS as TIME_CONTEXT_HANDLERS
from .time_boxed_decision import TRIGGER_HANDLERS as TIME_TRIGGER_HANDLERS


class OpportunityResolutionError(ValueError):
    pass


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


def _before(messages: list[dict[str, Any]], timestamp: int) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("end_ms", 0) <= timestamp]


def _after(messages: list[dict[str, Any]], timestamp: int) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("start_ms", 0) >= timestamp]


def _after_initial_positions(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    prior_ai = {
        message.get("participant_id")
        for message in _before(_messages(episode), event["timestamp_ms"])
        if message.get("speaker_type") == "ai"
    }
    expected = {
        participant["agent_id"] for participant in scenario.get("ai_participants", [])
    }
    return bool(expected) and expected <= prior_ai


def _after_goal_question(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "ai"
        and message.get("move") == "ask_question"
        and message.get("phase") == "problem_definition"
        for message in _before(_messages(episode), event["timestamp_ms"])
    )


def _before_idea_generation(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    starts = [
        message["start_ms"]
        for message in _messages(episode)
        if message.get("phase") == "idea_generation"
    ]
    return bool(starts) and event["timestamp_ms"] < min(starts)


def _after_two_options_present(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    prior = _before(_messages(episode), event["timestamp_ms"])
    return any(message.get("move") == "compare_options" for message in prior) or len(
        {
            message.get("participant_id")
            for message in prior
            if message.get("speaker_type") == "ai"
        }
    ) >= min(2, len(scenario.get("ai_participants", [])))


def _after_constraint_reveal(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        item.get("event") == "PRIVATE_CONCERN_REVEALED"
        and item.get("timestamp_ms", 0) <= event["timestamp_ms"]
        for item in episode.get("events", [])
    )


def _after_ai_question(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "ai"
        and message.get("move") == "ask_question"
        for message in _before(_messages(episode), event["timestamp_ms"])
    )


def _after_private_concern_reveal(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    return _after_constraint_reveal(scenario, episode, event)


def _after_initial_ideas(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("phase") == "idea_generation"
        for message in _before(_messages(episode), event["timestamp_ms"])
    )


def _after_tradeoff_identified(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("phase") == "option_comparison"
        and message.get("move") in {"compare_options", "challenge", "integrate"}
        for message in _before(_messages(episode), event["timestamp_ms"])
    )


def _after_position_conflict(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    prior = _before(_messages(episode), event["timestamp_ms"])
    return any(message.get("move") == "challenge" for message in prior) and len(
        {
            message.get("participant_id")
            for message in prior
            if message.get("speaker_type") == "ai"
        }
    ) >= 2


def _before_final_selection(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("speaker_type") == "user"
        and message.get("phase") == "decision"
        and message.get("move") in {"confirm_consensus", "propose_decision"}
        for message in _after(_messages(episode), event["timestamp_ms"])
    )


def _before_session_close(
    scenario: dict[str, Any], episode: dict[str, Any], event: dict[str, Any]
) -> bool:
    del scenario
    return any(
        message.get("phase") == "summary"
        for message in _after(_messages(episode), event["timestamp_ms"])
    )


_TRIGGER_HANDLERS: dict[
    str, Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], bool]
] = {
    "after_initial_positions": _after_initial_positions,
    "after_goal_question": _after_goal_question,
    "before_idea_generation": _before_idea_generation,
    "after_two_options_present": _after_two_options_present,
    "after_constraint_reveal": _after_constraint_reveal,
    "after_ai_question": _after_ai_question,
    "after_private_concern_reveal": _after_private_concern_reveal,
    "after_initial_ideas": _after_initial_ideas,
    "after_tradeoff_identified": _after_tradeoff_identified,
    "after_position_conflict": _after_position_conflict,
    "before_final_selection": _before_final_selection,
    "before_session_close": _before_session_close,
    **STAKEHOLDER_TRIGGER_HANDLERS,
    **TIME_TRIGGER_HANDLERS,
}


def _resolved_before(episode: dict[str, Any], key: str, timestamp: int) -> bool:
    return any(
        event.get("event") == "CONTEXT_RESOLVED"
        and event.get("key") == key
        and event.get("timestamp_ms", 0) <= timestamp
        for event in episode.get("events", [])
    )


def _context_satisfied(
    context: str,
    scenario: dict[str, Any],
    episode: dict[str, Any],
    event: dict[str, Any],
    target_participant_id: str,
) -> bool:
    timestamp = event["timestamp_ms"]
    prior = _before(_messages(episode), timestamp)
    future = _after(_messages(episode), timestamp)
    checks: dict[str, bool] = {
        "priority_target_undefined": not _resolved_before(
            episode, "priority_target", timestamp
        ),
        "success_metric_undefined": not _resolved_before(
            episode, "success_metric", timestamp
        ),
        "scope_boundaries_undefined": not _resolved_before(
            episode, "scope_boundaries", timestamp
        ),
        "two_options_available": any(
            message.get("move") == "compare_options" for message in prior
        )
        or len(
            {
                message.get("participant_id")
                for message in prior
                if message.get("speaker_type") == "ai"
            }
        )
        >= 2,
        "constraint_requires_tradeoff": any(
            item.get("event") == "PRIVATE_CONCERN_REVEALED"
            and item.get("timestamp_ms", 0) <= timestamp
            for item in episode.get("events", [])
        ),
        "ai_question_open": any(
            message.get("speaker_type") == "ai"
            and message.get("move") == "ask_question"
            for message in prior
        ),
        "concern_requires_response": any(
            item.get("event") == "PRIVATE_CONCERN_REVEALED"
            and item.get("timestamp_ms", 0) <= timestamp
            for item in episode.get("events", [])
        )
        and any(message.get("speaker_type") == "user" for message in future),
        "idea_space_open": any(
            message.get("phase") == "idea_generation"
            for message in prior + future
        ),
        "improvement_possible": any(
            message.get("phase") == "option_comparison"
            and message.get("move") in {"compare_options", "challenge", "integrate"}
            for message in prior
        ),
        "multiple_positions_active": len(
            {
                message.get("participant_id")
                for message in prior
                if message.get("speaker_type") == "ai"
            }
        )
        >= 2,
        "criteria_and_options_available": any(
            message.get("speaker_type") == "user"
            and message.get("move") == "define_criteria"
            for message in prior
        )
        and any(message.get("move") == "compare_options" for message in prior),
        "remaining_time_visible": timestamp
        < max(
            (message.get("end_ms", 0) for message in _messages(episode)),
            default=timestamp,
        ),
    }
    if context in checks:
        return checks[context]
    handler = TIME_CONTEXT_HANDLERS.get(context)
    if handler is None:
        handler = STAKEHOLDER_CONTEXT_HANDLERS.get(context)
    if handler is None:
        raise OpportunityResolutionError(
            f"UNIMPLEMENTED_OPPORTUNITY_CONTEXT: {context}"
        )
    return handler(scenario, episode, event, target_participant_id)


def resolve_opportunities(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    system_quality: dict[str, Any],
    target_participant_id: str,
    resolver_version: str,
) -> dict[str, Any]:
    messages = {
        message["message_id"]: message for message in episode.get("messages", [])
    }
    target_messages = {
        message_id
        for message_id, message in messages.items()
        if message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
    }
    offers: dict[str, list[dict[str, Any]]] = {}
    for event in episode.get("events", []):
        if event.get("event") == "OPPORTUNITY_OFFERED":
            offers.setdefault(event.get("opportunity_id"), []).append(event)

    failed_conditions = {
        result["rule_id"]
        for result in system_quality.get("rule_results", [])
        if result["outcome"] == "fail"
    }
    items: list[dict[str, Any]] = []
    for opportunity in scenario.get("evaluation_opportunities", []):
        opportunity_id = opportunity["opportunity_id"]
        events = sorted(
            offers.get(opportunity_id, []), key=lambda item: item["timestamp_ms"]
        )
        invalidated_by = [
            condition
            for condition in opportunity.get("invalidated_by", [])
            if condition in failed_conditions
        ]
        for event in events:
            if event.get("dimension") != opportunity["dimension"]:
                raise OpportunityResolutionError(
                    f"OPPORTUNITY_DIMENSION_MISMATCH: {opportunity_id}"
                )
            trigger = opportunity.get("trigger")
            handler = _TRIGGER_HANDLERS.get(trigger)
            if handler is None:
                raise OpportunityResolutionError(
                    f"UNIMPLEMENTED_OPPORTUNITY_TRIGGER: {trigger}"
                )
            if not handler(scenario, episode, event):
                raise OpportunityResolutionError(
                    f"OPPORTUNITY_TRIGGER_INVALID: {opportunity_id}"
                )
            if not all(
                _context_satisfied(
                    context, scenario, episode, event, target_participant_id
                )
                for context in opportunity.get("required_context", [])
            ):
                raise OpportunityResolutionError(
                    f"OPPORTUNITY_CONTEXT_INVALID: {opportunity_id}"
                )

        response_ids: list[str] = []
        for event in events:
            for message_id in event.get("candidate_response_message_ids", []):
                message = messages.get(message_id)
                if message_id not in target_messages:
                    raise OpportunityResolutionError(
                        f"EVIDENCE_OWNER_MISMATCH: {opportunity_id}:{message_id}"
                    )
                if message.get("phase") != opportunity.get("phase"):
                    raise OpportunityResolutionError(
                        f"OPPORTUNITY_PHASE_MISMATCH: {opportunity_id}:{message_id}"
                    )
                if message.get("start_ms", 0) < event.get("timestamp_ms", 0):
                    raise OpportunityResolutionError(
                        f"OPPORTUNITY_RESPONSE_BEFORE_TRIGGER: "
                        f"{opportunity_id}:{message_id}"
                    )
                if message_id not in response_ids:
                    response_ids.append(message_id)

        if invalidated_by:
            status = "invalid"
            response_status = "not_applicable"
            response_ids = []
            detail = "禁止条件により評価機会が無効化された。"
        elif events:
            status = "offered"
            response_status = "observed" if response_ids else "not_observed"
            detail = (
                "構造化イベントと利用者応答を確認した。"
                if response_ids
                else "評価機会は提供されたが利用者応答は観察されない。"
            )
        else:
            status = "not_offered"
            response_status = "not_applicable"
            detail = "対応する評価機会イベントが存在しない。"

        items.append(
            {
                "opportunity_id": opportunity_id,
                "dimension": opportunity["dimension"],
                "status": status,
                "trigger_event_ids": [event["event_id"] for event in events],
                "candidate_response_message_ids": response_ids,
                "invalidated_by": invalidated_by,
                "response_status": response_status,
                "detail": detail,
            }
        )

    summary = {
        "offered": sum(item["status"] == "offered" for item in items),
        "not_offered": sum(item["status"] == "not_offered" for item in items),
        "invalid": sum(item["status"] == "invalid" for item in items),
        "with_candidate_response": sum(
            item["response_status"] == "observed" for item in items
        ),
    }
    return {
        "contract_version": "0.1",
        "resolution_id": f"or-{episode['session_id']}",
        "session_id": episode["session_id"],
        "scenario_id": episode["scenario_id"],
        "scenario_version": episode["scenario_version"],
        "target_participant_id": target_participant_id,
        "resolver_version": resolver_version,
        "items": items,
        "summary": summary,
    }
