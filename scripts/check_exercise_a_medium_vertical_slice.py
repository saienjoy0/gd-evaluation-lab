#!/usr/bin/env python3
"""Validate Exercise A medium vertical slice and deterministic replay."""
from __future__ import annotations
import copy,hashlib,importlib.util,json
from pathlib import Path
from typing import Any,Callable
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT/"fixtures/calibration/full-episodes/ambiguous-structure/medium"
DIMS=["issue_framing","logical_reasoning","listening_and_response","valuable_contribution","collaboration_and_relationship","decision_and_consensus","process_and_time_management"]
ORDER=["scenario","episode","deterministic_rules","system_quality","opportunity_resolution","rater_a","rater_b","adjudication","evaluation_result","feedback"]
class Err(AssertionError):
 def __init__(self,code,msg):super().__init__(f"{code}: {msg}");self.code=code
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def evaluator():
 spec=importlib.util.spec_from_file_location("exercise_a",ROOT/"scripts/evaluate_exercise_a_medium.py");mod=importlib.util.module_from_spec(spec)
 if spec.loader is None:raise RuntimeError("evaluator loader missing")
 spec.loader.exec_module(mod);return mod
def schema(x,s,label):
 Draft202012Validator.check_schema(s);errors=sorted(Draft202012Validator(s,format_checker=FormatChecker()).iter_errors(x),key=lambda e:list(e.absolute_path))
 if errors:raise Err("SCHEMA_INVALID",f"{label}: {list(errors[0].absolute_path)} {errors[0].message}")
def agree(a,b):
 if a==b:return "exact"
 if "NE" in (a,b):return "ne_disagreement"
 return "adjacent" if abs(a-b)==1 else "major_disagreement"
def quality_status(results):
 failed=[r for r in results if r["outcome"]=="fail"]
 return "fail" if any(r["severity"]=="critical" for r in failed) else "warn" if failed else "pass"
