---
title: Contract and Scenario Hardening v0.1 Decision
type: decision
tags: [gd, evaluation, contract, scenario, hardening]
permalink: contract-scenario-hardening-v0-1
updated: 2026-08-04
---

# Contract and Scenario Hardening v0.1

## Decision

縦切り試験へ進む前に、評価契約と標準Scenarioを次の6点で堅牢化する。

1. 評価機会を整数からID付きオブジェクトへ変更する
2. instance rubricの自由記述`pass_condition`を構造化ruleへ変更する
3. NE理由コードを全Schemaで統一する
4. EvaluationResultの証拠を対象利用者本人の発言へ限定する
5. 3領域の数値を校正完了まで出さない
6. move、actor、phase、禁止条件を分離し共通語彙で検査する

## Additional safeguards

- question probabilitiesの合計を1にする
- 4点の証拠を異なるphaseから要求する
- 二重評価者と調停者のID重複を拒否する
- `agreement_class`を二人の点数から再計算する
- 負例テストは期待したエラー理由まで照合する

## Consequence

次の縦切り試験は、曖昧な自然文条件や恣意的な3領域平均を実装側で補わずに実行できる。
