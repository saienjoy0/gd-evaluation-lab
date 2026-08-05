"""Exercise A evidence-to-language policy.

The policy is keyed by observed dimension and adjudicated score, never by case ID or
high/medium/low/system_failure state. Unknown combinations fall back to rubric and
human-authored adjudication text.
"""
from __future__ import annotations

from typing import Any

_EXERCISE_ID = "candidate-assessment-a-ambiguous-structure"

_TEMPLATES: dict[tuple[str, int], tuple[str, str, str]] = {
    ("issue_framing", 1): (
        "対象、制約、判断基準を整理せず、曖昧なまま案へ進んだ。",
        "議論の前提と優先対象が定まっていない。",
        "最初に対象、制約、成功条件を一つずつ確認する。",
    ),
    ("issue_framing", 3): (
        "対象、時間帯、比較基準を明確にした。",
        "目的と制約の優先順位付けは弱い。",
        "最初に目的、対象、制約、判断基準の順で整理する。",
    ),
    ("issue_framing", 4): (
        "目的、対象、制約、判断基準を構造化し、優先順位まで示した。",
        "前提が変わった場合の再構成手順は明示していない。",
        "前提変化時にどの論点を再検討するかも定める。",
    ),
    ("logical_reasoning", 1): (
        "選択理由や根拠を示さず、比較を行わなかった。",
        "結論と理由が接続されていない。",
        "案を選ぶ前に、少なくとも二つの基準で理由を説明する。",
    ),
    ("logical_reasoning", 2): (
        "案の利点と運用負荷を比較した。",
        "主張を支える定量根拠が少ない。",
        "基準ごとに根拠と不確実性を明示する。",
    ),
    ("logical_reasoning", 4): (
        "二案の利点、リスク、閾値、撤退条件を結び付けて比較した。",
        "外部データによる仮説検証までは行っていない。",
        "主要仮説ごとに確認データと検証方法を指定する。",
    ),
    ("listening_and_response", 2): (
        "懸念へ反応したが、内容を踏まえた修正や確認はなかった。",
        "表面的な返答にとどまり、相手の意図を確認していない。",
        "懸念を言い換えて確認し、その内容を修正案へ反映する。",
    ),
    ("listening_and_response", 3): (
        "騒音と動線の懸念へ直接応答して案を修正した。",
        "相手の主張を要約して確認する行動は少ない。",
        "懸念を一度言い換えてから修正案を返す。",
    ),
    ("listening_and_response", 4): (
        "複数の懸念を言い換えて確認し、具体条件へ統合した。",
        "統合案への再確認を全員から取る余地がある。",
        "統合後に各立場の懸念が解消したか順に確認する。",
    ),
    ("valuable_contribution", 1): (
        "既出の交流案を繰り返し、具体化や改善を行わなかった。",
        "議論を前進させる新しい情報や具体案がない。",
        "既存案へ対象、条件、リスクのいずれかを追加する。",
    ),
    ("valuable_contribution", 2): (
        "時間帯分離と可動机の案を具体化した。",
        "新しい分析や代替案の広がりは限定的だった。",
        "少なくとも二案を改善し、比較可能な形にする。",
    ),
    ("valuable_contribution", 4): (
        "複数案を改善・統合し、運用表と撤退案まで補った。",
        "実施後に生じる二次的リスクの探索は限定的だった。",
        "実施後の副作用を想定し、追加の監視項目を置く。",
    ),
    ("collaboration_and_relationship", 2): (
        "礼儀は保ったが、他者の参加促進や対立調整は行わなかった。",
        "異なる立場を議論へ参加させる働きかけがない。",
        "未発言者や異なる立場へ具体的な問いを投げる。",
    ),
    ("collaboration_and_relationship", 3): (
        "対立するニーズを否定せず条件付きで統合した。",
        "発言機会の偏りを調整する行動はなかった。",
        "未発言者や異なる立場へ明示的に意見を求める。",
    ),
    ("collaboration_and_relationship", 4): (
        "異なる立場へ未解決点を問い、少数懸念を合意条件へ反映した。",
        "発言量の偏りを定量的に確認する行動はなかった。",
        "合意前に未発言者と反対意見を明示的に一巡確認する。",
    ),
    ("decision_and_consensus", 1): (
        "判断基準なしに結論を急ぎ、反対意見や実行条件を扱わなかった。",
        "納得可能な選択理由と合意条件がない。",
        "判断基準、反対意見、実行条件を確認してから結論を提案する。",
    ),
    ("decision_and_consensus", 3): (
        "成功指標と実証条件を含む結論を提示した。",
        "結論の弱点と撤退条件は十分に明示していない。",
        "合意時にリスク、例外、撤退条件も確認する。",
    ),
    ("decision_and_consensus", 4): (
        "指標、閾値、中間レビュー、撤退条件を含む合意を作った。",
        "判断基準間の優先順位が変わる場合の例外処理は未定義だった。",
        "基準が衝突した場合の優先順位と例外条件を確認する。",
    ),
    ("process_and_time_management", 1): (
        "時間や進捗を管理せず、結論と次の行動を整理しなかった。",
        "残り時間に応じた論点整理や収束行動がない。",
        "中盤と終了前に残り時間、未解決点、次の行動を確認する。",
    ),
    ("process_and_time_management", 2): (
        "最後に見直し時点を含めて要約した。",
        "途中の時間・進捗調整が少ない。",
        "中盤で残り時間と未解決論点を確認する。",
    ),
    ("process_and_time_management", 3): (
        "残り時間、次の論点、担当、中間レビューを具体化した。",
        "停滞を早期検知して議論順序を再設計する行動は少ない。",
        "中盤より前に進捗確認を置き、必要なら論点順を入れ替える。",
    ),
}

