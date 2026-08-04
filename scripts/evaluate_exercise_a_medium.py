#!/usr/bin/env python3
"""Regenerate Exercise A medium vertical-slice outputs without an LLM."""
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"fixtures/calibration/full-episodes/ambiguous-structure/medium"

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def transcript_hash(messages):
    return hashlib.sha256(json.dumps(messages,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def system_quality(scenario,episode):
    msgs={m["message_id"]:m for m in episode["messages"]}
    cand=[m for m in episode["messages"] if m["speaker_type"]=="user" and m["phase"]=="problem_definition" and m["move"] in {"clarify_goal","define_scope","define_criteria"}]
    ctx=[e for e in episode["events"] if e["event"]=="CONTEXT_RESOLVED"]
    concerns=[e for e in episode["events"] if e["event"]=="PRIVATE_CONCERN_REVEALED"]
    summaries=[e for e in episode["events"] if e["event"]=="SUMMARY_FIELDS_RECORDED"]
    prohibited=[e for e in episode["events"] if e["event"]=="PROHIBITED_CONDITION_TRIGGERED"]
    rubrics={r["rubric_id"]:r for r in scenario["instance_rubrics"]}
    conditions={r["condition_id"]:r for r in scenario["prohibited_conditions"]}
    resolved={e.get("key") for e in ctx}
    fields={f for e in summaries for f in e.get("fields",[])}
    triggered={e.get("condition_id") for e in prohibited}
    checks={
      "A-R01":(len(cand)>=3,[m["message_id"] for m in cand],[],"AIが対象・基準を先に確定せず、利用者が先に定義した。"),
      "A-R02":(len(resolved&{"priority_target","success_metric","usage_hours"})>=2,[e["message_id"] for e in ctx],[e["event_id"] for e in ctx],"三つの文脈キーが解消された。"),
      "A-R04":(bool(concerns) and all(e.get("trigger_move") in {"ask_question","compare_options","challenge"} for e in concerns),[e["message_id"] for e in concerns],[e["event_id"] for e in concerns],"非公開懸念は質問・比較後に開示された。"),
      "A-R05":({"success_metric","pilot_condition"}<=fields,[e["message_id"] for e in summaries],[e["event_id"] for e in summaries],"要約に成功指標と実証見直し条件が含まれる。")
    }
    results=[]
    for rid,(ok,mids,eids,detail) in checks.items():
        src=rubrics[rid]
        results.append({"rule_id":rid,"outcome":"pass" if ok else "fail","severity":src["severity"],"evidence_message_ids":mids,"evidence_event_ids":eids,"affected_dimensions":src["affected_dimensions"],"detail":detail if ok else "決定論的条件を満たさなかった。"})
    for cid in ["A-PROH-01","A-PROH-02"]:
        src=conditions[cid]; bad=cid in triggered
        mids=[e["message_id"] for e in concerns] if cid=="A-PROH-02" else []
        eids=[e["event_id"] for e in concerns] if cid=="A-PROH-02" else [e["event_id"] for e in prohibited if e.get("condition_id")==cid]
        detail=("triggerなしの非公開懸念開示は観察されない。" if cid=="A-PROH-02" else "AIによる先回りの課題定義は観察されない。")
        results.append({"rule_id":cid,"outcome":"fail" if bad else "pass","severity":src["severity"],"evidence_message_ids":mids,"evidence_event_ids":eids,"affected_dimensions":src["affected_dimensions"],"detail":detail if not bad else "禁止条件が発生した。"})
    fails=[r for r in results if r["outcome"]=="fail"]
    status="fail" if any(r["severity"]=="critical" for r in fails) else "warn" if fails else "pass"
    scores={"goal_progression":4,"responsiveness":4,"user_agency":5 if checks["A-R01"][0] else 2,"role_believability":4,"discussion_coherence":4,"novelty_and_repetition":4,"consensus_quality":4 if checks["A-R05"][0] else 2,"natural_pacing":4}
    return {"contract_version":"0.1","result_id":f"sq-{episode['session_id']}","session_id":episode["session_id"],"scenario_id":episode["scenario_id"],"scenario_version":episode["scenario_version"],"evaluator_version":"exercise-a-deterministic-v0.1","status":status,"rule_results":results,"dimension_scores":scores}

def opportunities(scenario,episode):
    offers={}
    invalid={}
    mids={m["message_id"] for m in episode["messages"]}
    for e in episode["events"]:
        if e["event"]=="OPPORTUNITY_OFFERED": offers.setdefault(e.get("opportunity_id"),[]).append(e)
        if e["event"]=="PROHIBITED_CONDITION_TRIGGERED": invalid.setdefault(e.get("condition_id"),[]).append(e)
    items=[]
    for o in scenario["evaluation_opportunities"]:
        evs=offers.get(o["opportunity_id"],[])
        bad=[c for c in o.get("invalidated_by",[]) if c in invalid]
        responses=list(dict.fromkeys(mid for e in evs for mid in e.get("candidate_response_message_ids",[]) if mid in mids))
        if bad: status,response,detail="invalid","not_applicable","禁止条件により評価機会が無効化された。"
        elif evs: status,response,detail="offered","observed" if responses else "not_observed","構造化イベントと利用者応答を確認した。" if responses else "評価機会は提供されたが利用者応答は観察されない。"
        else: status,response,detail="not_offered","not_applicable","対応する評価機会イベントが存在しない。"
        items.append({"opportunity_id":o["opportunity_id"],"dimension":o["dimension"],"status":status,"trigger_event_ids":[e["event_id"] for e in evs],"candidate_response_message_ids":responses,"invalidated_by":bad,"response_status":response,"detail":detail})
    return {"contract_version":"0.1","resolution_id":f"or-{episode['session_id']}","session_id":episode["session_id"],"scenario_id":episode["scenario_id"],"scenario_version":episode["scenario_version"],"resolver_version":"opportunity-resolver-v0.1","items":items,"summary":{"offered":sum(i["status"]=="offered" for i in items),"not_offered":sum(i["status"]=="not_offered" for i in items),"invalid":sum(i["status"]=="invalid" for i in items),"with_candidate_response":sum(i["response_status"]=="observed" for i in items)}}

def evaluation(episode,sq,adj,feedback):
    dims=[]
    for r in adj["dimension_resolutions"]:
        n=feedback["dimension_narratives"][r["dimension"]]; ne=r["final_score"]=="NE"
        dims.append({"dimension":r["dimension"],"score":r["final_score"],"confidence":0 if ne else .9,"evidence_message_ids":r["final_evidence_message_ids"],"positive_behavior":"" if ne else n["positive"],"missing_behavior":"" if ne else n["missing"],"improvement":"" if ne else n["improvement"],"not_evaluable_reason":{"code":r["not_evaluable_reason"],"detail":r["resolution_reason"]} if ne else None,"question_results":[]})
    violations=[{"rule_id":r["rule_id"],"severity":r["severity"],"message_ids":r["evidence_message_ids"],"affected_candidate_dimensions":r["affected_dimensions"]} for r in sq["rule_results"] if r["outcome"]=="fail"]
    return {"contract_version":"0.1","session_id":episode["session_id"],"target_participant_id":next(p["participant_id"] for p in episode["participants"] if p["speaker_type"]=="user"),"status":"completed" if all(r["final_score"]!="NE" for r in adj["dimension_resolutions"]) else "partial","ai_quality":{"status":sq["status"],"violations":violations,"dimension_scores":sq["dimension_scores"]},"candidate_dimensions":dims,"display_groups":feedback["display_groups"],"version_info":{"rubric_version":"candidate-behavior-v0.1","ai_quality_rubric_version":"ai-participant-v0.1","scenario_version":episode["scenario_version"],"orchestrator_version":episode["versions"]["orchestrator_version"],"prompt_version":episode["versions"]["prompt_version"],"judge_model":"human-adjudication","judge_version":"not-applied-v0.1","deterministic_evaluator_version":"exercise-a-deterministic-v0.1","transcript_hash":episode["transcript_hash"]},"review_status":"completed","legacy_evaluation":None,"evaluation_disagreement":None}

def build(repo=ROOT):
    base=repo/"fixtures/calibration/full-episodes/ambiguous-structure/medium"
    scenario=load(repo/"fixtures/scenarios/candidate-assessment-a-ambiguous-structure-v0.1.json")
    episode=load(base/"episode.json"); adj=load(base/"adjudication.json"); feedback=load(base/"expected-feedback.json")
    sq=system_quality(scenario,episode); op=opportunities(scenario,episode)
    return {"system_quality":sq,"opportunity_resolution":op,"evaluation_result":evaluation(episode,sq,adj,feedback)}

if __name__=="__main__": print(json.dumps(build(),ensure_ascii=False,indent=2,sort_keys=True))
