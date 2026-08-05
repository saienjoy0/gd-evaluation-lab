---
title: Exercise A System Failure Separation v0.1 Decision
type: decision
tags: [gd, evaluation, exercise-a, system-quality, ne, calibration]
permalink: exercise-a-system-failure-separation-v0-1
updated: 2026-08-05
---

# Exercise A System Failure Separation v0.1

## Observations

- Exercise Aのhigh、medium、lowではAI品質と評価機会を正常に保ち、利用者行動差を数値評価できる
- lowケースをNEへ変換すると、利用者の観察可能な弱い行動と評価機会不足を混同する
- System Qualityがfailでも、その失敗が全7軸の評価機会を破壊するとは限らない
- 無効化された評価機会をNEの根拠として記録するには、Rater Sheetがinvalid event IDを保持できる必要がある

## Decision

- system_failureケースではAIが利用者より先にscopeを定義する`A-PROH-01`を発生させる
- `A-PROH-01`が無効化する5機会を明示的に`invalid`とする
- 影響を受ける`issue_framing`と`valuable_contribution`だけを`NE / AI_QUALITY_FAILURE`とする
- 影響を受けない5軸は利用者本人の証拠から数値評価を維持する
- `AI_QUALITY_FAILURE`によるNEは、失敗ruleの影響軸とinvalid機会の両方が存在するときだけ許可する
- invalid機会への数値採点は拒否し、lowケースは全7軸の数値評価を維持する

## Consequence

Exercise Aでは、利用者の低い行動とシステム欠陥による評価不能を機械的に区別できる。次はhigh、medium、low、system_failureの4状態を横断し、評価機会、AI品質、数値・NEの伝播規則を一つのマトリクスとして確定する。

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise A High Low Calibration v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
