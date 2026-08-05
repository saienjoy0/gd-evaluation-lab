#!/usr/bin/env python3
"""Validate Exercise C medium vertical slice and fail-closed behavior."""
from __future__ import annotations
import copy,json,sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
CASE_DIR=ROOT/'fixtures/calibration/full-episodes/time-boxed-decision/medium'
from gd_eval.opportunities.resolver import OpportunityResolutionError, resolve_opportunities  # noqa:E402
from gd_eval.quality.system_quality import build_system_quality  # noqa:E402
from gd_eval.rules.registry import evaluate_deterministic_rules  # noqa:E402
from gd_eval.vertical_slice.loader import load_case  # noqa:E402
from gd_eval.vertical_slice.manifest import build_manifest, validate_manifest  # noqa:E402
from gd_eval.vertical_slice.runner import compare_oracles, run_full_episode  # noqa:E402
EXPECTED={'issue_framing':2,'logical_reasoning':3,'listening_and_response':3,'valuable_contribution':2,'collaboration_and_relationship':2,'decision_and_consensus':3,'process_and_time_management':3}
SUMMARY={'offered':15,'not_offered':0,'invalid':0,'with_candidate_response':15}

def schema(value,name):
    raw=json.loads((ROOT/'schemas'/name).read_text()); Draft202012Validator.check_schema(raw)
    errors=sorted(Draft202012Validator(raw,format_checker=FormatChecker()).iter_errors(value),key=lambda e:list(e.absolute_path))
    if errors: raise AssertionError(f'SCHEMA_INVALID:{name}:{list(errors[0].absolute_path)}:{errors[0].message}')
def outcomes(result): return {x['rule_id']:x['outcome'] for x in result['rule_results']}
def scores(result): return {x['dimension']:x['score'] for x in result['candidate_dimensions']}
def event(ep,eid): return next(x for x in ep['events'] if x['event_id']==eid)
def message(ep,mid): return next(x for x in ep['messages'] if x['message_id']==mid)
def mutate_rule(runtime,fn):
    r=copy.deepcopy(runtime); fn(r.episode)
    return outcomes(evaluate_deterministic_rules(r.scenario,r.episode,r.target_participant_id,r.versions['deterministic_evaluator_version']))
def expect_rule(runtime,rid,fn):
    got=mutate_rule(runtime,fn)
    if got.get(rid)!='fail': raise AssertionError(f'EXPECTED_RULE_FAILURE_NOT_RAISED:{rid}:{got}')
def expect_opp(runtime,sq,fn,text):
    r=copy.deepcopy(runtime); fn(r.episode)
    try: resolve_opportunities(r.scenario,r.episode,sq,r.target_participant_id,r.versions['opportunity_resolver_version'])
    except OpportunityResolutionError as exc:
        if text not in str(exc): raise AssertionError(f'WRONG_OPPORTUNITY_FAILURE:{text}:{exc}') from exc
        return
    raise AssertionError(f'EXPECTED_OPPORTUNITY_FAILURE_NOT_RAISED:{text}')
def quality_for(runtime):
    dr=evaluate_deterministic_rules(runtime.scenario,runtime.episode,runtime.target_participant_id,runtime.versions['deterministic_evaluator_version'])
    return build_system_quality(runtime.scenario,runtime.episode,dr,runtime.target_participant_id,runtime.versions['deterministic_evaluator_version'])

