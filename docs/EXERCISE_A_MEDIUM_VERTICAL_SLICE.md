# Exercise A Medium Vertical Slice v0.1

## 1. 目的

標準演習A「曖昧な課題の構造化」について、Scenarioから最終EvaluationResultまでを一度通し、契約間の欠落を発見する。

本縦切りは合成データによるPhase A検証であり、LLM Judgeや採用判断には使用しない。

## 2. パイプライン

```text
Scenario A
→ Episode
→ DeterministicRuleResult
→ SystemQualityResult
→ OpportunityResolution
→ Rater Sheet A / B
→ Adjudication
→ EvaluationResult
→ 3領域フィードバック
```

`DeterministicRuleResult`はAI、Episode、利用者を対象とする構造化ruleの結果を保持する。`SystemQualityResult`には、そのうちAI/system対象のruleと禁止条件だけを入れる。利用者の未達をAI品質不良として扱わない。

## 3. mediumケース

利用者は対象、利用時間、比較基準を設定し、AIの懸念を実施条件へ反映する。一方で、定量根拠、参加促進、中盤の時間管理は限定的とする。

全7軸に有効な評価機会を提供し、次の境界差を含める。

- `issue_framing`: 3対2
- `valuable_contribution`: 2対3
- `collaboration_and_relationship`: 3対2

## 4. 決定論的再生成

`scripts/evaluate_exercise_a_medium.py`はEpisode内の構造化イベントから次を順番に再生成する。

- Deterministic Rule Result
- System Quality Result
- Opportunity Resolution
- Evaluation Result
- Evidence-based Feedback

FeedbackをEvaluationResultの入力には使用しない。EvaluationResultを作成した後、その内容からFeedbackを生成する。

`check_exercise_a_medium_vertical_slice.py`は再生成結果をgolden fixtureと完全一致で比較する。

## 5. 保存場所

```text
fixtures/calibration/full-episodes/ambiguous-structure/medium/
```

Scenario本体は既存の標準演習Aを参照し、複製しない。

## 6. 受入れ条件

- 4つの新規Schemaと既存Schemaへ適合する
- Scenario、Episode、各中間結果の版が一致する
- transcript hashを再計算できる
- 12の評価機会IDが全て解決される
- 評価機会の応答と能力評価の証拠が対象利用者本人の発言である
- AI/system ruleだけがSystemQualityResultへ入る
- 二重評価と調停結果が一致する
- 3領域の数値は校正前のため`null`
- 同一入力から9成果物の同じ内容を再生成できる
- 14件の負例が意図した理由で失敗する
- AIが利用者より先にscopeを定義した場合、critical failureを検出する
