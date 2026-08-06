#!/usr/bin/env python3
"""Generate Exercise C high/low source fixtures and deterministic goldens."""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/time-boxed-decision"
MEDIUM_ROOT = CASE_ROOT / "medium"

from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.runner import (  # noqa: E402
    run_full_episode,
    transcript_hash,
    write_generated,
)

HIGH_TEXT = {
    "m005": "参加不能者を出さないことを最優先にし、学習効果、セキュリティ、30日以内の実施可能性、費用、例外対応で三案を比較します。未確定条件は後で明示して更新します。",
    "m008": "個人端末から社内演習環境へ接続できない懸念ですね。会社管理端末か指定会場端末に限定し、接続方式と代替手段を先に確認します。",
    "m010": "事前知識はオンライン、重要演習は対面、移動困難者は遠隔参加と後日補講を組み合わせる条件付きハイブリッドを候補にします。",
    "m012": "対面の演習品質を核にしつつ、知識学習と復習をオンラインへ分ければ、学習効果と参加可能性を同時に確保できます。",
    "m014": "端末を全員分用意せず、必須演習だけ会社管理端末へ限定し、その他は閲覧教材に分ければ運用費を抑えられます。",
    "m016": "まずセキュリティ条件、次に参加可能性、最後に学習効果と費用を比較し、条件を満たさない案は除外します。",
    "m018": "残り時間では、第一にセキュリティ、第二に地域採用者の参加方法、第三に実技品質を決め、費用詳細は実施条件へ回します。",
    "m020": "対面は実技に強い一方で参加可能性と費用が弱く、オンラインは参加可能性と費用に強い一方で実技とセキュリティが弱いです。ハイブリッドは調整が複雑ですが、管理端末、指定会場、補講条件を置けば弱点を抑えられます。",
    "m022": "初日に移動できない地域採用者は遠隔導入から開始し、実技は指定会場か後日補講へ分ければ、参加不能を避けながら対面品質も残せます。",
    "m024": "暫定案は、事前知識をオンライン、必須実技を二日間の対面、地域採用者には遠隔導入と後日補講を用意する条件付きハイブリッドです。",
    "m026": "必須実技を二日間へ絞り、管理端末数、指定会場数、補講対象者数を先に確定してから運用分担を決めます。",
    "m028": "追加条件を受け、オンライン演習を個人端末前提から会社管理端末または指定会場端末へ変更します。端末確保が間に合わない対象者は遠隔導入のみとし、実技は後日補講へ切り替えます。",
    "m030": "地域採用者の例外は遠隔導入と後日補講で扱い、通常参加者は二日間の対面実技へ集約します。対象人数と会場割当を実施前に確定します。",
    "m032": "残り時間は、必須端末数、例外対象者数、会場割当、確認責任者の順に固定し、結論と確認事項を分けて要約します。",
    "m033": "最終案は条件付きハイブリッドです。二日間の対面実技、事前オンライン学習、管理端末または指定会場端末、地域採用者の遠隔導入と後日補講をセットにします。",
    "m037": "実施条件は管理端末数、指定会場割当、遠隔導入対象、後日補講日、確認責任者です。端末不足ならオンライン実技を実施せず補講へ切り替えます。",
    "m038": "通常参加者、地域採用者、端末制約の例外まで含めたこの条件付きハイブリッドで合意とし、未確定数値は七日以内の確認事項にします。",
    "m039": "結論は条件付きハイブリッドです。事前知識はオンライン、必須実技は二日間の対面、個人端末は使わず管理端末か指定会場端末を使用します。移動できない地域採用者は遠隔導入と後日補講で対応し、七日以内に端末数、対象者数、会場割当、補講日、責任者を確認します。",
}

