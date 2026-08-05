"""Deterministic rules for time-boxed decision scenarios."""
from __future__ import annotations

from typing import Any


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


def _message_map(episode: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        message["message_id"]: message
        for message in episode.get("messages", [])
    }


def _target(episode: dict[str, Any], params: dict[str, Any]) -> str:
    explicit = params.get("target_participant_id")
    if explicit:
        return str(explicit)
    users = [
        participant["participant_id"]
        for participant in episode.get("participants", [])
        if participant.get("speaker_type") == "user"
    ]
    if len(users) != 1:
        raise ValueError("TARGET_PARTICIPANT_AMBIGUOUS")
    return users[0]


def _events(episode: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [
        event
        for event in episode.get("events", [])
        if event.get("event") == name
    ]


def _event_bound_to_message(
    event: dict[str, Any],
    message: dict[str, Any] | None,
    *,
    speaker_type: str | None = None,
    participant_id: str | None = None,
    move: str | None = None,
) -> bool:
    if message is None:
        return False
    timestamp = event.get("timestamp_ms")
    if not isinstance(timestamp, int):
        return False
    if not (
        message.get("start_ms", 0)
        <= timestamp
        <= message.get("end_ms", -1)
    ):
        return False
    if speaker_type is not None and message.get("speaker_type") != speaker_type:
        return False
    if participant_id is not None and message.get("participant_id") != participant_id:
        return False
    if move is not None and message.get("move") != move:
        return False
    event_participant = event.get("participant_id")
    if event_participant is not None and event_participant != message.get("participant_id"):
        return False
    return True


def _valid_checkpoint_events(
    episode: dict[str, Any],
) -> list[dict[str, Any]]:
    messages = _message_map(episode)
    return sorted(
        [
            event
            for event in _events(episode, "TIME_CHECKPOINT_REACHED")
            if _event_bound_to_message(
                event,
                messages.get(event.get("message_id")),
                speaker_type="ai",
                move="time_check",
            )
        ],
        key=lambda item: (item["timestamp_ms"], item["event_id"]),
    )


def time_checkpoints_followed_by_candidate_turn(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    duration_ms = int(scenario["duration_seconds"]) * 1000
    target = _target(episode, params)
    messages = _messages(episode)
    message_by_id = _message_map(episode)
    checkpoints = [int(value) for value in params.get("checkpoints_percent", [])]
    tolerance = (
        duration_ms
        * float(params.get("tolerance_percent_of_duration", 5))
        / 100
    )
    maximum_delay = int(params.get("maximum_response_delay_ms", 90000))
    minimum = int(params.get("minimum_candidate_turns_after_each", 1))
    checkpoint_events = _valid_checkpoint_events(episode)

    evidence_messages: list[str] = []
    evidence_events: list[str] = []
    ok = True

    for index, percentage in enumerate(checkpoints):
        candidates = [
            event
            for event in checkpoint_events
            if int(event.get("checkpoint_percent", -1)) == percentage
        ]
        if not candidates:
            ok = False
            continue

        event = min(candidates, key=lambda item: item["timestamp_ms"])
        linked = message_by_id[event["message_id"]]
        expected = duration_ms * percentage / 100
        if abs(event["timestamp_ms"] - expected) > tolerance:
            ok = False
            continue

        response_window_start = max(event["timestamp_ms"], linked["end_ms"])
        response_window_end = response_window_start + maximum_delay
        if index + 1 < len(checkpoints):
            next_checkpoint = duration_ms * checkpoints[index + 1] / 100
            response_window_end = min(
                response_window_end,
                next_checkpoint + tolerance,
            )

        responses = [
            message
            for message in messages
            if message.get("speaker_type") == "user"
            and message.get("participant_id") == target
            and response_window_start <= message.get("start_ms", 0)
            and message.get("start_ms", 0) <= response_window_end
        ]
        if len(responses) < minimum:
            ok = False
            continue

        evidence_messages.extend(
            [
                linked["message_id"],
                *[
                    message["message_id"]
                    for message in responses[:minimum]
                ],
            ]
        )
        evidence_events.append(event["event_id"])

    return {
        "ok": ok,
        "evidence_message_ids": list(dict.fromkeys(evidence_messages)),
        "evidence_event_ids": evidence_events,
        "detail": (
            f"{len(evidence_events)}件の時間通知後に"
            "候補者ターンが確保された。"
        ),
    }


def private_concern_revealed_before_phase(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    before_phase = params.get("before_phase", "decision")
    phase_starts = [
        message["start_ms"]
        for message in _messages(episode)
        if message.get("phase") == before_phase
    ]
    cutoff = min(phase_starts) if phase_starts else float("inf")
    target = _target(episode, params)
    participants = {
        participant["agent_id"]: participant
        for participant in scenario.get("ai_participants", [])
    }
    messages = _messages(episode)
    message_by_id = _message_map(episode)
    allowed_trigger_moves = set(params.get("allowed_trigger_moves", []))

    valid: list[dict[str, Any]] = []
    for event in _events(episode, "PRIVATE_CONCERN_REVEALED"):
        if params.get("require_late_risk", False) and not event.get("late_risk"):
            continue

        message = message_by_id.get(event.get("message_id"))
        participant = participants.get(event.get("participant_id"))
        if participant is None or not _event_bound_to_message(
            event,
            message,
            speaker_type="ai",
            participant_id=event.get("participant_id"),
        ):
            continue
        if event.get("concern") != participant.get("private_concern"):
            continue
        if message["end_ms"] > cutoff:
            continue

        trigger_move = event.get("trigger_move")
        if allowed_trigger_moves:
            if trigger_move not in allowed_trigger_moves:
                continue
            triggered = any(
                prior.get("speaker_type") == "user"
                and prior.get("participant_id") == target
                and prior.get("move") == trigger_move
                and prior.get("end_ms", 0) <= message.get("start_ms", 0)
                for prior in messages
            )
            if not triggered:
                continue

        valid.append(event)

    minimum = int(params.get("minimum_concerns", 1))
    unique_concerns = {
        (event.get("participant_id"), event.get("concern"))
        for event in valid
    }
    return {
        "ok": len(unique_concerns) >= minimum,
        "evidence_message_ids": [
            event["message_id"]
            for event in valid
        ],
        "evidence_event_ids": [
            event["event_id"]
            for event in valid
        ],
        "detail": (
            f"決定前に{len(unique_concerns)}件の遅延リスクが"
            "正規の候補者行動後に開示された。"
        ),
    }


def candidate_prioritizes_after_time_check(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    del scenario
    target = _target(episode, params)
    message_by_id = _message_map(episode)
    checkpoints = _valid_checkpoint_events(episode)
    minimum_items = int(params.get("minimum_ordered_items", 2))
    by_checkpoint: dict[str, dict[str, Any]] = {}

    for event in sorted(
        _events(episode, "PRIORITY_UPDATE_RECORDED"),
        key=lambda item: (item["timestamp_ms"], item["event_id"]),
    ):
        message = message_by_id.get(event.get("message_id"))
        if not _event_bound_to_message(
            event,
            message,
            speaker_type="user",
            participant_id=target,
            move="prioritize",
        ):
            continue

        prior_checkpoints = [
            checkpoint
            for checkpoint in checkpoints
            if checkpoint["timestamp_ms"] <= message["start_ms"]
        ]
        if not prior_checkpoints:
            continue
        checkpoint = max(
            prior_checkpoints,
            key=lambda item: item["timestamp_ms"],
        )
        following = [
            candidate["timestamp_ms"]
            for candidate in checkpoints
            if candidate["timestamp_ms"] > checkpoint["timestamp_ms"]
        ]
        if following and message["start_ms"] >= min(following):
            continue
        if len(event.get("ordered_items", [])) < minimum_items:
            continue
        by_checkpoint.setdefault(checkpoint["event_id"], event)

    valid = list(by_checkpoint.values())
    minimum_occurrences = int(params.get("minimum_occurrences", 1))
    return {
        "ok": len(valid) >= minimum_occurrences,
        "evidence_message_ids": [
            event["message_id"]
            for event in valid
        ],
        "evidence_event_ids": [
            event["event_id"]
            for event in valid
        ],
        "detail": (
            f"時間通知後の優先順位更新を{len(valid)}件確認した。"
        ),
    }


def candidate_compares_and_revises(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    target = _target(episode, params)
    message_by_id = _message_map(episode)
    required_options = set(
        scenario.get("shared_context", {}).get("options", [])
    )

    comparisons: list[dict[str, Any]] = []
    for event in _events(episode, "OPTIONS_COMPARED"):
        message = message_by_id.get(event.get("message_id"))
        if not _event_bound_to_message(
            event,
            message,
            speaker_type="user",
            participant_id=target,
            move="compare_options",
        ):
            continue
        if not required_options <= set(event.get("options", [])):
            continue
        if len(event.get("options", [])) < int(
            params.get("minimum_options", 3)
        ):
            continue
        if len(event.get("criteria", [])) < int(
            params.get("minimum_criteria", 2)
        ):
            continue
        comparisons.append(event)

    risks = [
        event
        for event in _events(episode, "PRIVATE_CONCERN_REVEALED")
        if event.get("late_risk")
        and _event_bound_to_message(
            event,
            message_by_id.get(event.get("message_id")),
            speaker_type="ai",
            participant_id=event.get("participant_id"),
        )
    ]
    risk_by_id = {
        event["event_id"]: event
        for event in risks
    }

    revisions: list[dict[str, Any]] = []
    for event in _events(episode, "DECISION_REVISION_RECORDED"):
        before = message_by_id.get(event.get("before_message_id"))
        after = message_by_id.get(event.get("after_message_id"))
        risk = risk_by_id.get(event.get("risk_event_id"))
        if before is None or after is None or risk is None:
            continue
        if before.get("speaker_type") != "user":
            continue
        if before.get("participant_id") != target:
            continue
        if before.get("move") != "propose_decision":
            continue
        if before.get("end_ms", 0) > risk["timestamp_ms"]:
            continue
        if not _event_bound_to_message(
            event,
            after,
            speaker_type="user",
            participant_id=target,
        ):
            continue
        if after.get("move") not in {
            "integrate",
            "propose_decision",
        }:
            continue
        if after.get("start_ms", 0) < risk["timestamp_ms"]:
            continue
        if not event.get("changed_fields"):
            continue
        revisions.append(event)

    ok = bool(comparisons) and (
        bool(revisions)
        if params.get("requires_risk_response", False)
        else True
    )
    return {
        "ok": ok,
        "evidence_message_ids": [
            *[
                event["message_id"]
                for event in comparisons
            ],
            *[
                event["after_message_id"]
                for event in revisions
            ],
        ],
        "evidence_event_ids": [
            *[
                event["event_id"]
                for event in comparisons
            ],
            *[
                event["event_id"]
                for event in revisions
            ],
        ],
        "detail": "三案比較と遅延リスク後の案修正を確認した。",
    }


def candidate_summary_contains_fields(
    scenario: dict[str, Any],
    episode: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    del scenario
    target = _target(episode, params)
    message_by_id = _message_map(episode)
    expected = set(params.get("fields", []))

    field_events = [
        event
        for event in _events(episode, "SUMMARY_FIELDS_RECORDED")
        if _event_bound_to_message(
            event,
            message_by_id.get(event.get("message_id")),
            speaker_type="user",
            participant_id=target,
            move="summarize",
        )
        and message_by_id[event["message_id"]].get("phase") == "summary"
        and expected <= set(event.get("fields", []))
    ]
    summary_events = [
        event
        for event in _events(episode, "SUMMARY_RECORDED")
        if _event_bound_to_message(
            event,
            message_by_id.get(event.get("message_id")),
            speaker_type="user",
            participant_id=target,
            move="summarize",
        )
        and message_by_id[event["message_id"]].get("phase") == "summary"
        and all(event.get(field) for field in expected)
    ]

    valid_pairs = [
        (field_event, summary_event)
        for field_event in field_events
        for summary_event in summary_events
        if field_event["message_id"] == summary_event["message_id"]
    ]
    return {
        "ok": bool(valid_pairs),
        "evidence_message_ids": list(
            dict.fromkeys(
                field_event["message_id"]
                for field_event, _ in valid_pairs
            )
        ),
        "evidence_event_ids": list(
            dict.fromkeys(
                event["event_id"]
                for pair in valid_pairs
                for event in pair
            )
        ),
        "detail": "要約に必要な項目と値が含まれる。",
    }
