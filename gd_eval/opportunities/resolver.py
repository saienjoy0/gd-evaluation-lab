"""Resolve evaluation opportunities from verified Episode evidence."""
from __future__ import annotations
from typing import Any, Callable
from .stakeholder_conflict import CONTEXT_HANDLERS as STAKEHOLDER_CONTEXT_HANDLERS
from .stakeholder_conflict import TRIGGER_HANDLERS as STAKEHOLDER_TRIGGER_HANDLERS
from .time_boxed_decision import CONTEXT_HANDLERS as TIME_CONTEXT_HANDLERS
from .time_boxed_decision import TRIGGER_HANDLERS as TIME_TRIGGER_HANDLERS

class OpportunityResolutionError(ValueError): pass

def _messages(episode): return sorted(episode.get("messages",[]),key=lambda x:(x["start_ms"],x["message_id"]))
def _before(messages,timestamp): return [m for m in messages if m.get("end_ms",0)<=timestamp]
def _after(messages,timestamp): return [m for m in messages if m.get("start_ms",0)>=timestamp]
def _after_initial_positions(scenario,episode,event):
    prior={m.get("participant_id") for m in _before(_messages(episode),event["timestamp_ms"]) if m.get("speaker_type")=="ai"}
    expected={p["agent_id"] for p in scenario.get("ai_participants",[])}
    return bool(expected) and expected<=prior
def _after_goal_question(scenario,episode,event):
    del scenario
    return any(m.get("speaker_type")=="ai" and m.get("move")=="ask_question" and m.get("phase")=="problem_definition" for m in _before(_messages(episode),event["timestamp_ms"]))
def _before_idea_generation(scenario,episode,event):
    del scenario
    starts=[m["start_ms"] for m in _messages(episode) if m.get("phase")=="idea_generation"]
    return bool(starts) and event["timestamp_ms"]<min(starts)
def _after_two_options_present(scenario,episode,event):
    prior=_before(_messages(episode),event["timestamp_ms"])
    return any(m.get("move")=="compare_options" for m in prior) or len({m.get("participant_id") for m in prior if m.get("speaker_type")=="ai"})>=min(2,len(scenario.get("ai_participants",[])))
def _after_constraint_reveal(scenario,episode,event):
    del scenario
    return any(e.get("event")=="PRIVATE_CONCERN_REVEALED" and e.get("timestamp_ms",0)<=event["timestamp_ms"] for e in episode.get("events",[]))
def _after_ai_question(scenario,episode,event):
    del scenario
    return any(m.get("speaker_type")=="ai" and m.get("move")=="ask_question" for m in _before(_messages(episode),event["timestamp_ms"]))
def _after_private_concern_reveal(scenario,episode,event): return _after_constraint_reveal(scenario,episode,event)
def _after_initial_ideas(scenario,episode,event):
    del scenario
    return any(m.get("phase")=="idea_generation" for m in _before(_messages(episode),event["timestamp_ms"]))
def _after_tradeoff_identified(scenario,episode,event):
    del scenario
    return any(m.get("phase")=="option_comparison" and m.get("move") in {"compare_options","challenge","integrate"} for m in _before(_messages(episode),event["timestamp_ms"]))
def _after_position_conflict(scenario,episode,event):
    del scenario
    prior=_before(_messages(episode),event["timestamp_ms"])
    return any(m.get("move")=="challenge" for m in prior) and len({m.get("participant_id") for m in prior if m.get("speaker_type")=="ai"})>=2
def _before_final_selection(scenario,episode,event):
    del scenario
    return any(m.get("speaker_type")=="user" and m.get("phase")=="decision" and m.get("move") in {"confirm_consensus","propose_decision"} for m in _after(_messages(episode),event["timestamp_ms"]))
def _before_session_close(scenario,episode,event):
    del scenario
    return any(m.get("phase")=="summary" for m in _after(_messages(episode),event["timestamp_ms"]))

_TRIGGER_HANDLERS: dict[str,Callable[[dict[str,Any],dict[str,Any],dict[str,Any]],bool]]={
 "after_initial_positions":_after_initial_positions,"after_goal_question":_after_goal_question,"before_idea_generation":_before_idea_generation,
 "after_two_options_present":_after_two_options_present,"after_constraint_reveal":_after_constraint_reveal,"after_ai_question":_after_ai_question,
 "after_private_concern_reveal":_after_private_concern_reveal,"after_initial_ideas":_after_initial_ideas,"after_tradeoff_identified":_after_tradeoff_identified,
 "after_position_conflict":_after_position_conflict,"before_final_selection":_before_final_selection,"before_session_close":_before_session_close,
 **STAKEHOLDER_TRIGGER_HANDLERS,**TIME_TRIGGER_HANDLERS,
}