LOW_TEXT = {
    "m005": "参加しやすさと費用を見て、無難な案を選べばよいと思います。",
    "m008": "セキュリティは気になりますが、オンラインでも何とかできると思います。",
    "m010": "ハイブリッドなら両方できるので、それがよいと思います。",
    "m012": "対面とオンラインを半分ずつにすればよいと思います。",
    "m014": "端末は必要な人だけ用意すればよいと思います。",
    "m016": "大きな問題がなければハイブリッドで進めたいです。",
    "m018": "時間もあるので、このままハイブリッドを中心に考えます。",
    "m020": "対面、オンライン、ハイブリッドがありますが、ハイブリッドが一番無難です。費用は後で調整できます。",
    "m022": "地域採用者はオンラインで参加すればよいと思います。",
    "m024": "暫定的にハイブリッドにします。",
    "m026": "実技はできる範囲で対面にすればよいです。",
    "m028": "端末の問題はありますが、基本案は変えずにハイブリッドで進めます。",
    "m030": "移動できない人はオンラインでよいと思います。",
    "m032": "時間が少ないので、もう結論に進みます。",
    "m033": "最終案はハイブリッドです。",
    "m037": "実施しながら必要なことを決めればよいと思います。",
    "m038": "この内容で合意にします。",
    "m039": "結論はハイブリッドです。細かい条件は後で確認します。",
}

SCORES = {
    "high": {
        "issue_framing": 3,
        "logical_reasoning": 4,
        "listening_and_response": 4,
        "valuable_contribution": 4,
        "collaboration_and_relationship": 4,
        "decision_and_consensus": 4,
        "process_and_time_management": 4,
    },
    "low": {
        "issue_framing": 1,
        "logical_reasoning": 1,
        "listening_and_response": 2,
        "valuable_contribution": 1,
        "collaboration_and_relationship": 1,
        "decision_and_consensus": 1,
        "process_and_time_management": 1,
    },
}

EVIDENCE = {
    "high": {
        "issue_framing": (["ev_opp_c_op_is_01"], ["m005"]),
        "logical_reasoning": (["ev_opp_c_op_lo_01", "ev_opp_c_op_lo_02", "ev_opp_c_op_de_03"], ["m020", "m028", "m037"]),
        "listening_and_response": (["ev_opp_c_op_li_01", "ev_opp_c_op_li_02"], ["m008", "m028"]),
        "valuable_contribution": (["ev_opp_c_op_va_01", "ev_opp_c_op_va_02"], ["m010", "m022"]),
        "collaboration_and_relationship": (["ev_opp_c_op_co_01", "ev_opp_c_op_co_02"], ["m012", "m037"]),
        "decision_and_consensus": (["ev_opp_c_op_de_01", "ev_opp_c_op_de_02", "ev_opp_c_op_de_03"], ["m020", "m028", "m037"]),
        "process_and_time_management": (["ev_opp_c_op_pr_01", "ev_opp_c_op_pr_02", "ev_opp_c_op_pr_03"], ["m018", "m032", "m039"]),
    },
    "low": {
        "issue_framing": (["ev_opp_c_op_is_01"], ["m005"]),
        "logical_reasoning": (["ev_opp_c_op_lo_01", "ev_opp_c_op_lo_02"], ["m020", "m028"]),
        "listening_and_response": (["ev_opp_c_op_li_01", "ev_opp_c_op_li_02"], ["m008", "m028"]),
        "valuable_contribution": (["ev_opp_c_op_va_01", "ev_opp_c_op_va_02"], ["m010", "m022"]),
        "collaboration_and_relationship": (["ev_opp_c_op_co_01", "ev_opp_c_op_co_02"], ["m012", "m037"]),
        "decision_and_consensus": (["ev_opp_c_op_de_01", "ev_opp_c_op_de_02", "ev_opp_c_op_de_03"], ["m020", "m028", "m037"]),
        "process_and_time_management": (["ev_opp_c_op_pr_01", "ev_opp_c_op_pr_02", "ev_opp_c_op_pr_03"], ["m018", "m032", "m039"]),
    },
}

