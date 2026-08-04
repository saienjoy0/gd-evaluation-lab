#!/usr/bin/env python3
"""Regenerate Exercise A medium vertical-slice outputs without an LLM."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

NARRATIVES = {
    "issue_framing": {
        "positive": "対象、時間帯、比較基準を明確にした。",
        "missing": "目的と制約の優先順位付けは弱い。",
        "improvement": "最初に目的、対象、制約、判断基準の順で整理する。",
    },
    "logical_reasoning": {
        "positive": "案の利点と運用負荷を比較した。",
        "missing": "主張を支える定量根拠が少ない。",
        "improvement": "基準ごとに根拠と不確実性を明示する。",
    },
    "listening_and_response": {
        "positive": "騒音と動線の懸念へ直接応答して案を修正した。",
        "missing": "相手の主張を要約して確認する行動は少ない。",
        "improvement": "懸念を一度言い換えてから修正案を返す。",
    },
    "valuable_contribution": {
        "positive": "時間帯分離と可動机の案を具体化した。",
        "missing": "新しい分析や代替案の広がりは限定的だった。",
        "improvement": "少なくとも二案を改善し、比較可能な形にする。",
    },
    "collaboration_and_relationship": {
        "positive": "対立するニーズを否定せず条件付きで統合した。",
        "missing": "発言機会の偏りを調整する行動はなかった。",
        "improvement": "未発言者や異なる立場へ明示的に意見を求める。",
    },
    "decision_and_consensus": {
        "positive": "成功指標と実証条件を含む結論を提示した。",
        "missing": "結論の弱点と撤退条件は十分に明示していない。",
        "improvement": "合意時にリスク、例外、撤退条件も確認する。",
    },
    "process_and_time_management": {
        "positive": "最後に見直し時点を含めて要約した。",
        "missing": "途中の時間・進捗調整が少ない。",
        "improvement": "中盤で残り時間と未解決論点を確認する。",
    },
}

DISPLAY_GROUPS = {
    "thinking": {
        "aggregation_status": "not_calibrated",
        "score": None,
        "coverage": {"evaluated": 3, "total": 3},
        "bottleneck_dimension": "logical_reasoning",
        "summary": "枠組みは作れたが、比較を支える根拠の明示が弱かった。",
    },
    "collaboration": {
        "aggregation_status": "not_calibrated",
        "score": None,
        "coverage": {"evaluated": 2, "total": 2},
        "bottleneck_dimension": "collaboration_and_relationship",
        "summary": "懸念へ応答して統合できたが、参加促進は限定的だった。",
    },
    "progress": {
        "aggregation_status": "not_calibrated",
        "score": None,
        "coverage": {"evaluated": 2, "total": 2},
        "bottleneck_dimension": "process_and_time_management",
        "summary": "条件付きの合意は作れたが、途中の進捗管理が不足した。",
    },
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def transcript_hash(messages: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        messages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def target_participant_id(episode: dict[str, Any]) -> str:
    candidates = [
        participant["participant_id"]
        for participant in episode["participants"]
        if participant["speaker_type"] == "user"
    ]
    if len(candidates) != 1:
        raise ValueError("Exercise A vertical slice requires exactly one target user")
    return candidates[0]


def system_quality(
    scenario: dict[str, Any], episode: dict[str, Any]
) -> dict[str, Any]:
    messages = sorted(episode["messages"], key=lambda item: item["start_ms"])
    message_by_id = {message["message_id"]: message for message in messages}
    candidate_id = target_participant_id(episode)
    candidate_messages = [
        message
        for message in messages
        if message["participant_id"] == candidate_id
        and message["speaker_type"] == "user"
    ]
    candidate_structure = [
        message
        for message in candidate_messages
        if message["phase"] == "problem_definition"
        and message["move"] in {"clarify_goal", "define_scope", "define_criteria"}
    ]
    context_events = [
        event for event in episode["events"] if event["event"] == "CONTEXT_RESOLVED"
    ]
    concern_events = [
        event
        for event in episode["events"]
        if event["event"] == "PRIVATE_CONCERN_REVEALED"
    ]
    summary_events = [
        event
        for event in episode["events"]
        if event["event"] == "SUMMARY_FIELDS_RECORDED"
    ]
    prohibited_events = [
        event
        for event in episode["events"]
        if event["event"] == "PROHIBITED_CONDITION_TRIGGERED"
    ]
    rubrics = {rubric["rubric_id"]: rubric for rubric in scenario["instance_rubrics"]}
    conditions = {
        condition["condition_id"]: condition
        for condition in scenario["prohibited_conditions"]
    }

    r01_params = rubrics["A-R01"]["rule"]["params"]
    guarded_moves = set(r01_params["actions"])
    minimum_user_messages = r01_params["minimum_user_messages"]
    preemptive_ai_actions = []
    for message in messages:
        if message["speaker_type"] != "ai" or message["move"] not in guarded_moves:
            continue
        prior_user_count = sum(
            candidate["end_ms"] <= message["start_ms"]
            for candidate in candidate_messages
        )
        if prior_user_count < minimum_user_messages:
            preemptive_ai_actions.append(message)

    resolved_keys = {event.get("key") for event in context_events}
    summary_fields = {
        field for event in summary_events for field in event.get("fields", [])
    }
    triggered_conditions = {
        event.get("condition_id") for event in prohibited_events
    }
    concern_events_valid = bool(concern_events) and all(
        event.get("trigger_move") in {"ask_question", "compare_options", "challenge"}
        and event.get("message_id") in message_by_id
        and message_by_id[event["message_id"]]["speaker_type"] == "ai"
        for event in concern_events
    )

    checks = {
        "A-R01": (
            not preemptive_ai_actions and len(candidate_structure) >= 3,
            [message["message_id"] for message in candidate_structure],
            [],
            "AIが対象・基準を先に確定せず、利用者が先に定義した。",
        ),
        "A-R02": (
            len(resolved_keys & {"priority_target", "success_metric", "usage_hours"})
            >= 2,
            [event["message_id"] for event in context_events],
            [event["event_id"] for event in context_events],
            "三つの文脈キーが解消された。",
        ),
        "A-R04": (
            concern_events_valid,
            [event["message_id"] for event in concern_events],
            [event["event_id"] for event in concern_events],
            "非公開懸念は質問・比較後に開示された。",
        ),
        "A-R05": (
            {"success_metric", "pilot_condition"} <= summary_fields,
            [event["message_id"] for event in summary_events],
            [event["event_id"] for event in summary_events],
            "要約に成功指標と実証見直し条件が含まれる。",
        ),
    }

    results = []
    for rule_id, (passed, message_ids, event_ids, detail) in checks.items():
        rubric = rubrics[rule_id]
        results.append(
            {
                "rule_id": rule_id,
                "outcome": "pass" if passed else "fail",
                "severity": rubric["severity"],
                "evidence_message_ids": message_ids,
                "evidence_event_ids": event_ids,
                "affected_dimensions": rubric["affected_dimensions"],
                "detail": detail if passed else "決定論的条件を満たさなかった。",
            }
        )

    for condition_id in ["A-PROH-01", "A-PROH-02"]:
        condition = conditions[condition_id]
        triggered = condition_id in triggered_conditions
        message_ids = (
            [event["message_id"] for event in concern_events]
            if condition_id == "A-PROH-02"
            else []
        )
        event_ids = (
            [event["event_id"] for event in concern_events]
            if condition_id == "A-PROH-02"
            else [
                event["event_id"]
                for event in prohibited_events
                if event.get("condition_id") == condition_id
            ]
        )
        detail = (
            "triggerなしの非公開懸念開示は観察されない。"
            if condition_id == "A-PROH-02"
            else "AIによる先回りの課題定義は観察されない。"
        )
        results.append(
            {
                "rule_id": condition_id,
                "outcome": "fail" if triggered else "pass",
                "severity": condition["severity"],
                "evidence_message_ids": message_ids,
                "evidence_event_ids": event_ids,
                "affected_dimensions": condition["affected_dimensions"],
                "detail": detail if not triggered else "禁止条件が発生した。",
            }
        )

    failed = [result for result in results if result["outcome"] == "fail"]
    status = (
        "fail"
        if any(result["severity"] == "critical" for result in failed)
        else "warn"
        if failed
        else "pass"
    )
    dimension_scores = {
        "goal_progression": 4,
        "responsiveness": 4,
        "user_agency": 5 if checks["A-R01"][0] else 2,
        "role_believability": 4,
        "discussion_coherence": 4,
        "novelty_and_repetition": 4,
        "consensus_quality": 4 if checks["A-R05"][0] else 2,
        "natural_pacing": 4,
    }
    return {
        "contract_version": "0.1",
        "result_id": f"sq-{episode['session_id']}",
        "session_id": episode["session_id"],
        "scenario_id": episode["scenario_id"],
        "scenario_version": episode["scenario_version"],
        "evaluator_version": "exercise-a-deterministic-v0.1",
        "status": status,
        "rule_results": results,
        "dimension_scores": dimension_scores,
    }


def opportunities(
    scenario: dict[str, Any], episode: dict[str, Any]
) -> dict[str, Any]:
    candidate_id = target_participant_id(episode)
    message_by_id = {message["message_id"]: message for message in episode["messages"]}
    valid_candidate_message_ids = {
        message_id
        for message_id, message in message_by_id.items()
        if message["speaker_type"] == "user"
        and message["participant_id"] == candidate_id
    }
    offers: dict[str, list[dict[str, Any]]] = {}
    invalidations: dict[str, list[dict[str, Any]]] = {}
    for event in episode["events"]:
        if event["event"] == "OPPORTUNITY_OFFERED":
            offers.setdefault(event.get("opportunity_id"), []).append(event)
        if event["event"] == "PROHIBITED_CONDITION_TRIGGERED":
            invalidations.setdefault(event.get("condition_id"), []).append(event)

    items = []
    for opportunity in scenario["evaluation_opportunities"]:
        offer_events = offers.get(opportunity["opportunity_id"], [])
        invalidated_by = [
            condition_id
            for condition_id in opportunity.get("invalidated_by", [])
            if condition_id in invalidations
        ]
        response_ids = list(
            dict.fromkeys(
                message_id
                for event in offer_events
                for message_id in event.get("candidate_response_message_ids", [])
                if message_id in valid_candidate_message_ids
            )
        )
        if invalidated_by:
            status = "invalid"
            response_status = "not_applicable"
            response_ids = []
            detail = "禁止条件により評価機会が無効化された。"
        elif offer_events:
            status = "offered"
            response_status = "observed" if response_ids else "not_observed"
            detail = (
                "構造化イベントと利用者応答を確認した。"
                if response_ids
                else "評価機会は提供されたが利用者応答は観察されない。"
            )
        else:
            status = "not_offered"
            response_status = "not_applicable"
            detail = "対応する評価機会イベントが存在しない。"

        items.append(
            {
                "opportunity_id": opportunity["opportunity_id"],
                "dimension": opportunity["dimension"],
                "status": status,
                "trigger_event_ids": [event["event_id"] for event in offer_events],
                "candidate_response_message_ids": response_ids,
                "invalidated_by": invalidated_by,
                "response_status": response_status,
                "detail": detail,
            }
        )

    return {
        "contract_version": "0.1",
        "resolution_id": f"or-{episode['session_id']}",
        "session_id": episode["session_id"],
        "scenario_id": episode["scenario_id"],
        "scenario_version": episode["scenario_version"],
        "target_participant_id": candidate_id,
        "resolver_version": "opportunity-resolver-v0.1",
        "items": items,
        "summary": {
            "offered": sum(item["status"] == "offered" for item in items),
            "not_offered": sum(item["status"] == "not_offered" for item in items),
            "invalid": sum(item["status"] == "invalid" for item in items),
            "with_candidate_response": sum(
                item["response_status"] == "observed" for item in items
            ),
        },
    }


def evaluation(
    episode: dict[str, Any],
    system_quality_result: dict[str, Any],
    adjudication: dict[str, Any],
) -> dict[str, Any]:
    dimensions = []
    for resolution in adjudication["dimension_resolutions"]:
        dimension = resolution["dimension"]
        narrative = NARRATIVES[dimension]
        not_evaluable = resolution["final_score"] == "NE"
        dimensions.append(
            {
                "dimension": dimension,
                "score": resolution["final_score"],
                "confidence": 0 if not_evaluable else 0.9,
                "evidence_message_ids": resolution["final_evidence_message_ids"],
                "positive_behavior": "" if not_evaluable else narrative["positive"],
                "missing_behavior": "" if not_evaluable else narrative["missing"],
                "improvement": "" if not_evaluable else narrative["improvement"],
                "not_evaluable_reason": (
                    {
                        "code": resolution["not_evaluable_reason"],
                        "detail": resolution["resolution_reason"],
                    }
                    if not_evaluable
                    else None
                ),
                "question_results": [],
            }
        )

    violations = [
        {
            "rule_id": result["rule_id"],
            "severity": result["severity"],
            "message_ids": result["evidence_message_ids"],
            "affected_candidate_dimensions": result["affected_dimensions"],
        }
        for result in system_quality_result["rule_results"]
        if result["outcome"] == "fail"
    ]
    return {
        "contract_version": "0.1",
        "session_id": episode["session_id"],
        "target_participant_id": target_participant_id(episode),
        "status": (
            "completed"
            if all(
                resolution["final_score"] != "NE"
                for resolution in adjudication["dimension_resolutions"]
            )
            else "partial"
        ),
        "ai_quality": {
            "status": system_quality_result["status"],
            "violations": violations,
            "dimension_scores": system_quality_result["dimension_scores"],
        },
        "candidate_dimensions": dimensions,
        "display_groups": DISPLAY_GROUPS,
        "version_info": {
            "rubric_version": "candidate-behavior-v0.1",
            "ai_quality_rubric_version": "ai-participant-v0.1",
            "scenario_version": episode["scenario_version"],
            "orchestrator_version": episode["versions"]["orchestrator_version"],
            "prompt_version": episode["versions"]["prompt_version"],
            "judge_model": "human-adjudication",
            "judge_version": "not-applied-v0.1",
            "deterministic_evaluator_version": "exercise-a-deterministic-v0.1",
            "transcript_hash": episode["transcript_hash"],
        },
        "review_status": "completed",
        "legacy_evaluation": None,
        "evaluation_disagreement": None,
    }


def feedback(evaluation_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": "0.1",
        "slice_id": "exercise-a-medium-v0.1",
        "dimension_narratives": {
            item["dimension"]: {
                "positive": item["positive_behavior"],
                "missing": item["missing_behavior"],
                "improvement": item["improvement"],
            }
            for item in evaluation_result["candidate_dimensions"]
        },
        "display_groups": evaluation_result["display_groups"],
        "strengths": [
            "曖昧なテーマへ対象と比較基準を設定した",
            "複数の懸念を実施条件へ反映した",
        ],
        "next_action": "中盤で残り時間と未解決論点を確認し、根拠付きで優先順位を付ける。",
        "limitations": "合成Episodeに基づく校正用フィードバックであり、採用判断には使用しない。",
    }


def build(repo: Path = ROOT) -> dict[str, Any]:
    base = repo / "fixtures/calibration/full-episodes/ambiguous-structure/medium"
    scenario = load(
        repo
        / "fixtures/scenarios/candidate-assessment-a-ambiguous-structure-v0.1.json"
    )
    episode = load(base / "episode.json")
    adjudication = load(base / "adjudication.json")
    quality_result = system_quality(scenario, episode)
    opportunity_result = opportunities(scenario, episode)
    evaluation_result = evaluation(episode, quality_result, adjudication)
    return {
        "system_quality": quality_result,
        "opportunity_resolution": opportunity_result,
        "evaluation_result": evaluation_result,
        "feedback": feedback(evaluation_result),
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True))
