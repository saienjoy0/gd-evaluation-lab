#!/usr/bin/env python3
"""Regenerate Exercise A medium vertical-slice outputs without an LLM."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
NARRATIVES={
"issue_framing":{"positive":"対象、時間帯、比較基準を明確にした。","missing":"目的と制約の優先順位付けは弱い。","improvement":"最初に目的、対象、制約、判断基準の順で整理する。"},
"logical_reasoning":{"positive":"案の利点と運用負荷を比較した。","missing":"主張を支える定量根拠が少ない。","improvement":"基準ごとに根拠と不確実性を明示する。"},
"listening_and_response":{"positive":"騒音と動線の懸念へ直接応答して案を修正した。","missing":"相手の主張を要約して確認する行動は少ない。","improvement":"懸念を一度言い換えてから修正案を返す。"},
"valuable_contribution":{"positive":"時間帯分離と可動机の案を具体化した。","missing":"新しい分析や代替案の広がりは限定的だった。","improvement":"少なくとも二案を改善し、比較可能な形にする。"},
"collaboration_and_relationship":{"positive":"対立するニーズを否定せず条件付きで統合した。","missing":"発言機会の偏りを調整する行動はなかった。","improvement":"未発言者や異なる立場へ明示的に意見を求める。"},
"decision_and_consensus":{"positive":"成功指標と実証条件を含む結論を提示した。","missing":"結論の弱点と撤退条件は十分に明示していない。","improvement":"合意時にリスク、例外、撤退条件も確認する。"},
"process_and_time_management":{"positive":"最後に見直し時点を含めて要約した。","missing":"途中の時間・進捗調整が少ない。","improvement":"中盤で残り時間と未解決論点を確認する。"}}
GROUPS={
"thinking":{"aggregation_status":"not_calibrated","score":None,"coverage":{"evaluated":3,"total":3},"bottleneck_dimension":"logical_reasoning","summary":"枠組みは作れたが、比較を支える根拠の明示が弱かった。"},
"collaboration":{"aggregation_status":"not_calibrated","score":None,"coverage":{"evaluated":2,"total":2},"bottleneck_dimension":"collaboration_and_relationship","summary":"懸念へ応答して統合できたが、参加促進は限定的だった。"},
"progress":{"aggregation_status":"not_calibrated","score":None,"coverage":{"evaluated":2,"total":2},"bottleneck_dimension":"process_and_time_management","summary":"条件付きの合意は作れたが、途中の進捗管理が不足した。"}}
def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def transcript_hash(messages):return hashlib.sha256(json.dumps(messages,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def target(episode):
 ids=[p["participant_id"] for p in episode["participants"] if p["speaker_type"]=="user"]
 if len(ids)!=1:raise ValueError("exactly one target user required")
 return ids[0]
def deterministic_rules(scenario,episode):
 msgs=sorted(episode["messages"],key=lambda m:m["start_ms"]); byid={m["message_id"]:m for m in msgs}; uid=target(episode)
 user=[m for m in msgs if m["speaker_type"]=="user" and m["participant_id"]==uid]
 structure=[m for m in user if m["phase"]=="problem_definition" and m["move"] in {"clarify_goal","define_scope","define_criteria"}]
 ctx=[e for e in episode["events"] if e["event"]=="CONTEXT_RESOLVED"]
 concerns=[e for e in episode["events"] if e["event"]=="PRIVATE_CONCERN_REVEALED"]
 summaries=[e for e in episode["events"] if e["event"]=="SUMMARY_FIELDS_RECORDED"]
 rubrics={r["rubric_id"]:r for r in scenario["instance_rubrics"]}; p=rubrics["A-R01"]["rule"]["params"]
 preempt=[m for m in msgs if m["speaker_type"]=="ai" and m["move"] in set(p["actions"]) and sum(u["end_ms"]<=m["start_ms"] for u in user)<p["minimum_user_messages"]]
 valid_concerns=bool(concerns) and all(e.get("trigger_move") in {"ask_question","compare_options","challenge"} and e.get("message_id") in byid and byid[e["message_id"]]["speaker_type"]=="ai" for e in concerns)
 resolved={e.get("key") for e in ctx}; fields={f for e in summaries for f in e.get("fields",[])}; distinct={m["move"] for m in structure}
 checks={
 "A-R01":(not preempt,[m["message_id"] for m in structure],[],"AIが対象・基準を先に確定せず、利用者が先に定義した。"),
 "A-R02":(len(resolved&{"priority_target","success_metric","usage_hours"})>=2,[e["message_id"] for e in ctx],[e["event_id"] for e in ctx],"三つの文脈キーが解消された。"),
 "A-R03":(len(distinct)>=rubrics["A-R03"]["rule"]["params"]["minimum_distinct_moves"],[m["message_id"] for m in structure],[],"利用者が課題設定に必要な3種類のmoveを実行した。"),
 "A-R04":(valid_concerns,[e["message_id"] for e in concerns],[e["event_id"] for e in concerns],"非公開懸念は質問・比較後に開示された。"),
 "A-R05":({"success_metric","pilot_condition"}<=fields,[e["message_id"] for e in summaries],[e["event_id"] for e in summaries],"要約に成功指標と実証見直し条件が含まれる。")}
 results=[]
 for rid,(ok,mids,eids,detail) in checks.items():
  r=rubrics[rid]; results.append({"rule_id":rid,"target":r["target"],"outcome":"pass" if ok else "fail","severity":r["severity"],"evidence_message_ids":mids,"evidence_event_ids":eids,"affected_dimensions":r["affected_dimensions"],"detail":detail if ok else "決定論的条件を満たさなかった。"})
 return {"contract_version":"0.1","result_id":f"dr-{episode['session_id']}","session_id":episode["session_id"],"scenario_id":episode["scenario_id"],"scenario_version":episode["scenario_version"],"evaluator_version":"exercise-a-deterministic-v0.1","rule_results":results}
def system_quality(scenario,episode,rule_result=None):
 rule_result=rule_result or deterministic_rules(scenario,episode); conditions={c["condition_id"]:c for c in scenario["prohibited_conditions"]}
 results=[{k:v for k,v in r.items() if k!="target"} for r in rule_result["rule_results"] if r["target"]=="ai_system"]
 events=[e for e in episode["events"] if e["event"]=="PROHIBITED_CONDITION_TRIGGERED"]; concerns=[e for e in episode["events"] if e["event"]=="PRIVATE_CONCERN_REVEALED"]
 for cid in ["A-PROH-01","A-PROH-02"]:
  c=conditions[cid]; bad=any(e.get("condition_id")==cid for e in events); mids=[e["message_id"] for e in concerns] if cid=="A-PROH-02" else []; eids=[e["event_id"] for e in concerns] if cid=="A-PROH-02" else [e["event_id"] for e in events if e.get("condition_id")==cid]
  detail="triggerなしの非公開懸念開示は観察されない。" if cid=="A-PROH-02" else "AIによる先回りの課題定義は観察されない。"
  results.append({"rule_id":cid,"outcome":"fail" if bad else "pass","severity":c["severity"],"evidence_message_ids":mids,"evidence_event_ids":eids,"affected_dimensions":c["affected_dimensions"],"detail":detail if not bad else "禁止条件が発生した。"})
 failed=[r for r in results if r["outcome"]=="fail"]; status="fail" if any(r["severity"]=="critical" for r in failed) else "warn" if failed else "pass"
 r01=next(r for r in results if r["rule_id"]=="A-R01")["outcome"]=="pass"
 scores={"goal_progression":4,"responsiveness":4,"user_agency":5 if r01 else 2,"role_believability":4,"discussion_coherence":4,"novelty_and_repetition":4,"consensus_quality":4,"natural_pacing":4}
 return {"contract_version":"0.1","result_id":f"sq-{episode['session_id']}","session_id":episode["session_id"],"scenario_id":episode["scenario_id"],"scenario_version":episode["scenario_version"],"evaluator_version":"exercise-a-deterministic-v0.1","status":status,"rule_results":results,"dimension_scores":scores}
def opportunities(scenario,episode):
 uid=target(episode); messages={m["message_id"]:m for m in episode["messages"]}; valid={mid for mid,m in messages.items() if m["speaker_type"]=="user" and m["participant_id"]==uid}; offers={}; invalid={}
 for e in episode["events"]:
  if e["event"]=="OPPORTUNITY_OFFERED":offers.setdefault(e.get("opportunity_id"),[]).append(e)
  if e["event"]=="PROHIBITED_CONDITION_TRIGGERED":invalid.setdefault(e.get("condition_id"),[]).append(e)
 items=[]
 for o in scenario["evaluation_opportunities"]:
  evs=offers.get(o["opportunity_id"],[]); bad=[c for c in o.get("invalidated_by",[]) if c in invalid]; response=list(dict.fromkeys(mid for e in evs for mid in e.get("candidate_response_message_ids",[]) if mid in valid))
  if bad:status,rs,response,detail="invalid","not_applicable",[],"禁止条件により評価機会が無効化された。"
  elif evs:status,rs,detail="offered","observed" if response else "not_observed","構造化イベントと利用者応答を確認した。" if response else "評価機会は提供されたが利用者応答は観察されない。"
  else:status,rs,detail="not_offered","not_applicable","対応する評価機会イベントが存在しない。"
  items.append({"opportunity_id":o["opportunity_id"],"dimension":o["dimension"],"status":status,"trigger_event_ids":[e["event_id"] for e in evs],"candidate_response_message_ids":response,"invalidated_by":bad,"response_status":rs,"detail":detail})
 return {"contract_version":"0.1","resolution_id":f"or-{episode['session_id']}","session_id":episode["session_id"],"scenario_id":episode["scenario_id"],"scenario_version":episode["scenario_version"],"target_participant_id":uid,"resolver_version":"opportunity-resolver-v0.1","items":items,"summary":{"offered":sum(i["status"]=="offered" for i in items),"not_offered":sum(i["status"]=="not_offered" for i in items),"invalid":sum(i["status"]=="invalid" for i in items),"with_candidate_response":sum(i["response_status"]=="observed" for i in items)}}
def evaluation(episode,sq,adj):
 dims=[]
 for r in adj["dimension_resolutions"]:
  n=NARRATIVES[r["dimension"]]; ne=r["final_score"]=="NE"; dims.append({"dimension":r["dimension"],"score":r["final_score"],"confidence":0 if ne else .9,"evidence_message_ids":r["final_evidence_message_ids"],"positive_behavior":"" if ne else n["positive"],"missing_behavior":"" if ne else n["missing"],"improvement":"" if ne else n["improvement"],"not_evaluable_reason":{"code":r["not_evaluable_reason"],"detail":r["resolution_reason"]} if ne else None,"question_results":[]})
 violations=[{"rule_id":r["rule_id"],"severity":r["severity"],"message_ids":r["evidence_message_ids"],"affected_candidate_dimensions":r["affected_dimensions"]} for r in sq["rule_results"] if r["outcome"]=="fail"]
 return {"contract_version":"0.1","session_id":episode["session_id"],"target_participant_id":target(episode),"status":"completed" if all(r["final_score"]!="NE" for r in adj["dimension_resolutions"]) else "partial","ai_quality":{"status":sq["status"],"violations":violations,"dimension_scores":sq["dimension_scores"]},"candidate_dimensions":dims,"display_groups":GROUPS,"version_info":{"rubric_version":"candidate-behavior-v0.1","ai_quality_rubric_version":"ai-participant-v0.1","scenario_version":episode["scenario_version"],"orchestrator_version":episode["versions"]["orchestrator_version"],"prompt_version":episode["versions"]["prompt_version"],"judge_model":"human-adjudication","judge_version":"not-applied-v0.1","deterministic_evaluator_version":"exercise-a-deterministic-v0.1","transcript_hash":episode["transcript_hash"]},"review_status":"completed","legacy_evaluation":None,"evaluation_disagreement":None}
def feedback(result):return {"contract_version":"0.1","slice_id":"exercise-a-medium-v0.1","dimension_narratives":{d["dimension"]:{"positive":d["positive_behavior"],"missing":d["missing_behavior"],"improvement":d["improvement"]} for d in result["candidate_dimensions"]},"display_groups":result["display_groups"],"strengths":["曖昧なテーマへ対象と比較基準を設定した","複数の懸念を実施条件へ反映した"],"next_action":"中盤で残り時間と未解決論点を確認し、根拠付きで優先順位を付ける。","limitations":"合成Episodeに基づく校正用フィードバックであり、採用判断には使用しない。"}
def build(repo=ROOT):
 base=repo/"fixtures/calibration/full-episodes/ambiguous-structure/medium"; scenario=load(repo/"fixtures/scenarios/candidate-assessment-a-ambiguous-structure-v0.1.json"); episode=load(base/"episode.json"); adj=load(base/"adjudication.json"); dr=deterministic_rules(scenario,episode); sq=system_quality(scenario,episode,dr); op=opportunities(scenario,episode); result=evaluation(episode,sq,adj)
 return {"deterministic_rules":dr,"system_quality":sq,"opportunity_resolution":op,"evaluation_result":result,"feedback":feedback(result)}
if __name__=="__main__":print(json.dumps(build(),ensure_ascii=False,indent=2,sort_keys=True))