COMMENTS = {
    "high": {
        "issue_framing": "初期段階で優先条件と比較軸を明示し、未確定条件も管理対象にした。",
        "logical_reasoning": "三案の弱点、遅延リスク、修正条件、実施条件を複数局面で接続した。",
        "listening_and_response": "セキュリティと地域採用者の懸念を言い換え、具体的な案変更へ反映した。",
        "valuable_contribution": "遠隔導入、指定会場端末、後日補講を組み合わせた新しい実施構造を作った。",
        "collaboration_and_relationship": "異なる立場を例外設計と確認条件へ統合し、合意可能な形へ整えた。",
        "decision_and_consensus": "比較、修正、例外、責任者、再判断条件まで含む実行可能な合意を形成した。",
        "process_and_time_management": "40%と75%の通知後に論点を絞り、結論と確認事項を時間内に分離した。",
    },
    "low": {
        "issue_framing": "比較軸を具体化せず、無難さだけで方向を決めた。",
        "logical_reasoning": "三案の差や制約を検討せず、リスク後も根拠を更新しなかった。",
        "listening_and_response": "懸念には返答したが、内容を十分に受け止めた修正には至らなかった。",
        "valuable_contribution": "既存案を言い換えるだけで、制約を解く新しい提案を作らなかった。",
        "collaboration_and_relationship": "他参加者の立場を確認せず、合意を急いだ。",
        "decision_and_consensus": "実施条件、例外、確認事項を詰めずに結論を固定した。",
        "process_and_time_management": "時間通知後に優先順位を更新せず、終盤は検討を打ち切った。",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def mutate_episode(state: str, medium: dict[str, Any]) -> dict[str, Any]:
    episode = copy.deepcopy(medium)
    old_target = "candidate_c_medium"
    new_target = f"candidate_c_{state}"
    episode["session_id"] = f"exercise-c-{state}-001"

    for participant in episode["participants"]:
        if participant["participant_id"] == old_target:
            participant["participant_id"] = new_target
    for message in episode["messages"]:
        if message["participant_id"] == old_target:
            message["participant_id"] = new_target
            message["text"] = (HIGH_TEXT if state == "high" else LOW_TEXT)[message["message_id"]]
    for event in episode["events"]:
        if event.get("participant_id") == old_target:
            event["participant_id"] = new_target

    by_id = {event["event_id"]: event for event in episode["events"]}
    if state == "high":
        by_id["ev_criteria"]["criteria"] = [
            "参加不能者を出さない",
            "学習効果",
            "セキュリティ",
            "30日以内の実施可能性",
            "費用",
            "例外対応",
        ]
        by_id["ev_options_compared"]["criteria"] = [
            "参加可能性",
            "学習効果",
            "セキュリティ",
            "実施可能性",
            "費用",
        ]
        by_id["ev_priority_40"]["ordered_items"] = [
            "セキュリティ",
            "地域採用者の参加方法",
            "実技品質",
            "費用詳細",
        ]
        by_id["ev_priority_75"]["ordered_items"] = [
            "必須端末数",
            "例外対象者数",
            "会場割当",
            "確認責任者",
        ]
        by_id["ev_revision"]["changed_fields"] = [
            "security_device_condition",
            "regional_exception",
            "fallback_training",
        ]
        by_id["ev_implementation"]["conditions"] = [
            "管理端末数",
            "指定会場割当",
            "遠隔導入対象",
            "後日補講日",
            "確認責任者",
        ]
    else:
        for message in episode["messages"]:
            if message["message_id"] == "m018":
                message["move"] = "propose_idea"
            elif message["message_id"] == "m032":
                message["move"] = "propose_decision"
        episode["events"] = [
            event
            for event in episode["events"]
            if event["event_id"] not in {"ev_priority_40", "ev_priority_75"}
        ]
        by_id = {event["event_id"]: event for event in episode["events"]}
        by_id["ev_criteria"]["criteria"] = ["費用"]
        by_id["ev_options_compared"]["criteria"] = ["費用"]
        by_id["ev_revision"]["changed_fields"] = []
        by_id["ev_summary_fields"]["fields"] = ["mode"]
        by_id["ev_summary"]["fields"] = ["mode"]
        by_id["ev_summary"]["exception"] = ""
        by_id["ev_summary"]["next_check"] = ""
        by_id["ev_implementation"]["conditions"] = []

    episode["transcript_hash"] = transcript_hash(episode["messages"])
    return episode


def mutate_rater(state: str, source: dict[str, Any], suffix: str) -> dict[str, Any]:
    sheet = copy.deepcopy(source)
    sheet["sheet_id"] = f"rater-{suffix}-exercise-c-{state}-001"
    sheet["episode_id"] = f"exercise-c-{state}-001"
    sheet["calibration_set_version"] = "exercise-c-high-low-v0.1"
    sheet["overall_notes"] = f"Exercise C {state}を証拠先行で独立採点した。"
    for entry in sheet["dimensions"]:
        dimension = entry["dimension"]
        events, messages = EVIDENCE[state][dimension]
        entry["score"] = SCORES[state][dimension]
        entry["opportunity_evidence_event_ids"] = events
        entry["selected_evidence_message_ids"] = messages
        entry["comment"] = COMMENTS[state][dimension]
        entry["confidence"] = 0.88 if state == "high" else 0.86
        entry["not_evaluable_reason"] = None
        entry["flags"] = []
        entry["opportunity_status"] = "sufficient"
    return sheet


def mutate_adjudication(state: str, source: dict[str, Any]) -> dict[str, Any]:
    adjudication = copy.deepcopy(source)
    adjudication["adjudication_id"] = f"adj-exercise-c-{state}-001"
    adjudication["episode_id"] = f"exercise-c-{state}-001"
    adjudication["rater_sheet_ids"] = [
        f"rater-a-exercise-c-{state}-001",
        f"rater-b-exercise-c-{state}-001",
    ]
    adjudication["trigger_reasons"] = ["RANDOM_CALIBRATION_SAMPLE"]
    adjudication["overall_resolution_notes"] = (
        f"Exercise C {state}の証拠、機会、時間制約下の行動を確認した。"
    )
    for entry in adjudication["dimension_resolutions"]:
        dimension = entry["dimension"]
        score = SCORES[state][dimension]
        entry["agreement_class"] = "exact"
        entry["rater_scores"] = [score, score]
        entry["final_score"] = score
        entry["final_evidence_message_ids"] = EVIDENCE[state][dimension][1]
        entry["resolution_reason"] = COMMENTS[state][dimension]
        entry["not_evaluable_reason"] = None
        entry["rubric_issue_code"] = None
    return adjudication


def generate_state(state: str) -> None:
    target = CASE_ROOT / state
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(MEDIUM_ROOT, target)

    case = load_json(target / "case.json")
    case["case_id"] = f"exercise-c-{state}-001"
    case["state"] = state
    case["target_participant_id"] = f"candidate_c_{state}"
    write_json(target / "case.json", case)

    episode = mutate_episode(state, load_json(MEDIUM_ROOT / "episode.json"))
    write_json(target / "episode.json", episode)

    rater_a = mutate_rater(state, load_json(MEDIUM_ROOT / "rater-sheet-a.json"), "a")
    rater_b = mutate_rater(state, load_json(MEDIUM_ROOT / "rater-sheet-b.json"), "b")
    write_json(target / "rater-sheet-a.json", rater_a)
    write_json(target / "rater-sheet-b.json", rater_b)

    adjudication = mutate_adjudication(
        state, load_json(MEDIUM_ROOT / "adjudication.json")
    )
    write_json(target / "adjudication.json", adjudication)

    loaded = load_case(target, ROOT)
    generated = run_full_episode(loaded.runtime)
    write_generated(target, generated)
    feedback = target / "feedback.json"
    if feedback.exists():
        feedback.replace(target / "expected-feedback.json")
    print(f"Generated Exercise C {state} fixture")


def main() -> None:
    for state in ("high", "low"):
        generate_state(state)


if __name__ == "__main__":
    main()
