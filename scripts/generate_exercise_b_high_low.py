#!/usr/bin/env python3
"""Generate Exercise B high/low source fixtures and deterministic goldens."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASE_ROOT = ROOT / "fixtures/calibration/full-episodes/stakeholder-conflict"
MEDIUM_ROOT = CASE_ROOT / "medium"

from gd_eval.vertical_slice.loader import load_case  # noqa: E402
from gd_eval.vertical_slice.runner import (  # noqa: E402
    run_full_episode,
    transcript_hash,
    write_generated,
)

USER_MESSAGE_IDS = {
    "m005",
    "m008",
    "m011",
    "m013",
    "m015",
    "m017",
    "m019",
    "m021",
    "m023",
    "m025",
    "m027",
    "m029",
    "m033",
    "m034",
    "m035",
}

HIGH_TEXT = {
    "m005": "追加予算3000万円、重点は二つ以下です。緊急性、公平性、2年以内の実行可能性、継続運営リスク、既存資源との重複、半年後の見直し可能性で比較し、未採用施策にも緩和策を置きましょう。",
    "m008": "既存施設の低稼働があるという懸念ですね。全市一律の増設は避け、待機が集中する中心部の一時預かり枠へ限定し、既存施設の稼働率が一定未満なら新設せず運用改善を優先します。この修正なら懸念は軽減しますか。",
    "m011": "全域展開では運転手不足が悪化するという点ですね。移動困難な二地区に限定し、既存事業者との共同配車、運行日数の上限、利用件数による半年後の拡大判断を条件にします。残る運用上の懸念も確認したいです。",
    "m013": "子育ては中心部限定、交通は二地区限定、観光は既存広報と事業者網を使う小規模実証に分ければ、三つの立場を競合予算と非予算施策の組合せとして比較できます。",
    "m015": "重点予算は緊急性の高い子育てと交通へ置き、観光は既存資源で通年企画を試します。半年後に子育て・交通の実績が基準未達なら、観光を含めて再配分する段階的な案にします。",
    "m017": "重みは緊急性を最優先、次に2年以内の実行可能性とし、公平性、継続リスク、既存資源との重複を確認します。ただし季節変動を抑えられる観光案が示されれば再評価します。",
    "m019": "即時の生活支援を重点予算で行い、地域経済への波及は既存資源の通年企画で残します。半年後の指標で重点配分を再検討するため、三つの利害を時間軸の異なる一つの配分原則へ統合できます。",
    "m021": "観光側の懸念は、重点から外すことで事業者支援が先送りになる点ですね。新規重点予算は付けませんが、既存広報枠、事業者ネットワーク、季節分散企画を使い、半年後に観光消費額と参加事業者数が基準を下回れば再配分対象にします。この条件でも不足する点を教えてください。",
    "m023": "子育ては緊急性が最も高く既存施設を活用できますが、低稼働地域へ広げるリスクがあります。交通は二地区限定なら実行可能ですが、運転手確保が未達なら縮小が必要です。観光は波及効果がある一方で季節変動が大きいため既存資源で検証し、指標次第で再配分します。",
    "m025": "子育て1700万円、二地区の交通実証1300万円とします。合計3000万円、重点二施策です。子育ては待機対応数、交通は利用件数と運行充足率を半年後に確認し、未達なら配分を見直します。",
    "m027": "観光は既存広報枠と地域事業者ネットワークで季節分散型の小規模企画を行います。半年後に観光消費額、参加事業者数、閑散期比率を確認し、子育て・交通の実績と合わせて再配分します。担当部署と確認日も要約へ残します。",
    "m029": "最終合意の前に三者を個別に確認します。子育ては対象地域、交通は運転手確保、観光は半年後の再配分条件について、まだ反対できる点や不足条件があれば挙げてください。",
    "m033": "残り時間を要約と確認に分けます。未解決点は観光の再配分条件と各施策の半年後指標なので、まず担当と閾値を固定し、その後に最終合意を確認します。",
    "m034": "子育て1700万円、交通1300万円、観光は既存枠で試行し、半年後の指標で再配分を検討する条件です。三者の懸念と実施条件を含め、この内容で合意としてよいですね。",
    "m035": "結論は子育て1700万円、二地区の交通実証1300万円です。観光は既存広報と事業者連携で季節分散企画を行います。6か月時点で待機児童対応数、交通利用件数・運行充足率、観光消費額・参加事業者数を確認し、基準未達時は再配分します。担当部署、確認日、2年後の継続判断まで記録します。",
}

LOW_TEXT = {
    "m005": "3000万円なので、必要そうなものから二つ選べばよいと思います。細かい基準は話しながら決めましょう。",
    "m008": "子育て支援は必要だと思うので、そのまま進めればよいです。",
    "m011": "交通も必要なので、できる範囲でやればよいと思います。",
    "m013": "子育てと交通が大事だと思います。観光も余裕があれば考えます。",
    "m015": "とりあえず子育てと交通にします。観光は今回はなしでよいです。",
    "m017": "緊急そうなものを優先すればよいと思います。重みまでは決めなくてよいです。",
    "m019": "子育てと交通を選ぶので、それでまとめればよいです。",
    "m021": "観光は今回は予算を付けないので、次の機会に考えればよいです。",
    "m023": "子育てと交通は必要で、観光は急がなくてもよいと思います。",
    "m025": "子育て1700万円、交通1300万円にします。合計3000万円です。",
    "m027": "観光は今回は選ばないので、特に対応しなくてよいと思います。",
    "m029": "だいたい決まったので、このまま進めてよいですよね。",
    "m033": "時間がないので、もう結論にしましょう。",
    "m034": "子育て1700万円、交通1300万円で合意にします。",
    "m035": "子育て1700万円、交通1300万円に決めました。観光は今回は扱いません。",
}

SCORES = {
    "high": {
        "issue_framing": 4,
        "logical_reasoning": 4,
        "listening_and_response": 4,
        "valuable_contribution": 4,
        "collaboration_and_relationship": 4,
        "decision_and_consensus": 4,
        "process_and_time_management": 3,
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
        "issue_framing": (["ev_opp_b_is_01", "ev_opp_b_va_02"], ["m005", "m019"]),
        "logical_reasoning": (["ev_opp_b_lo_01", "ev_opp_b_lo_02"], ["m017", "m027"]),
        "listening_and_response": (["ev_opp_b_li_01", "ev_opp_b_li_02", "ev_opp_b_li_03"], ["m008", "m011", "m021"]),
        "valuable_contribution": (["ev_opp_b_va_01", "ev_opp_b_va_02"], ["m013", "m019"]),
        "collaboration_and_relationship": (["ev_opp_b_co_01", "ev_opp_b_co_02", "ev_opp_b_co_03"], ["m008", "m021", "m029"]),
        "decision_and_consensus": (["ev_opp_b_de_01", "ev_opp_b_de_02", "ev_opp_b_de_03"], ["m023", "m025", "m027"]),
        "process_and_time_management": (["ev_opp_b_pr_01"], ["m033"]),
    },
    "low": {
        "issue_framing": (["ev_opp_b_is_01"], ["m005"]),
        "logical_reasoning": (["ev_opp_b_lo_01", "ev_opp_b_lo_02"], ["m017", "m027"]),
        "listening_and_response": (["ev_opp_b_li_01", "ev_opp_b_li_02", "ev_opp_b_li_03"], ["m008", "m011", "m021"]),
        "valuable_contribution": (["ev_opp_b_va_01", "ev_opp_b_va_02"], ["m013", "m019"]),
        "collaboration_and_relationship": (["ev_opp_b_co_01", "ev_opp_b_co_02", "ev_opp_b_co_03"], ["m008", "m021", "m029"]),
        "decision_and_consensus": (["ev_opp_b_de_01", "ev_opp_b_de_02", "ev_opp_b_de_03"], ["m023", "m025", "m027"]),
        "process_and_time_management": (["ev_opp_b_pr_01"], ["m033"]),
    },
}

COMMENTS = {
    "high": {
        "issue_framing": "初期条件を構造化し、後半の反論を受けて見直し条件まで判断枠組みに組み込んだ。",
        "logical_reasoning": "優先基準、各案の弱点、不確実性、再配分条件を複数局面で接続した。",
        "listening_and_response": "三者の懸念を言い換え、案を修正し、残る反対条件まで確認した。",
        "valuable_contribution": "重点予算、既存資源、再配分を時間軸で統合する段階的ポートフォリオを作った。",
        "collaboration_and_relationship": "少数意見を切り捨てず、三者が再度反対できる最終確認の場を作った。",
        "decision_and_consensus": "基準、配分、リスク、緩和策、実施条件、再検討条件を含む合意を形成した。",
        "process_and_time_management": "終盤で残時間を要約と確認へ配分し、未解決点の処理順を具体化した。",
    },
    "low": {
        "issue_framing": "予算と重点数には触れたが、比較基準を定義せず議論構造を作らなかった。",
        "logical_reasoning": "必要性を述べるだけで、比較、反証、条件、緩和策を根拠へ接続しなかった。",
        "listening_and_response": "各懸念の後に応答したが、内容を受け止めた案修正には至らなかった。",
        "valuable_contribution": "既出の二施策を選ぶだけで、統合案や新しい分析を提示しなかった。",
        "collaboration_and_relationship": "礼儀は保ったが、少数意見の保護や対立調整を行わず合意を急いだ。",
        "decision_and_consensus": "配分額は示したが、判断基準、反対意見の処理、緩和策を欠いた。",
        "process_and_time_management": "時間不足を理由に収束を急ぎ、論点や手順の調整を行わなかった。",
    },
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def replace_identity(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: replace_identity(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_identity(item, old, new) for item in value]
    return new if value == old else value


def build_episode(state: str) -> dict[str, Any]:
    episode = read_json(MEDIUM_ROOT / "episode.json")
    target = f"candidate_b_{state}"
    session = f"exercise-b-{state}-001"
    episode = replace_identity(episode, "candidate_b_medium", target)
    episode["session_id"] = session
    episode["started_at"] = "2026-08-05T08:00:00Z" if state == "high" else "2026-08-05T10:00:00Z"
    episode["ended_at"] = "2026-08-05T08:15:00Z" if state == "high" else "2026-08-05T10:15:00Z"
    texts = HIGH_TEXT if state == "high" else LOW_TEXT
    for message in episode["messages"]:
        if message["message_id"] in USER_MESSAGE_IDS:
            message["text"] = texts[message["message_id"]]
    if state == "low":
        episode["events"] = [
            event
            for event in episode["events"]
            if event.get("event")
            not in {"POSITIONS_INTEGRATED", "MINORITY_CONCERN_STATUS"}
        ]
        for event in episode["events"]:
            event_type = event.get("event")
            if event_type == "PRIVATE_CONCERN_REVEALED":
                event["candidate_response_message_ids"] = []
            elif event_type == "DECISION_ALLOCATION_RECORDED":
                event["fields"] = [
                    field
                    for field in event.get("fields", [])
                    if field != "mitigation"
                ]
                event.pop("mitigation", None)
            elif event_type == "SUMMARY_FIELDS_RECORDED":
                event["fields"] = ["allocation"]
    episode["transcript_hash"] = transcript_hash(episode["messages"])
    return episode


def build_rater(state: str, suffix: str) -> dict[str, Any]:
    sheet = read_json(MEDIUM_ROOT / f"rater-sheet-{suffix}.json")
    session = f"exercise-b-{state}-001"
    sheet["sheet_id"] = f"rater-{suffix}-exercise-b-{state}-001"
    sheet["episode_id"] = session
    sheet["calibration_set_version"] = f"exercise-b-{state}-v0.1"
    sheet["started_at"] = "2026-08-05T08:20:00Z" if state == "high" else "2026-08-05T10:20:00Z"
    sheet["completed_at"] = "2026-08-05T08:35:00Z" if state == "high" else "2026-08-05T10:35:00Z"
    for item in sheet["dimensions"]:
        dimension = item["dimension"]
        opportunity_ids, message_ids = EVIDENCE[state][dimension]
        item["opportunity_evidence_event_ids"] = opportunity_ids
        item["selected_evidence_message_ids"] = message_ids
        item["score"] = SCORES[state][dimension]
        item["confidence"] = 0.9 if state == "high" else 0.86
        item["comment"] = COMMENTS[state][dimension]
        item["not_evaluable_reason"] = None
        item["flags"] = []
    sheet["overall_notes"] = (
        f"Exercise B {state}の校正ケースとして、証拠を先に選択して独立採点した。"
    )
    return sheet


def build_adjudication(state: str) -> dict[str, Any]:
    adjudication = read_json(MEDIUM_ROOT / "adjudication.json")
    session = f"exercise-b-{state}-001"
    adjudication["adjudication_id"] = f"adj-exercise-b-{state}-001"
    adjudication["episode_id"] = session
    adjudication["rater_sheet_ids"] = [
        f"rater-a-exercise-b-{state}-001",
        f"rater-b-exercise-b-{state}-001",
    ]
    adjudication["created_at"] = "2026-08-05T08:50:00Z" if state == "high" else "2026-08-05T10:50:00Z"
    for item in adjudication["dimension_resolutions"]:
        dimension = item["dimension"]
        score = SCORES[state][dimension]
        item["rater_scores"] = [score, score]
        item["agreement_class"] = "exact"
        item["final_score"] = score
        item["final_evidence_message_ids"] = EVIDENCE[state][dimension][1]
        item["resolution_reason"] = COMMENTS[state][dimension]
        item["not_evaluable_reason"] = None
        item["rubric_issue_code"] = None
    adjudication["overall_resolution_notes"] = (
        f"全7軸で独立評価が一致し、Exercise B {state}の15評価機会との証拠連結を確認した。"
    )
    return adjudication


def build_case(state: str) -> dict[str, Any]:
    case = read_json(MEDIUM_ROOT / "case.json")
    case["case_id"] = f"exercise-b-{state}-001"
    case["state"] = state
    case["target_participant_id"] = f"candidate_b_{state}"
    return case


def generate_state(state: str) -> None:
    destination = CASE_ROOT / state
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    write_json(destination / "case.json", build_case(state))
    write_json(destination / "episode.json", build_episode(state))
    write_json(destination / "rater-sheet-a.json", build_rater(state, "a"))
    write_json(destination / "rater-sheet-b.json", build_rater(state, "b"))
    write_json(destination / "adjudication.json", build_adjudication(state))
    loaded = load_case(destination, ROOT)
    generated = run_full_episode(loaded.runtime)
    write_generated(destination, generated)
    generated_feedback = destination / "feedback.json"
    generated_feedback.replace(destination / "expected-feedback.json")


def main() -> None:
    for state in ("high", "low"):
        generate_state(state)
        print(f"Generated Exercise B {state} fixture")


if __name__ == "__main__":
    main()
