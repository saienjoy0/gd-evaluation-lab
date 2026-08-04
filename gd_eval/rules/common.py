"""Pure deterministic rule handlers shared across exercises."""
from __future__ import annotations

from typing import Any, Callable

RuleHandler = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(episode.get("messages", []), key=lambda item: (item["start_ms"], item["message_id"]))


def _message_map(episode: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {message["message_id"]: message for message in episode.get("messages", [])}


def _target_id(episode: dict[str, Any], params: dict[str, Any]) -> str:
    explicit = params.get("target_participant_id")
    if explicit:
        return explicit
    users = [
        participant["participant_id"]
        for participant in episode.get("participants", [])
        if participant.get("speaker_type") == "user"
    ]
    if len(users) != 1:
        raise ValueError("TARGET_PARTICIPANT_AMBIGUOUS")
    return users[0]


def _jp_count(value: int) -> str:
    return {1: "一つ", 2: "二つ", 3: "三つ", 4: "四つ", 5: "五つ"}.get(value, str(value))


def user_message_before_action(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    target_id = _target_id(episode, params)
    messages = _messages(episode)
    user_messages = [
        message
        for message in messages
        if message.get("speaker_type") == "user"
        and message.get("participant_id") == target_id
    ]
    actions = set(params.get("actions", []))
    minimum = int(params.get("minimum_user_messages", 1))
    preemptions = [
        message
        for message in messages
        if message.get("speaker_type") == "ai"
        and message.get("move") in actions
        and sum(
            user.get("end_ms", 0) <= message.get("start_ms", 0)
            for user in user_messages
        )
        < minimum
    ]
    evidence = [
        message["message_id"]
        for message in user_messages
        if message.get("phase") == "problem_definition"
        and message.get("move") in {"clarify_goal", "define_scope", "define_criteria"}
    ]
    return {
        "ok": not preemptions,
        "evidence_message_ids": evidence if not preemptions else [m["message_id"] for m in preemptions],
        "evidence_event_ids": [],
        "detail": "AIが対象・基準を先に確定せず、利用者が先に定義した。",
    }


def resolved_context_keys(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    keys = set(params.get("keys", []))
    events = [
        event
        for event in episode.get("events", [])
        if event.get("event") == "CONTEXT_RESOLVED" and event.get("key") in keys
    ]
    resolved = {event.get("key") for event in events}
    minimum = int(params.get("minimum_resolved", len(keys)))
    return {
        "ok": len(resolved) >= minimum,
        "evidence_message_ids": [event["message_id"] for event in events if event.get("message_id")],
        "evidence_event_ids": [event["event_id"] for event in events],
        "detail": f"{_jp_count(len(resolved))}の文脈キーが解消された。",
    }


def candidate_move_types(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    target_id = _target_id(episode, params)
    allowed = set(params.get("moves", []))
    messages = [
        message
        for message in _messages(episode)
        if message.get("speaker_type") == "user"
        and message.get("participant_id") == target_id
        and message.get("move") in allowed
    ]
    distinct = {message.get("move") for message in messages}
    minimum = int(params.get("minimum_distinct_moves", 1))
    return {
        "ok": len(distinct) >= minimum,
        "evidence_message_ids": [message["message_id"] for message in messages],
        "evidence_event_ids": [],
        "detail": f"利用者が課題設定に必要な{len(distinct)}種類のmoveを実行した。",
    }


def private_concern_triggered_release(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    allowed = set(params.get("allowed_triggers", []))
    messages = _message_map(episode)
    concerns = [
        event
        for event in episode.get("events", [])
        if event.get("event") == "PRIVATE_CONCERN_REVEALED"
    ]
    valid = bool(concerns) and all(
        event.get("trigger_move") in allowed
        and event.get("message_id") in messages
        and messages[event["message_id"]].get("speaker_type") == "ai"
        for event in concerns
    )
    return {
        "ok": valid,
        "evidence_message_ids": [event["message_id"] for event in concerns if event.get("message_id")],
        "evidence_event_ids": [event["event_id"] for event in concerns],
        "detail": "非公開懸念は質問・比較後に開示された。",
    }


def summary_contains_fields(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    expected = set(params.get("fields", []))
    events = [
        event
        for event in episode.get("events", [])
        if event.get("event") == "SUMMARY_FIELDS_RECORDED"
    ]
    fields = {field for event in events for field in event.get("fields", [])}
    if expected == {"success_metric", "pilot_condition"}:
        detail = "要約に成功指標と実証見直し条件が含まれる。"
    else:
        detail = "要約に必要な項目が含まれる。"
    return {
        "ok": expected <= fields,
        "evidence_message_ids": [event["message_id"] for event in events if event.get("message_id")],
        "evidence_event_ids": [event["event_id"] for event in events],
        "detail": detail,
    }
