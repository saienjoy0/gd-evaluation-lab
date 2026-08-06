"""System-quality prohibitions for time-boxed decision scenarios."""
from __future__ import annotations

from typing import Any


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


def _valid_late_risk_events(episode: dict[str, Any]) -> list[dict[str, Any]]:
    messages = {
        message["message_id"]: message
        for message in episode.get("messages", [])
    }
    valid: list[dict[str, Any]] = []
    for event in episode.get("events", []):
        if event.get("event") != "PRIVATE_CONCERN_REVEALED":
            continue
        if not event.get("late_risk"):
            continue
        message = messages.get(event.get("message_id"))
        timestamp = event.get("timestamp_ms")
        participant_id = event.get("participant_id")
        if message is None or not isinstance(timestamp, int):
            continue
        if message.get("speaker_type") != "ai":
            continue
        if not participant_id or message.get("participant_id") != participant_id:
            continue
        if not (
            message.get("start_ms", 0)
            <= timestamp
            <= message.get("end_ms", -1)
        ):
            continue
        valid.append(event)
    return valid


def finalize_before_risk_reveal(
    episode: dict[str, Any],
    target_participant_id: str,
) -> dict[str, Any]:
    del target_participant_id
    risks = _valid_late_risk_events(episode)
    cutoff = min(
        (event["timestamp_ms"] for event in risks),
        default=float("inf"),
    )
    offenders = [
        message
        for message in _messages(episode)
        if message.get("speaker_type") == "ai"
        and message.get("move")
        in {"propose_decision", "confirm_consensus", "summarize"}
        and message.get("start_ms", 0) < cutoff
    ]
    return {
        "failed": bool(offenders),
        "message_ids": [message["message_id"] for message in offenders],
        "event_ids": [],
        "pass_detail": "AIは遅延リスク開示前に結論を確定していない。",
    }


def skip_summary(
    episode: dict[str, Any],
    target_participant_id: str,
) -> dict[str, Any]:
    summaries = [
        message
        for message in _messages(episode)
        if message.get("speaker_type") == "user"
        and message.get("participant_id") == target_participant_id
        and message.get("phase") == "summary"
        and message.get("move") == "summarize"
    ]
    closes = [
        event
        for event in episode.get("events", [])
        if event.get("event") == "SESSION_CLOSED"
    ]
    early = bool(
        closes
        and (
            not summaries
            or min(event["timestamp_ms"] for event in closes)
            < min(message["end_ms"] for message in summaries)
        )
    )
    return {
        "failed": not summaries or early,
        "message_ids": [message["message_id"] for message in summaries],
        "event_ids": [event["event_id"] for event in closes if early],
        "pass_detail": "候補者要約の後にセッションが終了した。",
    }
