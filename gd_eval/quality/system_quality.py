"""Build AI/system quality without importing candidate-performance rules."""
from __future__ import annotations
from typing import Any, Callable
from .stakeholder_conflict import finalize_before_conflict, silence_minority_concern
from .time_boxed_decision import finalize_before_risk_reveal, skip_summary

class UnsupportedQualityRuleError(ValueError): pass

def _messages(episode: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(episode.get("messages", []), key=lambda item:(item["start_ms"],item["message_id"]))

def _ai_defines_scope_before_candidate(episode,target_participant_id):
    messages=_messages(episode)
    first_user=min((m["start_ms"] for m in messages if m.get("speaker_type")=="user" and m.get("participant_id")==target_participant_id),default=float("inf"))
    offenders=[m for m in messages if m.get("speaker_type")=="ai" and m.get("move") in {"define_scope","define_criteria"} and m.get("start_ms",0)<first_user]
    return {"failed":bool(offenders),"message_ids":[m["message_id"] for m in offenders],"event_ids":[],"pass_detail":"AIによる先回りの課題定義は観察されない。"}

def _private_concern_revealed_without_trigger(episode,target_participant_id):
    del target_participant_id
    concerns=[e for e in episode.get("events",[]) if e.get("event")=="PRIVATE_CONCERN_REVEALED"]
    messages={m["message_id"]:m for m in episode.get("messages",[])}
    invalid=[e for e in concerns if e.get("trigger_move") not in {"ask_question","compare_options","challenge"} or e.get("message_id") not in messages or not any(m.get("move")==e.get("trigger_move") and m.get("end_ms",0)<=e.get("timestamp_ms",0) and m.get("message_id")!=e.get("message_id") for m in messages.values())]
    return {"failed":bool(invalid),"message_ids":[e["message_id"] for e in concerns if e.get("message_id")],"event_ids":[e["event_id"] for e in concerns],"pass_detail":"triggerなしの非公開懸念開示は観察されない。"}

_PROHIBITED_HANDLERS: dict[str, Callable[[dict[str,Any],str],dict[str,Any]]] = {
 "ai_defines_scope_before_candidate":_ai_defines_scope_before_candidate,
 "private_concern_revealed_without_trigger":_private_concern_revealed_without_trigger,
 "finalize_before_conflict":finalize_before_conflict,
 "silence_minority_concern":silence_minority_concern,
 "finalize_before_risk_reveal":finalize_before_risk_reveal,
 "skip_summary":skip_summary,
}

def _quality_status(results):
    failed=[r for r in results if r["outcome"]=="fail"]
    if any(r["severity"]=="critical" for r in failed): return "fail"
    return "warn" if failed else "pass"

def build_system_quality(scenario,episode,deterministic_result,target_participant_id,evaluator_version):
    results=[{k:v for k,v in r.items() if k!="target"} for r in deterministic_result["rule_results"] if r["target"]=="ai_system"]
    explicit={e.get("condition_id"):e for e in episode.get("events",[]) if e.get("event")=="PROHIBITED_CONDITION_TRIGGERED"}
    for condition in scenario.get("prohibited_conditions",[]):
        rule_id=condition.get("rule_id"); handler=_PROHIBITED_HANDLERS.get(rule_id)
        if handler is None: raise UnsupportedQualityRuleError(f"UNIMPLEMENTED_QUALITY_RULE: {rule_id}")
        outcome=handler(episode,target_participant_id); triggered=condition["condition_id"] in explicit; failed=bool(outcome["failed"] or triggered); event_ids=list(outcome["event_ids"])
        if triggered and explicit[condition["condition_id"]].get("event_id") not in event_ids: event_ids.append(explicit[condition["condition_id"]]["event_id"])
        results.append({"rule_id":condition["condition_id"],"outcome":"fail" if failed else "pass","severity":condition["severity"],"evidence_message_ids":outcome["message_ids"],"evidence_event_ids":event_ids,"affected_dimensions":condition["affected_dimensions"],"detail":"禁止条件が発生した。" if failed else outcome["pass_detail"]})
    status=_quality_status(results); agency_ok=not any(r["outcome"]=="fail" and r["severity"]=="critical" for r in results)
    dimension_scores={"goal_progression":4,"responsiveness":4,"user_agency":5 if agency_ok else 2,"role_believability":4,"discussion_coherence":4,"novelty_and_repetition":4,"consensus_quality":4,"natural_pacing":4}
    return {"contract_version":"0.1","result_id":f"sq-{episode['session_id']}","session_id":episode["session_id"],"scenario_id":episode["scenario_id"],"scenario_version":episode["scenario_version"],"evaluator_version":evaluator_version,"status":status,"rule_results":results,"dimension_scores":dimension_scores}
