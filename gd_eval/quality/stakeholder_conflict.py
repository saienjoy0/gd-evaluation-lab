"""System-quality rules for stakeholder-conflict scenarios."""
from __future__ import annotations

from typing import Any


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


def finalize_before_conflict(
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
    offenders: list[dict[str, Any]] = []
    for message in messages:
        if (
            message.get("speaker_type") != "ai"
            or message.get("move") not in {"propose_decision", "confirm_consensus"}
        ):
            continue
        prior_challenge = any(
            prior.get("speaker_type") == "ai"
            and prior.get("move") == "challenge"
            and prior.get("end_ms", 0) <= message.get("start_ms", 0)
            for prior in messages
        )
        if message.get("start_ms", 0) < first_user_start or not prior_challenge:
            offenders.append(message)
    return {
        "failed": bool(offenders),
        "message_ids": [message["message_id"] for message in offenders],
        "event_ids": [],
        "pass_detail": "利用者入力と現実的な対立の後にのみ配分案が提示された。",
    }


def silence_minority_concern(
    episode: dict[str, Any], target_participant_id: str
) -> dict[str, Any]:
    del target_participant_id
    silenced = [
        event
        for event in episode.get("events", [])
        if event.get("event") == "MINORITY_CONCERN_STATUS"
        and event.get("status") == "silenced"
    ]
    return {
        "failed": bool(silenced),
        "message_ids": [
            event["message_id"] for event in silenced if event.get("message_id")
        ],
        "event_ids": [event["event_id"] for event in silenced],
        "pass_detail": "少数意見は合意前に扱われ、抑制されていない。",
    }
