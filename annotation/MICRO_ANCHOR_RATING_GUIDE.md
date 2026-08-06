# Micro Anchor Blind Rating Guide v0.1

## 1. 目的

評価者が期待点を見ずに、Micro Anchorの評価機会、証拠、score 1〜4またはNEを独立判定するための手順を定める。

本評価は練習・研究・校正用であり、採用合否の自動決定には使用しない。

## 2. 使用するもの

- Blind Pack
- `rubrics/candidate-behavior/v0.1.json`
- `schemas/micro-anchor-rating-v0.1.schema.json`
- 匿名の`rater_id`

正本アンカー、期待点、rationale、boundary noteは評価完了前に見ない。

## 3. 評価順序

1. Scenario contextを読む
2. 評価対象dimensionを確認する
3. 評価機会が`sufficient / insufficient / uncertain / invalid`のどれか判定する
4. scoreを考える前に対象候補者本人のmessage IDを選ぶ
5. RubricのBARSアンカーへ照合する
6. 1〜4またはNEを記録する
7. confidenceとnotesを記録する

## 4. 数値評価

- opportunity statusは`sufficient`
- 対象候補者本人の証拠を最低1件選ぶ
- score 4では異なる時点の証拠を2件以上選ぶ
- `not_evaluable_reason`はnull
- 発言量、言い方、性格印象を根拠にしない

## 5. NE評価

- `selected_evidence_message_ids`は空
- `not_evaluable_reason`を必須にする
- 機会不足やAI品質不良をscore 1へ置き換えない
- 低品質だからという理由でNEにしない

主な理由:

- `INSUFFICIENT_OPPORTUNITY`
- `AI_QUALITY_FAILURE`
- `TRANSCRIPT_INCOMPLETE`
- `SCENARIO_CONTRACT_FAILURE`
- `INSUFFICIENT_EVIDENCE`

## 6. 境界説明

### 1とNE

- 十分な機会があり、期待行動が観察されない: score 1
- 機会自体が不足・失効し、採点不能: NE

### 2と3

- 一部行動はあるが表面的・不完全・不安定: score 2
- 期待行動が明確で、議論へ有効に作用: score 3

### 3と4

- 一つの場面で期待行動を十分実施: score 3
- 複数場面で高度な行動を行い、チームや議論構造を改善: score 4

## 7. Rating形式

```json
{
  "contract_version": "0.1",
  "rating_version": "micro-anchor-rating-v0.1",
  "blind_anchor_id": "blind-001",
  "rater_id": "rater-001",
  "rubric_version": "candidate-behavior-v0.1",
  "target_dimension": "issue_framing",
  "opportunity_status": "sufficient",
  "selected_evidence_message_ids": ["m003"],
  "assigned_score": 3,
  "not_evaluable_reason": null,
  "confidence": 0.82,
  "notes": ""
}
```

## 8. 独立性

- 他評価者の点数・証拠・コメントを見ない
- AIの期待点を見ない
- 評価完了後まで正本アンカーを開かない
- 不一致は多数決ではなく、機会、証拠、Rubric境界の順に調停する

## 9. 現在の状態

Issue Framing 5件はblind rating用にexport可能だが、まだ`draft`である。35件完成と二重評価前に`approved`として扱わない。
