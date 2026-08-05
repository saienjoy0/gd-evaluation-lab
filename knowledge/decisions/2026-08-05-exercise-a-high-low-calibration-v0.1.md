---
title: Exercise A High Low Calibration v0.1 Decision
type: decision
tags: [gd, evaluation, calibration, exercise-a, full-episode]
permalink: exercise-a-high-low-calibration-v0-1
updated: 2026-08-05
---

# Exercise A High Low Calibration v0.1

## Observations

- Generic Full-Episode Runner v0.1により、state名を評価ロジックへ渡さず複数ケースを実行できる
- mediumだけでは、高得点・低得点・NEの境界を横断比較できない
- lowケースでも評価機会が有効なら、利用者の弱い行動をNEではなく数値評価する必要がある
- 従来のFeedback Builderは低得点ケースにも強み見出しを表示し得た

## Decision

- Exercise Aへhighとlowの完全Episodeを追加する
- high、medium、lowでScenario、AI品質、12評価機会を統制する
- 全7軸で`high > medium > low`を成立させ、差を利用者本人の発言証拠で説明する
- lowは全機会が有効なため1〜2点を使用し、system failure用のNEと分離する
- Feedbackのstrength候補は3点以上の軸に限定する
- runtimeへstate別の点数分岐を追加しない

## Consequence

Exercise Aでは、正常なAI環境下におけるhigh、medium、lowの三水準を同じrunnerで比較できる。次はsystem_failureを追加し、システム欠陥によるNEと利用者低得点の差を検証する。

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise A Medium Vertical Slice v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
