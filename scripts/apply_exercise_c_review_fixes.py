#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def patch_scenario() -> None:
    path = ROOT / "fixtures/scenarios/candidate-assessment-c-time-boxed-decision-v0.1.json"
    scenario = json.loads(path.read_text(encoding="utf-8"))
    opportunities = {item["opportunity_id"]: item for item in scenario["evaluation_opportunities"]}
    opportunities["C-OP-VA-01"]["trigger"] = "after_training_initial_positions"
    rubrics = {item["rubric_id"]: item for item in scenario["instance_rubrics"]}
    rubrics["C-R02"]["rule"]["params"]["allowed_trigger_moves"] = ["ask_question"]
    rubrics["C-R05"]["rule"]["deterministic_rule_id"] = "candidate_summary_contains_fields"
    path.write_text(json.dumps(scenario, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def patch_episode() -> None:
    path = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision/medium/episode.json"
    episode = json.loads(path.read_text(encoding="utf-8"))
    events = {item["event_id"]: item for item in episode["events"]}
    for event_id, message_id, timestamp_ms in [
        ("ev_options_presented", "m003", 44000),
        ("ev_success_requirements", "m004", 56000),
        ("ev_collision", "m021", 370000),
        ("ev_revision", "m028", 500000),
        ("ev_unresolved", "m030", 535000),
    ]:
        events[event_id]["message_id"] = message_id
        events[event_id]["timestamp_ms"] = timestamp_ms
    path.write_text(json.dumps(episode, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def patch_rules() -> None:
    path = ROOT / "gd_eval/rules/time_boxed_decision.py"
    source = path.read_text(encoding="utf-8")
    old = '''            triggered = any(
                prior.get("speaker_type") == "user"
                and prior.get("participant_id") == target
                and prior.get("move") == trigger_move
                and prior.get("end_ms", 0) <= message.get("start_ms", 0)
                for prior in messages
            )'''
    new = '''            triggered = any(
                prior.get("move") == trigger_move
                and prior.get("end_ms", 0) <= message.get("start_ms", 0)
                and prior.get("message_id") != message.get("message_id")
                for prior in messages
            )'''
    if old in source:
        source = source.replace(old, new)
    path.write_text(source, encoding="utf-8")


def patch_checker() -> None:
    path = ROOT / "scripts/check_exercise_c_medium.py"
    source = path.read_text(encoding="utf-8")
    source = source.replace("from pathlib import Path\n", "from dataclasses import replace\nfrom pathlib import Path\n")
    source = source.replace("from materialize_exercise_c_medium_episode import main as materialize_episode  # noqa: E402\n", "")
    source = source.replace("    materialize_episode()\n", "")
    import_anchor = "from gd_eval.quality.system_quality import build_system_quality  # noqa: E402\n"
    imports = '''from gd_eval.opportunities.stakeholder_conflict import (  # noqa: E402
    CONTEXT_HANDLERS as STAKEHOLDER_CONTEXT_HANDLERS,
    TRIGGER_HANDLERS as STAKEHOLDER_TRIGGER_HANDLERS,
)
from gd_eval.opportunities.time_boxed_decision import (  # noqa: E402
    CONTEXT_HANDLERS as TIME_CONTEXT_HANDLERS,
    TRIGGER_HANDLERS as TIME_TRIGGER_HANDLERS,
)
'''
    if imports not in source:
        source = source.replace(import_anchor, imports + import_anchor)
    helper_anchor = "\ndef quality_for(runtime) -> dict:\n"
    helper = '''
def expect_scenario_opportunity_failure(runtime, system_quality: dict, mutator: Callable[[dict], None], expected: str) -> None:
    scenario = json.loads(json.dumps(runtime.scenario))
    mutator(scenario)
    mutated = replace(runtime, scenario=scenario)
    try:
        resolve_opportunities(mutated.scenario, mutated.episode, system_quality, mutated.target_participant_id, mutated.versions["opportunity_resolver_version"])
    except OpportunityResolutionError as exc:
        if expected not in str(exc):
            raise AssertionError(f"WRONG_OPPORTUNITY_FAILURE: expected {expected}, got {exc}") from exc
        return
    raise AssertionError(f"EXPECTED_OPPORTUNITY_FAILURE_NOT_RAISED: {expected}")

'''
    if helper not in source:
        source = source.replace(helper_anchor, "\n" + helper + "def quality_for(runtime) -> dict:\n")
    normal_anchor = "    deterministic = rule_outcomes(generated.deterministic_rules)\n"
    normal = '''    generic_triggers = {"after_initial_positions", "after_goal_question", "before_idea_generation", "after_two_options_present", "after_constraint_reveal", "after_ai_question", "after_private_concern_reveal", "after_initial_ideas", "after_tradeoff_identified", "after_position_conflict", "before_final_selection", "before_session_close"}
    generic_contexts = {"priority_target_undefined", "success_metric_undefined", "scope_boundaries_undefined", "two_options_available", "constraint_requires_tradeoff", "ai_question_open", "concern_requires_response", "idea_space_open", "improvement_possible", "multiple_positions_active", "criteria_and_options_available", "remaining_time_visible"}
    if set(TIME_TRIGGER_HANDLERS) & (set(STAKEHOLDER_TRIGGER_HANDLERS) | generic_triggers):
        raise AssertionError("EXERCISE_C_TRIGGER_NAMESPACE_COLLISION")
    if set(TIME_CONTEXT_HANDLERS) & (set(STAKEHOLDER_CONTEXT_HANDLERS) | generic_contexts):
        raise AssertionError("EXERCISE_C_CONTEXT_NAMESPACE_COLLISION")
    scenario_opportunities = {item["opportunity_id"]: item for item in loaded.runtime.scenario["evaluation_opportunities"]}
    if scenario_opportunities["C-OP-VA-01"]["trigger"] != "after_training_initial_positions":
        raise AssertionError("EXERCISE_C_INITIAL_POSITION_TRIGGER_NOT_NAMESPACED")
    scenario_rubrics = {item["rubric_id"]: item for item in loaded.runtime.scenario["instance_rubrics"]}
    if scenario_rubrics["C-R02"]["rule"]["params"].get("allowed_trigger_moves") != ["ask_question"]:
        raise AssertionError("EXERCISE_C_RISK_TRIGGER_CONTRACT_INVALID")
    if scenario_rubrics["C-R05"]["rule"]["deterministic_rule_id"] != "candidate_summary_contains_fields":
        raise AssertionError("EXERCISE_C_SUMMARY_RULE_NOT_EVIDENCE_BOUND")

'''
    if normal not in source:
        source = source.replace(normal_anchor, normal + normal_anchor)
    summary_anchor = '    summary = event(episode, "ev_summary")\n'
    bindings = '''    for event_id, message_id in {"ev_options_presented": "m003", "ev_success_requirements": "m004", "ev_collision": "m021", "ev_revision": "m028", "ev_unresolved": "m030", "ev_summary": "m039", "ev_summary_fields": "m039"}.items():
        linked_event = event(episode, event_id)
        linked_message = message(episode, message_id)
        if linked_event.get("message_id") != message_id:
            raise AssertionError(f"EVENT_MESSAGE_BINDING_INVALID:{event_id}")
        if not linked_message["start_ms"] <= linked_event["timestamp_ms"] <= linked_message["end_ms"]:
            raise AssertionError(f"EVENT_TIMESTAMP_PROVENANCE_INVALID:{event_id}")

'''
    if bindings not in source:
        source = source.replace(summary_anchor, bindings + summary_anchor)
    negative_anchor = '    print("Exercise C medium vertical slice v0.1 OK")\n'
    negatives = '''    expect_rule_failure(loaded.runtime, "C-R01", lambda item: event(item, "ev_checkpoint_40").update(message_id="m016"))
    expect_rule_failure(loaded.runtime, "C-R01", lambda item: message(item, "m018").update(start_ms=400000, end_ms=410000))
    expect_rule_failure(loaded.runtime, "C-R02", lambda item: event(item, "ev_late_risk_security").update(message_id="m025"))
    expect_rule_failure(loaded.runtime, "C-R02", lambda item: event(item, "ev_late_risk_security").update(trigger_move="unknown_move"))
    expect_rule_failure(loaded.runtime, "C-R03", lambda item: event(item, "ev_priority_40").update(timestamp_ms=400000))
    expect_rule_failure(loaded.runtime, "C-R04", lambda item: event(item, "ev_options_compared").update(message_id="m019"))
    expect_rule_failure(loaded.runtime, "C-R04", lambda item: event(item, "ev_revision").update(before_message_id="m026"))
    expect_rule_failure(loaded.runtime, "C-R05", lambda item: event(item, "ev_summary_fields").update(message_id="m027"))
    expect_rule_failure(loaded.runtime, "C-R05", lambda item: event(item, "ev_summary").update(next_check=""))
    mutated = json.loads(json.dumps(loaded.runtime.episode))
    event(mutated, "ev_session_closed").update(timestamp_ms=650000)
    quality_runtime = replace(loaded.runtime, episode=mutated)
    if rule_outcomes(quality_for(quality_runtime)).get("C-PROH-02") != "fail":
        raise AssertionError("C_PROH_02_EARLY_CLOSE_NOT_CAUGHT")
    expect_scenario_opportunity_failure(loaded.runtime, generated.system_quality, lambda scenario: next(item for item in scenario["evaluation_opportunities"] if item["opportunity_id"] == "C-OP-IS-01").update(trigger="unknown_trigger"), "UNIMPLEMENTED_OPPORTUNITY_TRIGGER")
    expect_scenario_opportunity_failure(loaded.runtime, generated.system_quality, lambda scenario: next(item for item in scenario["evaluation_opportunities"] if item["opportunity_id"] == "C-OP-IS-01")["required_context"].append("unknown_context"), "UNIMPLEMENTED_OPPORTUNITY_CONTEXT")
    expect_opportunity_failure(loaded.runtime, generated.system_quality, lambda item: message(item, "m008").update(phase="option_comparison"), "OPPORTUNITY_PHASE_MISMATCH")
    expect_opportunity_failure(loaded.runtime, generated.system_quality, lambda item: event(item, "ev_opp_c_op_li_01").update(dimension="logical_reasoning"), "OPPORTUNITY_DIMENSION_MISMATCH")
    expect_opportunity_failure(loaded.runtime, generated.system_quality, lambda item: event(item, "ev_security_open").update(timestamp_ms=100000), "OPPORTUNITY_TRIGGER_INVALID")

'''
    if negatives not in source:
        source = source.replace(negative_anchor, negatives + negative_anchor)
    source = source.replace('    print("Negative tests: 17 passed")\n', '    print("Negative tests: 32 passed")\n')
    path.write_text(source, encoding="utf-8")


def restore_workflow() -> None:
    workflow = '''name: Evaluation Health

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install validation dependencies
        run: python -m pip install --disable-pip-version-check "jsonschema[format]>=4.23,<5"
      - name: Validate knowledge notes
        run: python scripts/check_knowledge.py
      - name: Validate evaluation contract
        run: python scripts/check_evaluation_contract.py
      - name: Validate human annotation foundation
        run: python scripts/check_annotation_foundation.py
      - name: Validate candidate assessment scenario pack
        run: python scripts/check_candidate_scenario_pack.py
      - name: Validate contract and scenario hardening
        run: python scripts/check_contract_hardening.py
      - name: Validate generic full-Episode runner
        run: python scripts/check_full_episode_runner.py
      - name: Validate Exercise A high/low calibration
        run: python scripts/check_exercise_a_high_low.py
      - name: Validate Exercise A system failure separation
        run: python scripts/check_exercise_a_system_failure.py
      - name: Validate numeric evidence provenance
        run: python scripts/check_numeric_evidence_provenance.py
      - name: Validate Exercise A four-state matrix
        run: python scripts/check_exercise_a_four_state_matrix.py
      - name: Validate Exercise B medium vertical slice
        run: python scripts/check_exercise_b_medium.py
      - name: Validate Exercise B high/low calibration
        run: python scripts/check_exercise_b_high_low.py
      - name: Validate Exercise B fixture generator reproducibility
        run: |
          python scripts/generate_exercise_b_high_low.py
          git diff --exit-code -- fixtures/calibration/full-episodes/stakeholder-conflict/high fixtures/calibration/full-episodes/stakeholder-conflict/low
          python scripts/check_exercise_b_high_low.py
      - name: Validate Exercise B system failure separation
        run: python scripts/check_exercise_b_system_failure.py
      - name: Validate Exercise B system failure generator reproducibility
        run: |
          python scripts/generate_exercise_b_system_failure.py
          git diff --exit-code -- fixtures/calibration/full-episodes/stakeholder-conflict/system_failure
          python scripts/check_exercise_b_system_failure.py
      - name: Validate Exercise B four-state matrix
        run: python scripts/check_exercise_b_four_state_matrix.py
      - name: Validate Exercise C medium vertical slice
        run: |
          python scripts/generate_exercise_c_medium.py
          git diff --exit-code -- fixtures/calibration/full-episodes/time-boxed-decision/medium/deterministic-rule-result.json fixtures/calibration/full-episodes/time-boxed-decision/medium/system-quality-result.json fixtures/calibration/full-episodes/time-boxed-decision/medium/opportunity-resolution.json fixtures/calibration/full-episodes/time-boxed-decision/medium/evaluation-result.json fixtures/calibration/full-episodes/time-boxed-decision/medium/expected-feedback.json
          python scripts/check_exercise_c_medium.py
'''
    (ROOT / ".github/workflows/knowledge-health.yml").write_text(workflow, encoding="utf-8")


def main() -> None:
    patch_scenario()
    patch_episode()
    patch_rules()
    patch_checker()
    run("python", "scripts/generate_exercise_c_medium.py")
    run("python", "scripts/check_exercise_c_medium.py")
    run("python", "scripts/check_exercise_b_medium.py")
    run("python", "scripts/check_full_episode_runner.py")
    restore_workflow()
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "--", ".github/workflows/knowledge-health.yml", "fixtures/calibration/full-episodes/time-boxed-decision/medium/episode.json", "fixtures/calibration/full-episodes/time-boxed-decision/medium/deterministic-rule-result.json", "fixtures/calibration/full-episodes/time-boxed-decision/medium/system-quality-result.json", "fixtures/calibration/full-episodes/time-boxed-decision/medium/opportunity-resolution.json", "fixtures/calibration/full-episodes/time-boxed-decision/medium/evaluation-result.json", "fixtures/calibration/full-episodes/time-boxed-decision/medium/expected-feedback.json", "fixtures/scenarios/candidate-assessment-c-time-boxed-decision-v0.1.json", "gd_eval/rules/time_boxed_decision.py", "scripts/check_exercise_c_medium.py")
    for relative in [".github/workflows/finalize-exercise-c-review.yml", "docs/.exercise-c-review-trigger", "fixtures/calibration/full-episodes/time-boxed-decision/medium/episode.json.gz.b64", "scripts/materialize_exercise_c_medium_episode.py", "scripts/apply_exercise_c_review_fixes.py"]:
        path = ROOT / relative
        if path.exists():
            run("git", "rm", "-f", "--", relative)
    run("git", "commit", "-m", "fix: harden Exercise C evidence provenance")
    run("git", "push", "origin", "HEAD:feat/exercise-c-medium-v0.1")


if __name__ == "__main__":
    main()