def main()->None:
    loaded=load_case(CASE_DIR,ROOT); generated=run_full_episode(loaded.runtime); compare_oracles(generated,loaded.oracle_paths)
    if run_full_episode(loaded.runtime)!=generated: raise AssertionError('NONDETERMINISTIC_EXERCISE_C_MEDIUM_OUTPUT')
    manifest=build_manifest(loaded.profile,loaded.runtime,generated,loaded.oracle_paths); validate_manifest(manifest)
    for value,name in [(generated.deterministic_rules,'deterministic-rule-result-v0.1.schema.json'),(generated.system_quality,'system-quality-result-v0.1.schema.json'),(generated.opportunity_resolution,'opportunity-resolution-v0.1.schema.json'),(generated.evaluation_result,'evaluation-result-v0.1.schema.json'),(manifest,'full-episode-manifest-v0.1.schema.json')]: schema(value,name)
    if loaded.profile.state!='medium' or loaded.profile.exercise_id!='candidate-assessment-c-time-boxed-decision': raise AssertionError('EXERCISE_C_PROFILE_INVALID')
    if outcomes(generated.deterministic_rules)!={'C-R01':'pass','C-R02':'pass','C-R03':'pass','C-R04':'pass','C-R05':'pass'}: raise AssertionError(f'C_RULE_PROFILE_INVALID:{outcomes(generated.deterministic_rules)}')
    if generated.system_quality['status']!='pass': raise AssertionError('EXERCISE_C_SYSTEM_QUALITY_NOT_PASS')
    if outcomes(generated.system_quality)!={'C-R01':'pass','C-R02':'pass','C-PROH-01':'pass','C-PROH-02':'pass'}: raise AssertionError(f'C_QUALITY_PROFILE_INVALID:{outcomes(generated.system_quality)}')
    if generated.opportunity_resolution['summary']!=SUMMARY: raise AssertionError(f'EXERCISE_C_OPPORTUNITY_SUMMARY_INVALID:{generated.opportunity_resolution["summary"]}')
    if any(i['status']!='offered' or i['response_status']!='observed' or not i['candidate_response_message_ids'] for i in generated.opportunity_resolution['items']): raise AssertionError('EXERCISE_C_OPPORTUNITY_NOT_FULLY_OBSERVED')
    if scores(generated.evaluation_result)!=EXPECTED or generated.evaluation_result['status']!='completed': raise AssertionError(f'EXERCISE_C_SCORE_PROFILE_INVALID:{scores(generated.evaluation_result)}')
    ep=loaded.runtime.episode
    if event(ep,'ev_checkpoint_40')['timestamp_ms']!=290000 or event(ep,'ev_checkpoint_75')['timestamp_ms']!=544000: raise AssertionError('CHECKPOINT_TIMING_INVALID')
    if message(ep,'m018')['move']!='prioritize' or message(ep,'m032')['move']!='prioritize': raise AssertionError('CHECKPOINT_PRIORITY_RESPONSE_INVALID')
    if event(ep,'ev_late_risk_security')['timestamp_ms']>=message(ep,'m033')['start_ms']: raise AssertionError('LATE_RISK_AFTER_DECISION')
    if message(ep,'m028')['start_ms']<event(ep,'ev_late_risk_security')['timestamp_ms']: raise AssertionError('REVISION_BEFORE_RISK')
    summary=event(ep,'ev_summary')
    if any(not summary.get(k) for k in ('mode','exception','next_check')): raise AssertionError('SUMMARY_VALUE_MISSING')
    expect_rule(loaded.runtime,'C-R01',lambda e:e['events'].remove(event(e,'ev_checkpoint_40')))
    expect_rule(loaded.runtime,'C-R01',lambda e:e['events'].remove(event(e,'ev_checkpoint_75')))
    expect_rule(loaded.runtime,'C-R01',lambda e:event(e,'ev_checkpoint_40').update(timestamp_ms=100000))
    expect_rule(loaded.runtime,'C-R02',lambda e:event(e,'ev_late_risk_security').update(timestamp_ms=590000))
    expect_rule(loaded.runtime,'C-R02',lambda e:event(e,'ev_late_risk_security').update(concern='wrong'))
    expect_rule(loaded.runtime,'C-R03',lambda e:message(e,'m018').update(move='propose_idea'))
    expect_rule(loaded.runtime,'C-R03',lambda e:[e['events'].remove(event(e,x)) for x in ('ev_priority_40','ev_priority_75')])
    expect_rule(loaded.runtime,'C-R04',lambda e:event(e,'ev_options_compared')['options'].remove('オンライン'))
    expect_rule(loaded.runtime,'C-R04',lambda e:e['events'].remove(event(e,'ev_revision')))
    expect_rule(loaded.runtime,'C-R04',lambda e:message(e,'m028').update(start_ms=470000))
    for field in ('mode','exception','next_check'):
        expect_rule(loaded.runtime,'C-R05',lambda e,f=field:event(e,'ev_summary_fields')['fields'].remove(f))
    q=copy.deepcopy(loaded.runtime); message(q.episode,'m015').update(move='propose_decision'); sq=quality_for(q)
    if outcomes(sq).get('C-PROH-01')!='fail': raise AssertionError('C_PROH_01_NEGATIVE_NOT_CAUGHT')
    q=copy.deepcopy(loaded.runtime); q.episode['messages'].remove(message(q.episode,'m039')); sq=quality_for(q)
    if outcomes(sq).get('C-PROH-02')!='fail': raise AssertionError('C_PROH_02_NEGATIVE_NOT_CAUGHT')
    expect_opp(loaded.runtime,generated.system_quality,lambda e:event(e,'ev_opp_c_op_li_01').update(timestamp_ms=130000),'OPPORTUNITY_RESPONSE_BEFORE_TRIGGER')
    expect_opp(loaded.runtime,generated.system_quality,lambda e:event(e,'ev_opp_c_op_li_01').update(candidate_response_message_ids=['m007']),'EVIDENCE_OWNER_MISMATCH')
    print('Exercise C medium vertical slice v0.1 OK')
    print('Rules C-R01..C-R05, System Quality, 15 opportunities, 2/3/3/2/2/3/3')
    print('Negative tests: 17 passed')
if __name__=='__main__': main()