def _resolved_before(episode,key,timestamp): return any(e.get("event")=="CONTEXT_RESOLVED" and e.get("key")==key and e.get("timestamp_ms",0)<=timestamp for e in episode.get("events",[]))
def _context_satisfied(context,scenario,episode,event,target_participant_id):
    timestamp=event["timestamp_ms"]; prior=_before(_messages(episode),timestamp); future=_after(_messages(episode),timestamp)
    checks={
      "priority_target_undefined":not _resolved_before(episode,"priority_target",timestamp),
      "success_metric_undefined":not _resolved_before(episode,"success_metric",timestamp),
      "scope_boundaries_undefined":not _resolved_before(episode,"scope_boundaries",timestamp),
      "two_options_available":any(m.get("move")=="compare_options" for m in prior) or len({m.get("participant_id") for m in prior if m.get("speaker_type")=="ai"})>=2,
      "constraint_requires_tradeoff":any(e.get("event")=="PRIVATE_CONCERN_REVEALED" and e.get("timestamp_ms",0)<=timestamp for e in episode.get("events",[])),
      "ai_question_open":any(m.get("speaker_type")=="ai" and m.get("move")=="ask_question" for m in prior),
      "concern_requires_response":any(e.get("event")=="PRIVATE_CONCERN_REVEALED" and e.get("timestamp_ms",0)<=timestamp for e in episode.get("events",[])) and any(m.get("speaker_type")=="user" for m in future),
      "idea_space_open":any(m.get("phase")=="idea_generation" for m in prior+future),
      "improvement_possible":any(m.get("phase")=="option_comparison" and m.get("move") in {"compare_options","challenge","integrate"} for m in prior),
      "multiple_positions_active":len({m.get("participant_id") for m in prior if m.get("speaker_type")=="ai"})>=2,
      "criteria_and_options_available":any(m.get("speaker_type")=="user" and m.get("move")=="define_criteria" for m in prior) and any(m.get("move")=="compare_options" for m in prior),
      "remaining_time_visible":timestamp<max((m.get("end_ms",0) for m in _messages(episode)),default=timestamp),
    }
    if context in checks: return checks[context]
    handler=TIME_CONTEXT_HANDLERS.get(context) or STAKEHOLDER_CONTEXT_HANDLERS.get(context)
    if handler is None: raise OpportunityResolutionError(f"UNIMPLEMENTED_OPPORTUNITY_CONTEXT: {context}")
    return handler(scenario,episode,event,target_participant_id)

def resolve_opportunities(scenario,episode,system_quality,target_participant_id,resolver_version):
    messages={m["message_id"]:m for m in episode.get("messages",[])}
    target_messages={mid for mid,m in messages.items() if m.get("speaker_type")=="user" and m.get("participant_id")==target_participant_id}
    offers={}
    for e in episode.get("events",[]):
        if e.get("event")=="OPPORTUNITY_OFFERED": offers.setdefault(e.get("opportunity_id"),[]).append(e)
    failed_conditions={r["rule_id"] for r in system_quality.get("rule_results",[]) if r["outcome"]=="fail"}
    items=[]
    for opportunity in scenario.get("evaluation_opportunities",[]):
        oid=opportunity["opportunity_id"]; events=sorted(offers.get(oid,[]),key=lambda e:e["timestamp_ms"])
        invalidated=[c for c in opportunity.get("invalidated_by",[]) if c in failed_conditions]
        for event in events:
            if event.get("dimension")!=opportunity["dimension"]: raise OpportunityResolutionError(f"OPPORTUNITY_DIMENSION_MISMATCH: {oid}")
            trigger=opportunity.get("trigger"); handler=_TRIGGER_HANDLERS.get(trigger)
            if handler is None: raise OpportunityResolutionError(f"UNIMPLEMENTED_OPPORTUNITY_TRIGGER: {trigger}")
            if not handler(scenario,episode,event): raise OpportunityResolutionError(f"OPPORTUNITY_TRIGGER_INVALID: {oid}")
            if not all(_context_satisfied(c,scenario,episode,event,target_participant_id) for c in opportunity.get("required_context",[])): raise OpportunityResolutionError(f"OPPORTUNITY_CONTEXT_INVALID: {oid}")
        response_ids=[]
        for event in events:
            for mid in event.get("candidate_response_message_ids",[]):
                message=messages.get(mid)
                if mid not in target_messages: raise OpportunityResolutionError(f"EVIDENCE_OWNER_MISMATCH: {oid}:{mid}")
                if message.get("phase")!=opportunity.get("phase"): raise OpportunityResolutionError(f"OPPORTUNITY_PHASE_MISMATCH: {oid}:{mid}")
                if message.get("start_ms",0)<event.get("timestamp_ms",0): raise OpportunityResolutionError(f"OPPORTUNITY_RESPONSE_BEFORE_TRIGGER: {oid}:{mid}")
                if mid not in response_ids: response_ids.append(mid)
        if invalidated:
            status="invalid"; response_status="not_applicable"; response_ids=[]; detail="禁止条件により評価機会が無効化された。"
        elif events:
            status="offered"; response_status="observed" if response_ids else "not_observed"; detail="構造化イベントと利用者応答を確認した。" if response_ids else "評価機会は提供されたが利用者応答は観察されない。"
        else:
            status="not_offered"; response_status="not_applicable"; detail="対応する評価機会イベントが存在しない。"
        items.append({"opportunity_id":oid,"dimension":opportunity["dimension"],"status":status,"trigger_event_ids":[e["event_id"] for e in events],"candidate_response_message_ids":response_ids,"invalidated_by":invalidated,"response_status":response_status,"detail":detail})
    summary={"offered":sum(i["status"]=="offered" for i in items),"not_offered":sum(i["status"]=="not_offered" for i in items),"invalid":sum(i["status"]=="invalid" for i in items),"with_candidate_response":sum(i["response_status"]=="observed" for i in items)}
    return {"contract_version":"0.1","resolution_id":f"or-{episode['session_id']}","session_id":episode["session_id"],"scenario_id":episode["scenario_id"],"scenario_version":episode["scenario_version"],"target_participant_id":target_participant_id,"resolver_version":resolver_version,"items":items,"summary":summary}
