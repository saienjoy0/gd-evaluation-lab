#!/usr/bin/env python3
"""Validate Exercise A medium vertical slice and its deterministic replay."""
import copy, hashlib, importlib.util, json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"fixtures/calibration/full-episodes/ambiguous-structure/medium"
DIMS=["issue_framing","logical_reasoning","listening_and_response","valuable_contribution","collaboration_and_relationship","decision_and_consensus","process_and_time_management"]

class Err(AssertionError):
    def __init__(self,code,msg): super().__init__(f"{code}: {msg}"); self.code=code
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def evaluator():
    spec=importlib.util.spec_from_file_location("exercise_a",ROOT/"scripts/evaluate_exercise_a_medium.py")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def schema(instance,schema_doc,label):
    Draft202012Validator.check_schema(schema_doc)
    errors=sorted(Draft202012Validator(schema_doc,format_checker=FormatChecker()).iter_errors(instance),key=lambda e:list(e.absolute_path))
    if errors: raise Err("SCHEMA_INVALID",f"{label}: {list(errors[0].absolute_path)} {errors[0].message}")
def agreement(a,b):
    if a==b:return "exact"
    if "NE" in (a,b):return "ne_disagreement"
    return "adjacent" if abs(a-b)==1 else "major_disagreement"

def validate(b,e):
    m,s,ep,sq,op,ra,rb,adj,res,fb=[b[k] for k in ["manifest","scenario","episode","system_quality","opportunities","rater_a","rater_b","adjudication","evaluation","feedback"]]
    if m["scenario_ref"]["scenario_id"]!=s["scenario_id"] or m["scenario_ref"]["version"]!=s["version"] or ep["scenario_id"]!=s["scenario_id"] or ep["scenario_version"]!=s["version"]: raise Err("VERSION_MISMATCH","Scenario/Episode")
    th=e.transcript_hash(ep["messages"])
    if ep["transcript_hash"]!=th or res["version_info"]["transcript_hash"]!=th: raise Err("TRANSCRIPT_HASH_MISMATCH","hash")
    if {x["opportunity_id"] for x in s["evaluation_opportunities"]}!={x["opportunity_id"] for x in op["items"]}: raise Err("OPPORTUNITY_ID_MISMATCH","set")
    messages={x["message_id"]:x for x in ep["messages"]}; events={x["event_id"] for x in ep["events"]}
    target=res["target_participant_id"]; user={mid for mid,x in messages.items() if x["speaker_type"]=="user" and x["participant_id"]==target}
    def evidence(ids,label):
        for mid in ids:
            if mid not in user: raise Err("EVIDENCE_OWNER_MISMATCH",f"{label}:{mid}")
    for sheet in (ra,rb):
        for d in sheet["dimensions"]:
            evidence(d["selected_evidence_message_ids"],sheet["sheet_id"])
            if any(x not in events for x in d["opportunity_evidence_event_ids"]): raise Err("UNKNOWN_EVENT_ID",d["dimension"])
    for d in adj["dimension_resolutions"]: evidence(d["final_evidence_message_ids"],"adjudication")
    for d in res["candidate_dimensions"]:
        evidence(d["evidence_message_ids"],"evaluation")
        for q in d["question_results"]:
            evidence(q["evidence_message_ids"],"question")
            if abs(sum(q["probabilities"].values())-1)>1e-6: raise Err("PROBABILITY_SUM_INVALID",d["dimension"])
    bydim={d:[] for d in DIMS}
    for x in op["items"]: bydim[x["dimension"]].append(x)
    for sheet in (ra,rb):
        for d in sheet["dimensions"]:
            if not any(x["status"]=="offered" for x in bydim[d["dimension"]]) and d["score"]!="NE": raise Err("SCORE_WITHOUT_OPPORTUNITY",d["dimension"])
    if ra["annotator_id"]==rb["annotator_id"]: raise Err("DUPLICATE_RATER","id")
    if adj["adjudicator_id"] in {ra["annotator_id"],rb["annotator_id"]}: raise Err("ADJUDICATOR_OVERLAP","id")
    maps=[{x["dimension"]:x["score"] for x in y["dimensions"]} for y in (ra,rb)]
    amap={}
    for d in adj["dimension_resolutions"]:
        scores=[maps[0][d["dimension"]],maps[1][d["dimension"]]]
        if d["rater_scores"]!=scores: raise Err("RATER_SCORE_MISMATCH",d["dimension"])
        if d["agreement_class"]!=agreement(*scores): raise Err("AGREEMENT_CLASS_MISMATCH",d["dimension"])
        amap[d["dimension"]]=d
    for d in res["candidate_dimensions"]:
        a=amap[d["dimension"]]
        if d["score"]!=a["final_score"] or d["evidence_message_ids"]!=a["final_evidence_message_ids"]: raise Err("FINAL_RESULT_MISMATCH",d["dimension"])
        if d["score"]==4 and len({messages[x]["phase"] for x in d["evidence_message_ids"]})<2: raise Err("SCORE4_PHASE_DIVERSITY",d["dimension"])
    if any(g["aggregation_status"]=="not_calibrated" and g["score"] is not None for g in res["display_groups"].values()): raise Err("UNCALIBRATED_GROUP_SCORE","score")
    if res["display_groups"]!=fb["display_groups"]: raise Err("FEEDBACK_RESULT_MISMATCH","groups")
    if sq["status"]!=res["ai_quality"]["status"] or sq["dimension_scores"]!=res["ai_quality"]["dimension_scores"]: raise Err("SYSTEM_QUALITY_MISMATCH","result")
    generated={"system_quality":e.system_quality(s,ep),"opportunity_resolution":e.opportunities(s,ep)}
    generated["evaluation_result"]=e.evaluation(ep,generated["system_quality"],adj,fb)
    if generated["system_quality"]!=sq or generated["opportunity_resolution"]!=op or generated["evaluation_result"]!=res or e.system_quality(s,ep)!=generated["system_quality"]: raise Err("NONDETERMINISTIC_OUTPUT","golden")

