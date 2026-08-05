"""System-quality prohibitions for time-boxed decision scenarios."""
from __future__ import annotations
from typing import Any


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(episode.get("messages", []), key=lambda x:(x["start_ms"],x["message_id"]))


def finalize_before_risk_reveal(episode: dict[str, Any], target_participant_id: str) -> dict[str, Any]:
    del target_participant_id
    risks=[e for e in episode.get("events",[]) if e.get("event")=="PRIVATE_CONCERN_REVEALED" and e.get("late_risk")]
    cutoff=min((e["timestamp_ms"] for e in risks),default=float("inf"))
    offenders=[m for m in _messages(episode) if m.get("speaker_type")=="ai" and m.get("move") in {"propose_decision","confirm_consensus","summarize"} and m.get("start_ms",0)<cutoff]
    return {"failed":bool(offenders),"message_ids":[m["message_id"] for m in offenders],"event_ids":[],"pass_detail":"AIは遅延リスク開示前に結論を確定していない。"}


def skip_summary(episode: dict[str, Any], target_participant_id: str) -> dict[str, Any]:
    summaries=[m for m in _messages(episode) if m.get("speaker_type")=="user" and m.get("participant_id")==target_participant_id and m.get("phase")=="summary" and m.get("move")=="summarize"]
    closes=[e for e in episode.get("events",[]) if e.get("event")=="SESSION_CLOSED"]
    early=bool(closes and (not summaries or min(e["timestamp_ms"] for e in closes)<min(m["end_ms"] for m in summaries)))
    return {"failed":not summaries or early,"message_ids":[m["message_id"] for m in summaries],"event_ids":[e["event_id"] for e in closes if early],"pass_detail":"候補者要約の後にセッションが終了した。"}
