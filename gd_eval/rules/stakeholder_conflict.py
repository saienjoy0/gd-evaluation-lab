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


def _expected_ai_ids(scenario: dict[str, Any]) -> set[str]:
    return {
        participant["agent_id"]
        for participant in scenario.get("ai_participants", [])
    }


def _expected_position_ids(scenario: dict[str, Any]) -> set[str]:
    return {
        participant["agent_id"].rsplit("_", 1)[-1]
        for participant in scenario.get("ai_participants", [])
    }


def positions_and_challenge_before_phase(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    expected_ai_ids = _expected_ai_ids(scenario)
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
        actor = message.get("participant_id")
        if (
            message.get("speaker_type") == "ai"
            and actor in expected_ai_ids
            and message.get("move") in position_moves
            and actor not in position_actors
        ):
            positions.append(message)
            position_actors.add(actor)
    required_move = params.get("required_move", "challenge")
    challenges = [
        message
        for message in prior
        if message.get("speaker_type") == "ai"
        and message.get("participant_id") in expected_ai_ids
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
    expected_ai_ids = _expected_ai_ids(scenario)
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
    for concern in episode.get("events", []):
        if concern.get("event") != "PRIVATE_CONCERN_REVEALED":
            continue
        source = messages.get(concern.get("message_id"))
        if (
            source is None
            or source.get("speaker_type") != "ai"
            or source.get("participant_id") not in expected_ai_ids
            or source.get("participant_id") != concern.get("participant_id")
        ):
            continue
        linked: list[str] = []
        for message_id in concern.get("candidate_response_message_ids", []):
            response = messages.get(message_id)
            if (
                response is not None
                and response.get("speaker_type") == "user"
                and response.get("participant_id") == target_id
                and response.get("start_ms", 0)
                >= concern.get("timestamp_ms", 0)
                and response.get("move") in allowed_moves
            ):
                linked.append(message_id)
        if linked:
            evidence_event_ids.append(concern["event_id"])
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
    expected_position_ids = _expected_position_ids(scenario)
    target_id = _target_id(episode, params)
    messages = {
        message["message_id"]: message for message in episode.get("messages", [])
    }
    valid_events: list[dict[str, Any]] = []
    position_ids: set[str] = set()
    for integration in episode.get("events", []):
        if integration.get("event") != "POSITIONS_INTEGRATED":
            continue
        linked_message = messages.get(integration.get("message_id"))
        integrated = set(integration.get("position_ids", []))
        if (
            linked_message is not None
            and linked_message.get("speaker_type") == "user"
            and linked_message.get("participant_id") == target_id
            and integrated
            and integrated <= expected_position_ids
        ):
            valid_events.append(integration)
            position_ids.update(integrated)
    minimum = int(params.get("minimum_positions", 2))
    return {
        "ok": len(position_ids) >= minimum,
        "evidence_message_ids": [
            item["message_id"] for item in valid_events if item.get("message_id")
        ],
        "evidence_event_ids": [item["event_id"] for item in valid_events],
        "detail": f"{len(position_ids)}立場を統合する案が記録された。",
    }


def decision_contains_fields(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    del scenario
    expected = set(params.get("fields", []))
    valid_events = [
        item
        for item in episode.get("events", [])
        if item.get("event") == "DECISION_ALLOCATION_RECORDED"
        and expected <= set(item.get("fields", []))
    ]
    return {
        "ok": bool(valid_events),
        "evidence_message_ids": [
            item["message_id"] for item in valid_events if item.get("message_id")
        ],
        "evidence_event_ids": [item["event_id"] for item in valid_events],
        "detail": "結論に判断基準、配分、未採用施策への緩和策が含まれる。",
    }


def challenge_after_first_candidate_proposal(
    scenario: dict[str, Any], episode: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    expected_ai_ids = _expected_ai_ids(scenario)
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
        and message.get("participant_id") in expected_ai_ids
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