def validate(b,e):
 m,s,ep,dr,sq,op,ra,rb,adj,res,fb=[b[k] for k in ["manifest","scenario","deterministic_rules" if False else "episode","deterministic_rules","system_quality","opportunities","rater_a","rater_b","adjudication","evaluation","feedback"]]
 if m["pipeline_order"]!=ORDER:raise Err("PIPELINE_ORDER_MISMATCH","manifest")
 versions=[m["scenario_ref"]["scenario_id"]==s["scenario_id"],m["scenario_ref"]["version"]==s["version"],ep["scenario_id"]==s["scenario_id"],ep["scenario_version"]==s["version"],dr["scenario_id"]==s["scenario_id"],dr["scenario_version"]==s["version"],sq["scenario_id"]==s["scenario_id"],sq["scenario_version"]==s["version"],op["scenario_id"]==s["scenario_id"],op["scenario_version"]==s["version"]]
 if not all(versions):raise Err("VERSION_MISMATCH","derived artifacts")
 th=e.transcript_hash(ep["messages"])
 if ep["transcript_hash"]!=th or res["version_info"]["transcript_hash"]!=th:raise Err("TRANSCRIPT_HASH_MISMATCH","hash")
 messages={x["message_id"]:x for x in ep["messages"]};events={x["event_id"] for x in ep["events"]};target=res["target_participant_id"]
 user={mid for mid,x in messages.items() if x["speaker_type"]=="user" and x["participant_id"]==target}
 if op["target_participant_id"]!=target:raise Err("TARGET_PARTICIPANT_MISMATCH","opportunity target")
 def evidence(ids,label):
  for mid in ids:
   if mid not in user:raise Err("EVIDENCE_OWNER_MISMATCH",f"{label}:{mid}")
 scenario_opps={x["opportunity_id"] for x in s["evaluation_opportunities"]}
 if scenario_opps!={x["opportunity_id"] for x in op["items"]}:raise Err("OPPORTUNITY_ID_MISMATCH","set")
 bydim={d:[] for d in DIMS};summary={"offered":0,"not_offered":0,"invalid":0,"with_candidate_response":0}
 for x in op["items"]:
  bydim[x["dimension"]].append(x);evidence(x["candidate_response_message_ids"],x["opportunity_id"])
  if any(i not in events for i in x["trigger_event_ids"]):raise Err("UNKNOWN_EVENT_ID",x["opportunity_id"])
  summary[x["status"]]+=1;summary["with_candidate_response"]+=x["response_status"]=="observed"
  if x["status"]=="offered" and (not x["trigger_event_ids"] or x["invalidated_by"]):raise Err("OPPORTUNITY_STATUS_INCONSISTENT",x["opportunity_id"])
  if x["status"]=="not_offered" and (x["trigger_event_ids"] or x["candidate_response_message_ids"] or x["invalidated_by"] or x["response_status"]!="not_applicable"):raise Err("OPPORTUNITY_STATUS_INCONSISTENT",x["opportunity_id"])
  if x["status"]=="invalid" and (not x["invalidated_by"] or x["candidate_response_message_ids"] or x["response_status"]!="not_applicable"):raise Err("OPPORTUNITY_STATUS_INCONSISTENT",x["opportunity_id"])
 if op["summary"]!=summary:raise Err("OPPORTUNITY_SUMMARY_MISMATCH","counts")
 rubrics={r["rubric_id"]:r for r in s["instance_rubrics"]};drmap={r["rule_id"]:r for r in dr["rule_results"]}
 if set(drmap)!=set(rubrics):raise Err("DETERMINISTIC_RULE_SET_MISMATCH","rubrics")
 for rid,r in drmap.items():
  if r["target"]!=rubrics[rid]["target"]:raise Err("DETERMINISTIC_RULE_TARGET_MISMATCH",rid)
  evidence(r["evidence_message_ids"],rid) if r["target"]=="candidate" else None
 ai_rule_ids={rid for rid,r in drmap.items() if r["target"]=="ai_system"}|{c["condition_id"] for c in s["prohibited_conditions"]}
 if {r["rule_id"] for r in sq["rule_results"]}!=ai_rule_ids:raise Err("SYSTEM_QUALITY_SCOPE_MISMATCH","non-system rule included")
 if sq["status"]!=quality_status(sq["rule_results"]):raise Err("SYSTEM_QUALITY_STATUS_MISMATCH","status")
 for sheet in (ra,rb):
  for d in sheet["dimensions"]:
   evidence(d["selected_evidence_message_ids"],sheet["sheet_id"])
   if any(i not in events for i in d["opportunity_evidence_event_ids"]):raise Err("UNKNOWN_EVENT_ID",d["dimension"])
   if not any(x["status"]=="offered" for x in bydim[d["dimension"]]) and d["score"]!="NE":raise Err("SCORE_WITHOUT_OPPORTUNITY",d["dimension"])
 if ra["annotator_id"]==rb["annotator_id"]:raise Err("DUPLICATE_RATER","id")
 if adj["adjudicator_id"] in {ra["annotator_id"],rb["annotator_id"]}:raise Err("ADJUDICATOR_OVERLAP","id")
 scores=[{x["dimension"]:x["score"] for x in y["dimensions"]} for y in (ra,rb)];amap={}
 for d in adj["dimension_resolutions"]:
  expected=[scores[0][d["dimension"]],scores[1][d["dimension"]]]
  if d["rater_scores"]!=expected:raise Err("RATER_SCORE_MISMATCH",d["dimension"])
  if d["agreement_class"]!=agree(*expected):raise Err("AGREEMENT_CLASS_MISMATCH",d["dimension"])
  evidence(d["final_evidence_message_ids"],"adjudication");amap[d["dimension"]]=d
 for d in res["candidate_dimensions"]:
  evidence(d["evidence_message_ids"],"evaluation");a=amap[d["dimension"]]
  if d["score"]!=a["final_score"] or d["evidence_message_ids"]!=a["final_evidence_message_ids"]:raise Err("FINAL_RESULT_MISMATCH",d["dimension"])
  if d["score"]==4 and len({messages[mid]["phase"] for mid in d["evidence_message_ids"]})<2:raise Err("SCORE4_PHASE_DIVERSITY",d["dimension"])
  for q in d["question_results"]:
   evidence(q["evidence_message_ids"],"question")
   if abs(sum(q["probabilities"].values())-1)>1e-6:raise Err("PROBABILITY_SUM_INVALID",d["dimension"])
  n=fb["dimension_narratives"][d["dimension"]]
  if [n["positive"],n["missing"],n["improvement"]]!=[d["positive_behavior"],d["missing_behavior"],d["improvement"]]:raise Err("FEEDBACK_RESULT_MISMATCH",d["dimension"])
 if any(g["aggregation_status"]=="not_calibrated" and g["score"] is not None for g in res["display_groups"].values()):raise Err("UNCALIBRATED_GROUP_SCORE","score")
 if res["display_groups"]!=fb["display_groups"]:raise Err("FEEDBACK_RESULT_MISMATCH","groups")
 if sq["status"]!=res["ai_quality"]["status"] or sq["dimension_scores"]!=res["ai_quality"]["dimension_scores"]:raise Err("SYSTEM_QUALITY_MISMATCH","result")
 generated=e.build(ROOT)
 if generated["deterministic_rules"]!=dr or generated["system_quality"]!=sq or generated["opportunity_resolution"]!=op or generated["evaluation_result"]!=res or generated["feedback"]!=fb or e.build(ROOT)!=generated:raise Err("NONDETERMINISTIC_OUTPUT","golden")
