"""Deterministic rules for stakeholder-conflict assessment scenarios."""
from __future__ import annotations

from typing import Any


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        episode.get("messages", []),
        key=lambda item: (item["start_ms"], item["message_id"]),
    )


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


def positions_and_challenge_before_phase(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    before_phase = params.get("before_phase", "decision")
    messages = _messages(episode)
    phase_starts = [
        message["start_ms"]
        for message in messages
        if message.get("phase") == before_phase
    ]
    cutoff = min(phase_starts) if phase_starts else float("inf")
    prior = [message for message in messages if message.get("end_ms", 0) <= cutoff]
    position_moves = set(
        params.get("position_moves", ["propose_idea", "clarify_goal"])
    )
    positions: list[dict[str, Any]] = []
    position_actors: set[str] = set()
    for message in prior:
        if (
            message.get("speaker_type") == "ai"
            and message.get("move") in position_moves
            and message.get("participant_id") not in position_actors
        ):
            positions.append(message)
            position_actors.add(message["participant_id"])
    required_move = params.get("required_move", "challenge")
    challenges = [
        message
        for message in prior
        if message.get("speaker_type") == "ai"
        and message.get("move") == required_move
    ]
    minimum_positions = int(params.get("minimum_positions", 1))
    return {
        "ok": len(position_actors) >= minimum_positions and bool(challenges),
        "evidence_message_ids": [
            message["message_id"] for message in positions + challenges
        ],
        "evidence_event_ids": [],
        "detail": (
            f"{len(position_actors)}立場と{len(challenges)}件の反対意見が"
            "決定前に提示された。"
        ),
    }


def candidate_response_to_concern(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    target_id = _target_id(episode, params)
    messages = {
        message["message_id"]: message for message in episode.get("messages", [])
    }
    allowed_moves = set(
        params.get(
            "response_moves",
            ["respond_to_question", "integrate", "compare_options", "propose_idea"],
        )
    )
    evidence_message_ids: list[str] = []
    evidence_event_ids: list[str] = []
    for event in episode.get("events", []):
        if event.get("event") != "PRIVATE_CONCERN_REVEALED":
            continue
        linked: list[str] = []
        for message_id in event.get("candidate_response_message_ids", []):
            message = messages.get(message_id)
            if (
                message is not None
                and message.get("speaker_type") == "user"
                and message.get("participant_id") == target_id
                and message.get("start_ms", 0) >= event.get("timestamp_ms", 0)
                and message.get("move") in allowed_moves
            ):
                linked.append(message_id)
        if linked:
            evidence_event_ids.append(event["event_id"])
            for message_id in linked:
                if message_id not in evidence_message_ids:
                    evidence_message_ids.append(message_id)
    minimum = int(params.get("minimum_responses", 1))
    return {
        "ok": len(evidence_message_ids) >= minimum,
        "evidence_message_ids": evidence_message_ids,
        "evidence_event_ids": evidence_event_ids,
        "detail": f"{len(evidence_message_ids)}件の懸念へ候補者が直接応答した。",
    }


def candidate_integrates_positions(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    target_id = _target_id(episode, params)
    messages = {
        message["message_id"]: message for message in episode.get("messages", [])
    }
    valid_events: list[dict[str, Any]] = []
    position_ids: set[str] = set()
    for event in episode.get("events", []):
        if event.get("event") != "POSITIONS_INTEGRATED":
            continue
        message = messages.get(event.get("message_id"))
        if (
            message is not None
            and message.get("speaker_type") == "user"
            and message.get("participant_id") == target_id
        ):
            valid_events.append(event)
            position_ids.update(event.get("position_ids", []))
    minimum = int(params.get("minimum_positions", 2))
    return {
        "ok": len(position_ids) >= minimum,
        "evidence_message_ids": [
            event["message_id"] for event in valid_events if event.get("message_id")
        ],
        "evidence_event_ids": [event["event_id"] for event in valid_events],
        "detail": f"{len(position_ids)}立場を統合する案が記録された。",
    }


def decision_contains_fields(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    expected = set(params.get("fields", []))
    events = [
        event
        for event in episode.get("events", [])
        if event.get("event") == "DECISION_ALLOCATION_RECORDED"
    ]
    fields = {field for event in events for field in event.get("fields", [])}
    return {
        "ok": expected <= fields,
        "evidence_message_ids": [
            event["message_id"] for event in events if event.get("message_id")
        ],
        "evidence_event_ids": [event["event_id"] for event in events],
        "detail": "結論に判断基準、配分、未採用施策への緩和策が含まれる。",
    }


def challenge_after_first_candidate_proposal(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    target_id = _target_id(episode, params)
    messages = _messages(episode)
    first_proposal = next(
        (
            message
            for message in messages
            if message.get("speaker_type") == "user"
            and message.get("participant_id") == target_id
            and message.get("move") == "propose_idea"
        ),
        None,
    )
    if first_proposal is None:
        return {
            "ok": False,
            "evidence_message_ids": [],
            "evidence_event_ids": [],
            "detail": "候補者の最初の案が存在しない。",
        }
    decision_starts = [
        message["start_ms"]
        for message in messages
        if message.get("phase") == "decision"
    ]
    cutoff = min(decision_starts) if decision_starts else float("inf")
    challenges = [
        message
        for message in messages
        if message.get("speaker_type") == "ai"
        and message.get("move") == "challenge"
        and message.get("start_ms", 0) >= first_proposal.get("end_ms", 0)
        and message.get("start_ms", 0) < cutoff
    ]
    minimum = int(params.get("minimum_challenges", 1))
    return {
        "ok": len(challenges) >= minimum,
        "evidence_message_ids": [first_proposal["message_id"]]
        + [message["message_id"] for message in challenges],
        "evidence_event_ids": [],
        "detail": (
            f"候補者の最初の案の後に{len(challenges)}件のchallengeが提示された。"
        ),
    }


def numeric_constraint_preserved(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    event_name = params.get("event")
    checks = params.get("checks", [])
    matching = [
        event
        for event in episode.get("events", [])
        if event.get("event") == event_name
    ]
    valid: list[dict[str, Any]] = []
    for event in matching:
        ok = True
        for check in checks:
            value = event.get(check["field"])
            if "equals" in check and value != check["equals"]:
                ok = False
            if "maximum" in check and (
                value is None or value > check["maximum"]
            ):
                ok = False
            if "minimum" in check and (
                value is None or value < check["minimum"]
            ):
                ok = False
        if ok:
            valid.append(event)
    return {
        "ok": bool(valid),
        "evidence_message_ids": [
            event["message_id"] for event in valid if event.get("message_id")
        ],
        "evidence_event_ids": [event["event_id"] for event in valid],
        "detail": "配分総額と重点施策数がシナリオ制約内にある。",
    }