_GROUP_SUMMARIES = {
    "logical_reasoning": "枠組みは作れたが、比較を支える根拠の明示が弱かった。",
    "collaboration_and_relationship": "懸念へ応答して統合できたが、参加促進は限定的だった。",
    "process_and_time_management": "条件付きの合意は作れたが、途中の進捗管理が不足した。",
}

_STRENGTH_HEADLINES = {
    "issue_framing": "曖昧なテーマへ対象と比較基準を設定した",
    "listening_and_response": "複数の懸念を実施条件へ反映した",
    "decision_and_consensus": "判断基準と実証条件を含む合意を作った",
}


def narrative(
    exercise_id: str,
    dimension: str,
    score: int,
    resolution: dict[str, Any],
    rubric_dimension: dict[str, Any],
) -> tuple[str, str, str]:
    if exercise_id == _EXERCISE_ID and (dimension, score) in _TEMPLATES:
        return _TEMPLATES[(dimension, score)]
    anchors = rubric_dimension.get("anchors", {})
    current = anchors.get(
        str(score), resolution.get("resolution_reason", "観察行動を確認した。")
    )
    next_anchor = anchors.get(str(min(score + 1, 4)), current)
    return (
        resolution.get("resolution_reason", current),
        f"次の水準で求められる行動は「{next_anchor}」である。",
        f"次回は、{next_anchor}",
    )


def group_summary(bottleneck_dimension: str, fallback: str) -> str:
    return _GROUP_SUMMARIES.get(bottleneck_dimension, fallback)


def strength_headline(dimension: str, positive_behavior: str) -> str:
    return _STRENGTH_HEADLINES.get(dimension, positive_behavior.rstrip("。"))


def compose_next_action(low_dimensions: list[str], improvements: dict[str, str]) -> str:
    if {
        "logical_reasoning",
        "process_and_time_management",
    }.issubset(low_dimensions):
        return "中盤で残り時間と未解決論点を確認し、根拠付きで優先順位を付ける。"
    if not low_dimensions:
        return "今回の強みを別の議題でも再現し、複数場面で証拠を増やす。"
    return improvements[low_dimensions[0]]
