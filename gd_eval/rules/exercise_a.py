"""Exercise A evidence-to-language policy.

The policy is keyed by observed dimension and adjudicated score, never by case ID or
high/medium/low/system_failure state. Unknown combinations fall back to rubric and
human-authored adjudication text.
"""
from __future__ import annotations

from typing import Any

_EXERCISE_ID = "candidate-assessment-a-ambiguous-structure"

_TEMPLATES: dict[tuple[str, int], tuple[str, str, str]] = {
    ("issue_framing", 3): (
        "対象、時間帯、比較基準を明確にした。",
        "目的と制約の優先順位付けは弱い。",
        "最初に目的、対象、制約、判断基準の順で整理する。",
    ),
    ("logical_reasoning", 2): (
        "案の利点と運用負荷を比較した。",
        "主張を支える定量根拠が少ない。",
        "基準ごとに根拠と不確実性を明示する。",
    ),
    ("listening_and_response", 3): (
        "騒音と動線の懸念へ直接応答して案を修正した。",
        "相手の主張を要約して確認する行動は少ない。",
        "懸念を一度言い換えてから修正案を返す。",
    ),
    ("valuable_contribution", 2): (
        "時間帯分離と可動机の案を具体化した。",
        "新しい分析や代替案の広がりは限定的だった。",
        "少なくとも二案を改善し、比較可能な形にする。",
    ),
    ("collaboration_and_relationship", 3): (
        "対立するニーズを否定せず条件付きで統合した。",
        "発言機会の偏りを調整する行動はなかった。",
        "未発言者や異なる立場へ明示的に意見を求める。",
    ),
    ("decision_and_consensus", 3): (
        "成功指標と実証条件を含む結論を提示した。",
        "結論の弱点と撤退条件は十分に明示していない。",
        "合意時にリスク、例外、撤退条件も確認する。",
    ),
    ("process_and_time_management", 2): (
        "最後に見直し時点を含めて要約した。",
        "途中の時間・進捗調整が少ない。",
        "中盤で残り時間と未解決論点を確認する。",
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
    current = anchors.get(str(score), resolution.get("resolution_reason", "観察行動を確認した。"))
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