def fail(code,fn):
 try:fn()
 except Err as x:
  if x.code!=code:raise AssertionError(f"expected {code}, got {x.code}") from x
  return
 raise AssertionError(f"{code} unexpectedly passed")
def main():
 e=evaluator();b={"manifest":load(BASE/"manifest.json"),"scenario":load(ROOT/"fixtures/scenarios/candidate-assessment-a-ambiguous-structure-v0.1.json"),"episode":load(BASE/"episode.json"),"deterministic_rules":load(BASE/"deterministic-rule-result.json"),"system_quality":load(BASE/"system-quality-result.json"),"opportunities":load(BASE/"opportunity-resolution.json"),"rater_a":load(BASE/"rater-sheet-a.json"),"rater_b":load(BASE/"rater-sheet-b.json"),"adjudication":load(BASE/"adjudication.json"),"evaluation":load(BASE/"evaluation-result.json"),"feedback":load(BASE/"expected-feedback.json")}
 schemas={"manifest":"vertical-slice-manifest-v0.1.schema.json","episode":"episode-v0.1.schema.json","deterministic_rules":"deterministic-rule-result-v0.1.schema.json","system_quality":"system-quality-result-v0.1.schema.json","opportunities":"opportunity-resolution-v0.1.schema.json","rater_a":"rater-sheet-v0.1.schema.json","rater_b":"rater-sheet-v0.1.schema.json","adjudication":"adjudication-v0.1.schema.json","evaluation":"evaluation-result-v0.1.schema.json"}
 for k,n in schemas.items():schema(b[k],load(ROOT/"schemas"/n),k)
 for name,a in b["manifest"]["artifacts"].items():
  p=ROOT/a["path"]
  if not p.is_file():raise Err("MANIFEST_PATH_MISSING",name)
  if sha(p)!=a["sha256"]:raise Err("MANIFEST_HASH_MISMATCH",name)
 validate(b,e);tests=[]
 def add(code,mut):
  x=copy.deepcopy(b);mut(x);tests.append((code,lambda x=x:validate(x,e)))
 add("VERSION_MISMATCH",lambda x:x["episode"].__setitem__("scenario_version","wrong"));add("TRANSCRIPT_HASH_MISMATCH",lambda x:x["episode"].__setitem__("transcript_hash","0"*64));add("OPPORTUNITY_ID_MISMATCH",lambda x:x["opportunities"]["items"][0].__setitem__("opportunity_id","UNKNOWN"));add("EVIDENCE_OWNER_MISMATCH",lambda x:x["opportunities"]["items"][0].__setitem__("candidate_response_message_ids",["m001"]));add("EVIDENCE_OWNER_MISMATCH",lambda x:x["rater_a"]["dimensions"][0].__setitem__("selected_evidence_message_ids",["m001"]))
 def no_opp(x):
  for i in x["opportunities"]["items"]:
   if i["dimension"]=="issue_framing":i.update(status="invalid",response_status="not_applicable",candidate_response_message_ids=[],invalidated_by=["A-PROH-01"])
  x["opportunities"]["summary"]={"offered":9,"not_offered":0,"invalid":3,"with_candidate_response":9}
 add("SCORE_WITHOUT_OPPORTUNITY",no_opp)
 def score4(x):
  x["evaluation"]["candidate_dimensions"][0].update(score=4,evidence_message_ids=["m004","m006"]);x["adjudication"]["dimension_resolutions"][0].update(final_score=4,final_evidence_message_ids=["m004","m006"])
 add("SCORE4_PHASE_DIVERSITY",score4)
 add("PROBABILITY_SUM_INVALID",lambda x:x["evaluation"]["candidate_dimensions"][0].__setitem__("question_results",[{"question_id":"IF01","probabilities":{"not_observed":.5,"partially_observed":.5,"observed":.5,"strongly_observed":0},"evidence_message_ids":["m004"]}]));add("RATER_SCORE_MISMATCH",lambda x:x["adjudication"]["dimension_resolutions"][0].__setitem__("rater_scores",[1,1]));add("UNCALIBRATED_GROUP_SCORE",lambda x:x["evaluation"]["display_groups"]["thinking"].__setitem__("score",3.0));add("SYSTEM_QUALITY_STATUS_MISMATCH",lambda x:x["system_quality"].__setitem__("status","warn"));add("FEEDBACK_RESULT_MISMATCH",lambda x:x["feedback"]["dimension_narratives"]["issue_framing"].__setitem__("positive","changed"));add("SYSTEM_QUALITY_SCOPE_MISMATCH",lambda x:x["system_quality"]["rule_results"].append({k:v for k,v in x["deterministic_rules"]["rule_results"][1].items() if k!="target"}));add("NONDETERMINISTIC_OUTPUT",lambda x:x["deterministic_rules"]["rule_results"][0].__setitem__("detail","changed"))
 for code,fn in tests:fail(code,fn)
 pre=copy.deepcopy(b["episode"]);pre["messages"].append({"message_id":"m_preempt","participant_id":"ai_a_operations","speaker_type":"ai","text":"対象と基準はこちらで決めます。","phase":"problem_definition","move":"define_scope","start_ms":38000,"end_ms":39000,"generation_id":"g_preempt"});dr=e.deterministic_rules(b["scenario"],pre);sq=e.system_quality(b["scenario"],pre,dr);r01=next(r for r in dr["rule_results"] if r["rule_id"]=="A-R01")
 if r01["outcome"]!="fail" or sq["status"]!="fail":raise AssertionError("preemptive AI scope definition was not detected")
 print("Exercise A medium vertical slice v0.1 OK");print(f"Artifacts: {len(b['manifest']['artifacts'])}");print(f"Opportunities: {len(b['opportunities']['items'])} offered");print("Raters: 2 independent + 1 adjudication");print(f"Negative vertical-slice tests: {len(tests)} passed");print("Evaluator behavior tests: 1 passed")
if __name__=="__main__":main()
