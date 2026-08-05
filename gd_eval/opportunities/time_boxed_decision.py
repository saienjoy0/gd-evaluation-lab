"""Opportunity trigger/context handlers for time-boxed decisions."""
from __future__ import annotations
from typing import Any, Callable
TriggerHandler=Callable[[dict[str,Any],dict[str,Any],dict[str,Any]],bool]
ContextHandler=Callable[[dict[str,Any],dict[str,Any],dict[str,Any],str],bool]

def _messages(ep): return sorted(ep.get("messages",[]),key=lambda x:(x["start_ms"],x["message_id"]))
def _before(ep,ts): return [m for m in _messages(ep) if m.get("end_ms",0)<=ts]
def _after(ep,ts): return [m for m in _messages(ep) if m.get("start_ms",0)>=ts]
def _events_before(ep,name,ts): return [e for e in ep.get("events",[]) if e.get("event")==name and e.get("timestamp_ms",0)<=ts]
def _event_before(name, pred=lambda e:True):
    def h(s,ep,e): del s; return any(pred(x) for x in _events_before(ep,name,e["timestamp_ms"]))
    return h

def _after_initial_positions(s,ep,e):
    ids={m.get("participant_id") for m in _before(ep,e["timestamp_ms"]) if m.get("speaker_type")=="ai" and m.get("move")=="propose_idea"}
    return len(ids)>=min(3,len(s.get("ai_participants",[])))
def _before_future(move):
    def h(s,ep,e): del s; return any(m.get("speaker_type")=="user" and m.get("move")==move for m in _after(ep,e["timestamp_ms"]))
    return h
def _checkpoint(pct):
    def h(s,ep,e):
        dur=s["duration_seconds"]*1000; tol=dur*.05
        return any(int(x.get("checkpoint_percent",-1))==pct and abs(x["timestamp_ms"]-dur*pct/100)<=tol and x["timestamp_ms"]<=e["timestamp_ms"] for x in ep.get("events",[]) if x.get("event")=="TIME_CHECKPOINT_REACHED")
    return h

def _decision_criteria_incomplete(s,ep,e,t): del s,t; return not _events_before(ep,"CRITERIA_RECORDED",e["timestamp_ms"])
def _three_options_available(s,ep,e,t): del t; return any(set(s.get("shared_context",{}).get("options",[]))<=set(x.get("options",[])) for x in _events_before(ep,"OPTIONS_PRESENTED",e["timestamp_ms"]))
def _risk_requires_reassessment(s,ep,e,t): del s,t; return bool(_events_before(ep,"PRIVATE_CONCERN_REVEALED",e["timestamp_ms"])) and not _events_before(ep,"DECISION_REVISION_RECORDED",e["timestamp_ms"])
def _security_open(s,ep,e,t): del s,t; return any(x.get("status")=="open" for x in _events_before(ep,"SECURITY_CONCERN_STATUS",e["timestamp_ms"]))
def _risk_response(s,ep,e,t): del s; return bool(_events_before(ep,"PRIVATE_CONCERN_REVEALED",e["timestamp_ms"])) and any(m.get("speaker_type")=="user" and m.get("participant_id")==t for m in _after(ep,e["timestamp_ms"]))
def _solution_open(s,ep,e,t): del s; return not any(m.get("speaker_type")=="user" and m.get("participant_id")==t and m.get("move")=="confirm_consensus" for m in _before(ep,e["timestamp_ms"]))
def _hybrid_possible(s,ep,e,t): del s,t; return any("ハイブリッド" in x.get("candidate_modes",[]) for x in _events_before(ep,"CONSTRAINT_COLLISION_RECORDED",e["timestamp_ms"]))
def _regional_open(s,ep,e,t): del s,t; return any(x.get("status")=="open" for x in _events_before(ep,"REGIONAL_ACCESS_CONCERN_STATUS",e["timestamp_ms"]))
def _decision_requires_revision(s,ep,e,t): del s,t; return bool(_events_before(ep,"PRELIMINARY_DECISION_RECORDED",e["timestamp_ms"])) and bool(_events_before(ep,"PRIVATE_CONCERN_REVEALED",e["timestamp_ms"])) and not _events_before(ep,"DECISION_REVISION_RECORDED",e["timestamp_ms"])
def _implementation_required(s,ep,e,t): del s; return not _events_before(ep,"IMPLEMENTATION_CONDITION_RECORDED",e["timestamp_ms"]) and any(m.get("speaker_type")=="user" and m.get("participant_id")==t and m.get("move")=="confirm_consensus" for m in _after(ep,e["timestamp_ms"]))
def _unresolved(s,ep,e,t): del s,t; return any(x.get("items") for x in _events_before(ep,"UNRESOLVED_ITEMS_RECORDED",e["timestamp_ms"]))
def _summary_required(s,ep,e,t): del s; return bool(_events_before(ep,"FINAL_DECISION_RECORDED",e["timestamp_ms"])) and not _events_before(ep,"SUMMARY_RECORDED",e["timestamp_ms"])

TRIGGER_HANDLERS={
 "after_success_requirements":_event_before("SUCCESS_REQUIREMENTS_PRESENTED",lambda x:len(x.get("requirements",[]))>=3),
 "after_three_options_present":_event_before("OPTIONS_PRESENTED",lambda x:len(x.get("options",[]))>=3),
 "after_late_risk_reveal":_event_before("PRIVATE_CONCERN_REVEALED",lambda x:bool(x.get("late_risk"))),
 "after_security_question":_event_before("SECURITY_CONCERN_STATUS",lambda x:x.get("status")=="open"),
 "after_constraint_collision":_event_before("CONSTRAINT_COLLISION_RECORDED",lambda x:len(x.get("constraints",[]))>=2),
 "before_final_alignment":_before_future("confirm_consensus"),
 "after_criteria_defined":_event_before("CRITERIA_RECORDED"),
 "before_consensus_confirmation":_before_future("confirm_consensus"),
 "at_40_percent_time_checkpoint":_checkpoint(40),
 "at_75_percent_time_checkpoint":_checkpoint(75),
}
CONTEXT_HANDLERS={
 "decision_criteria_incomplete":_decision_criteria_incomplete,"three_options_available":_three_options_available,"risk_requires_reassessment":_risk_requires_reassessment,
 "security_concern_open":_security_open,"risk_requires_response":_risk_response,"solution_space_open":_solution_open,"hybrid_solution_possible":_hybrid_possible,
 "regional_access_concern_present":_regional_open,"decision_requires_revision":_decision_requires_revision,"implementation_condition_required":_implementation_required,
 "unresolved_items_visible":_unresolved,"summary_required":_summary_required,
}