def fail(code,fn):
    try: fn()
    except Err as x:
        if x.code!=code: raise AssertionError(f"expected {code}, got {x.code}")
        return
    raise AssertionError(f"{code} unexpectedly passed")

def main():
    e=evaluator()
    b={
      "manifest":load(BASE/"manifest.json"),
      "scenario":load(ROOT/"fixtures/scenarios/candidate-assessment-a-ambiguous-structure-v0.1.json"),
      "episode":load(BASE/"episode.json"),"system_quality":load(BASE/"system-quality-result.json"),
      "opportunities":load(BASE/"opportunity-resolution.json"),"rater_a":load(BASE/"rater-sheet-a.json"),
      "rater_b":load(BASE/"rater-sheet-b.json"),"adjudication":load(BASE/"adjudication.json"),
      "evaluation":load(BASE/"evaluation-result.json"),"feedback":load(BASE/"expected-feedback.json")}
    docs={"manifest":"vertical-slice-manifest-v0.1.schema.json","episode":"episode-v0.1.schema.json","system_quality":"system-quality-result-v0.1.schema.json","opportunities":"opportunity-resolution-v0.1.schema.json","rater_a":"rater-sheet-v0.1.schema.json","rater_b":"rater-sheet-v0.1.schema.json","adjudication":"adjudication-v0.1.schema.json","evaluation":"evaluation-result-v0.1.schema.json"}
    for key,name in docs.items(): schema(b[key],load(ROOT/"schemas"/name),key)
    for name,a in b["manifest"]["artifacts"].items():
        path=ROOT/a["path"]
        if not path.is_file(): raise Err("MANIFEST_PATH_MISSING",name)
        if sha(path)!=a["sha256"]: raise Err("MANIFEST_HASH_MISMATCH",name)
    validate(b,e)
    tests=[]
    x=copy.deepcopy(b);x["episode"]["scenario_version"]="wrong";tests.append(("VERSION_MISMATCH",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["episode"]["transcript_hash"]="0"*64;tests.append(("TRANSCRIPT_HASH_MISMATCH",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["opportunities"]["items"][0]["opportunity_id"]="UNKNOWN";tests.append(("OPPORTUNITY_ID_MISMATCH",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["rater_a"]["dimensions"][0]["selected_evidence_message_ids"]=["m001"];tests.append(("EVIDENCE_OWNER_MISMATCH",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b)
    for i in x["opportunities"]["items"]:
        if i["dimension"]=="issue_framing":i["status"]="invalid";i["response_status"]="not_applicable"
    tests.append(("SCORE_WITHOUT_OPPORTUNITY",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["evaluation"]["candidate_dimensions"][0]["score"]=4;x["evaluation"]["candidate_dimensions"][0]["evidence_message_ids"]=["m004","m006"];x["adjudication"]["dimension_resolutions"][0]["final_score"]=4;x["adjudication"]["dimension_resolutions"][0]["final_evidence_message_ids"]=["m004","m006"];tests.append(("SCORE4_PHASE_DIVERSITY",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["evaluation"]["candidate_dimensions"][0]["question_results"]=[{"question_id":"IF01","probabilities":{"not_observed":.5,"partially_observed":.5,"observed":.5,"strongly_observed":0},"evidence_message_ids":["m004"]}];tests.append(("PROBABILITY_SUM_INVALID",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["adjudication"]["dimension_resolutions"][0]["rater_scores"]=[1,1];tests.append(("RATER_SCORE_MISMATCH",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["evaluation"]["display_groups"]["thinking"]["score"]=3.0;tests.append(("UNCALIBRATED_GROUP_SCORE",lambda x=x:validate(x,e)))
    x=copy.deepcopy(b);x["system_quality"]["rule_results"][0]["detail"]="changed";tests.append(("NONDETERMINISTIC_OUTPUT",lambda x=x:validate(x,e)))
    for code,fn in tests: fail(code,fn)
    print("Exercise A medium vertical slice v0.1 OK")
    print(f"Artifacts: {len(b['manifest']['artifacts'])}")
    print(f"Opportunities: {len(b['opportunities']['items'])} offered")
    print("Raters: 2 independent + 1 adjudication")
    print(f"Negative vertical-slice tests: {len(tests)} passed")
if __name__=="__main__":main()
