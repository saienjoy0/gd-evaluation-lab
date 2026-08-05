"""Deterministic rules for time-boxed decision scenarios."""
from __future__ import annotations
from typing import Any


def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(episode.get("messages", []), key=lambda x: (x["start_ms"], x["message_id"]))


def _target(episode: dict[str, Any], params: dict[str, Any]) -> str:
    if params.get("target_participant_id"):
        return str(params["target_participant_id"])
    users=[p["participant_id"] for p in episode.get("participants",[]) if p.get("speaker_type")=="user"]
    if len(users)!=1:
        raise ValueError("TARGET_PARTICIPANT_AMBIGUOUS")
    return users[0]


def _events(episode: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [e for e in episode.get("events",[]) if e.get("event")==name]


def time_checkpoints_followed_by_candidate_turn(scenario, episode, params):
    duration_ms=int(scenario["duration_seconds"])*1000
    target=_target(episode,params)
    msgs={m["message_id"]:m for m in _messages(episode)}
    checkpoints=[int(v) for v in params.get("checkpoints_percent",[])]
    tolerance=duration_ms*float(params.get("tolerance_percent_of_duration",5))/100
    max_delay=int(params.get("maximum_response_delay_ms",90000))
    minimum=int(params.get("minimum_candidate_turns_after_each",1))
    evs=_events(episode,"TIME_CHECKPOINT_REACHED")
    evidence_messages=[]; evidence_events=[]; ok=True
    for i,pct in enumerate(checkpoints):
        candidates=[e for e in evs if int(e.get("checkpoint_percent",-1))==pct]
        if not candidates:
            ok=False; continue
        event=min(candidates,key=lambda e:e["timestamp_ms"])
        expected=duration_ms*pct/100
        linked=msgs.get(event.get("message_id"))
        if abs(event["timestamp_ms"]-expected)>tolerance or not linked or linked.get("speaker_type")!="ai" or linked.get("move")!="time_check":
            ok=False; continue
        next_ts=duration_ms
        if i+1<len(checkpoints):
            next_ts=duration_ms*checkpoints[i+1]/100+tolerance
        responses=[m for m in _messages(episode) if m.get("speaker_type")=="user" and m.get("participant_id")==target and m.get("start_ms",0)>=event["timestamp_ms"] and m.get("start_ms",0)<=event["timestamp_ms"]+max_delay and m.get("start_ms",0)<next_ts]
        if len(responses)<minimum:
            ok=False
        else:
            evidence_messages.extend([linked["message_id"],*[m["message_id"] for m in responses[:minimum]]]); evidence_events.append(event["event_id"])
    return {"ok":ok,"evidence_message_ids":list(dict.fromkeys(evidence_messages)),"evidence_event_ids":evidence_events,"detail":f"{len(evidence_events)}件の時間通知後に候補者ターンが確保された。"}


def private_concern_revealed_before_phase(scenario, episode, params):
    before_phase=params.get("before_phase","decision")
    starts=[m["start_ms"] for m in _messages(episode) if m.get("phase")==before_phase]
    cutoff=min(starts) if starts else float("inf")
    ai={p["agent_id"]:p for p in scenario.get("ai_participants",[])}
    msgs={m["message_id"]:m for m in _messages(episode)}
    valid=[]
    for e in _events(episode,"PRIVATE_CONCERN_REVEALED"):
        if params.get("require_late_risk",False) and not e.get("late_risk"):
            continue
        m=msgs.get(e.get("message_id")); p=ai.get(e.get("participant_id"))
        if not m or not p or m.get("speaker_type")!="ai" or m.get("participant_id")!=e.get("participant_id"):
            continue
        if e.get("concern")!=p.get("private_concern") or e.get("timestamp_ms",0)>=cutoff:
            continue
        valid.append(e)
    minimum=int(params.get("minimum_concerns",1))
    unique={e.get("concern") for e in valid}
    return {"ok":len(unique)>=minimum,"evidence_message_ids":[e["message_id"] for e in valid],"evidence_event_ids":[e["event_id"] for e in valid],"detail":f"決定前に{len(unique)}件の遅延リスクが開示された。"}


def candidate_prioritizes_after_time_check(scenario, episode, params):
    del scenario
    target=_target(episode,params); msgs={m["message_id"]:m for m in _messages(episode)}
    checkpoints=sorted(_events(episode,"TIME_CHECKPOINT_REACHED"),key=lambda e:e["timestamp_ms"])
    valid=[]
    for e in _events(episode,"PRIORITY_UPDATE_RECORDED"):
        m=msgs.get(e.get("message_id")); prior=[c for c in checkpoints if c["timestamp_ms"]<=e.get("timestamp_ms",0)]
        if not m or not prior or m.get("speaker_type")!="user" or m.get("participant_id")!=target or m.get("move")!="prioritize":
            continue
        checkpoint=max(prior,key=lambda c:c["timestamp_ms"])
        if m.get("start_ms",0)<checkpoint["timestamp_ms"] or len(e.get("ordered_items",[]))<int(params.get("minimum_ordered_items",2)):
            continue
        valid.append(e)
    return {"ok":len(valid)>=int(params.get("minimum_occurrences",1)),"evidence_message_ids":[e["message_id"] for e in valid],"evidence_event_ids":[e["event_id"] for e in valid],"detail":f"時間通知後の優先順位更新を{len(valid)}件確認した。"}


def candidate_compares_and_revises(scenario, episode, params):
    target=_target(episode,params); msgs={m["message_id"]:m for m in _messages(episode)}
    required_options=set(scenario.get("shared_context",{}).get("options",[]))
    comparisons=[]
    for e in _events(episode,"OPTIONS_COMPARED"):
        m=msgs.get(e.get("message_id"))
        if m and m.get("speaker_type")=="user" and m.get("participant_id")==target and m.get("move")=="compare_options" and required_options<=set(e.get("options",[])) and len(e.get("options",[]))>=int(params.get("minimum_options",3)) and len(e.get("criteria",[]))>=int(params.get("minimum_criteria",2)):
            comparisons.append(e)
    risks=[e for e in _events(episode,"PRIVATE_CONCERN_REVEALED") if e.get("late_risk")]
    revisions=[]
    for e in _events(episode,"DECISION_REVISION_RECORDED"):
        before=msgs.get(e.get("before_message_id")); after=msgs.get(e.get("after_message_id")); linked=next((r for r in risks if r.get("event_id")==e.get("risk_event_id")),None)
        if not before or not after or not linked or after.get("speaker_type")!="user" or after.get("participant_id")!=target or after.get("start_ms",0)<linked.get("timestamp_ms",0) or not e.get("changed_fields"):
            continue
        revisions.append(e)
    ok=bool(comparisons) and (bool(revisions) if params.get("requires_risk_response",False) else True)
    return {"ok":ok,"evidence_message_ids":[*[e["message_id"] for e in comparisons],*[e["after_message_id"] for e in revisions]],"evidence_event_ids":[*[e["event_id"] for e in comparisons],*[e["event_id"] for e in revisions]],"detail":"三案比較と遅延リスク後の案修正を確認した。"}
