---
title: Exercise A Four-State Matrix v0.1 Decision
type: decision
tags: [gd, evaluation, exercise-a, calibration, matrix, ne]
permalink: exercise-a-four-state-matrix-v0-1
updated: 2026-08-05
---

# Exercise A Four-State Matrix v0.1

## Observations

- Exercise Aには`high`、`medium`、`low`、`system_failure`の完全Episodeが個別に存在する
- 正常3状態は同じAI発言、System Quality、12評価機会の下で利用者行動だけを変えている
- `low`は機会が十分にあるため全7軸を数値評価し、低い行動をNEへ逃がしてはならない
- `system_failure`はAI先回りにより5機会が無効化され、影響2軸だけが評価不能になる
- 個別checkerだけでは、4状態全体の順序、統制条件、NE伝播、state非依存を一つの契約として説明できない

## Decision

- 4状態をrunner出力から毎回再構築する一つの横断マトリクスとして管理する
- 正常3状態でAI発言、System Qualityの意味的結果、評価機会供給が一致することを必須化する
- 全7軸で`high > medium > low`を必須化する
- lowは7軸すべて数値、system_failureは影響2軸だけNEとする
- system_failureの非影響5軸はmediumと同じ数値を維持する
- 共通runnerへstateを渡さず、評価中核に状態文字列をハードコードしない
- JSONとMarkdownのマトリクスは生成完了後のtest oracleとしてのみ使用し、生成入力には使用しない
- Schema、JSON正本、Markdown正本、横断checkerをCIで同時に検査する

## Consequence

Exercise Aはv0.1校正セットとして、正常な能力差とシステム起因NEを一つの決定論的基盤で説明できる。次は同じ共通runnerと証拠契約をExercise B・Cへ展開する。

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise A System Failure Separation v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
