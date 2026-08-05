---
title: Exercise B System Failure v0.1 Decision
type: decision
tags: [gd, evaluation, calibration, exercise-b, system-quality]
permalink: exercise-b-system-failure-v0-1-decision
updated: 2026-08-05
---

# Exercise B System Failure v0.1 Decision

## Observations

- Exercise Bの正常3状態は同じAI品質・同じ15評価機会で校正済みである
- lowは全15機会が提供され、7軸すべてを数値評価する
- Scenario Bでは`B-PROH-01`が課題設定1機会と意思決定3機会を無効化する
- 現行の`finalize_before_conflict`は、候補者の最初の発言より前のAI配分決定を検出できる
- m004以外を変更すると、複数のsystem failureが混ざり因果範囲が不明瞭になる
- System Quality ruleのaffected dimensionだけではNEにせず、因果的invalid機会と有効機会不足が必要である

## Decision

mediumのm004だけを、比較基準を尋ねる`ask_question`から、候補者より前に配分を確定する`propose_decision`へ変更する。

新しい本番ルールやstate分岐は追加しない。既存のSystem Quality、Opportunity Resolver、NE因果検査をそのまま使用する。

## Failure profile

- `B-R01`〜`B-R06`: pass
- `B-PROH-01`: fail
- `B-PROH-02`: pass
- System Quality: fail
- invalid opportunities: `B-OP-IS-01`, `B-OP-DE-01`, `B-OP-DE-02`, `B-OP-DE-03`

## Evaluation profile

次の2軸だけを`NE / AI_QUALITY_FAILURE`とする。

- `issue_framing`
- `decision_and_consensus`

影響外5軸はmediumと同じ数値を維持する。

- `logical_reasoning`: 3
- `listening_and_response`: 3
- `valuable_contribution`: 3
- `collaboration_and_relationship`: 3
- `process_and_time_management`: 2

## Evidence policy

NEには、失敗したSystem Quality rule、同じruleによるinvalid機会、必要数未満の有効機会、空の最終証拠を必須とする。

一部機会がinvalidでも必要数の有効機会が残る場合は、NEを拒否して数値評価を維持する。

## Consequence

Exercise Bで、候補者underperformanceとAI品質不良を機械的に分離できる。次のPRではhigh、medium、low、system_failureを4状態マトリクスへ統合する。

## Relations

- follows [[Exercise B High Low Calibration v0.1 Decision]]
- informed_by [[Exercise A System Failure v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
- part_of [[GD Evaluation Lab Project Overview]]
