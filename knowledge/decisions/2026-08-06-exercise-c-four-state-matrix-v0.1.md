---
title: Exercise C Four-State Matrix v0.1 Decision
type: decision
tags: [gd, evaluation, exercise-c, matrix]
permalink: exercise-c-four-state-matrix-v0-1-decision
updated: 2026-08-06
---

# Exercise C Four-State Matrix v0.1 Decision

## Observations

- Exercise Cのhigh、medium、low、system_failureはすべてFull-Episode fixtureとして完成している。
- 正常3状態は同じAI発言、同じSystem Quality、同じ15評価機会で校正されている。
- system_failureはm025のtextとmoveだけを変更した`C-PROH-01`単独故障である。
- system_failureでは7機会がinvalidとなり、3軸だけが`AI_QUALITY_FAILURE`でNEになる。
- Exercise A・Bでは共通matrix checker、Schema、JSON、Markdown正本を使う方式が確立している。

## Decision

Exercise Cの4状態を既存の`calibration_four_state_matrix.py`へ接続し、Exercise C専用checkerは演習固有の期待値とm025単一差分検査だけを保持する。

共通評価中核へstate分岐を追加せず、matrix期待値は校正層に閉じ込める。

## Matrix Profile

| state | System Quality | offered | invalid | numeric | NE |
|---|---|---:|---:|---:|---:|
| high | pass | 15 | 0 | 7 | 0 |
| medium | pass | 15 | 0 | 7 | 0 |
| low | pass | 15 | 0 | 7 | 0 |
| system_failure | fail | 8 | 7 | 4 | 3 |

正常3状態は全7軸で`high > medium > low`とする。lowは全機会が観察可能なためNEを許可しない。

system_failureのNE範囲はlogical reasoning、listening and response、decision and consensusに限定し、影響外4軸はmediumの数値を維持する。

## Controlled Failure

mediumとsystem_failureの候補者発言は同一にする。AI差分はm025のtextとmoveだけとし、その他の制御項目とAI発言は変更しない。

失敗System Quality ruleは`C-PROH-01`だけとする。C-PROH-02とC-R01〜C-R05はpassを維持する。

## Artifacts

- `scripts/check_exercise_c_four_state_matrix.py`
- `fixtures/calibration/matrices/exercise-c-four-state-v0.1.json`
- `fixtures/calibration/matrices/exercise-c-four-state-v0.1.md`
- `docs/EXERCISE_C_FOUR_STATE_MATRIX_V0.1.md`
- Exercise C conditional profileを追加したmatrix Schema

## Rejected Alternatives

- Exercise C専用の別matrix frameworkを作る方法
- system_failureの候補者発言を変更する方法
- AI品質失敗を理由に7軸すべてをNEにする方法
- 保存済みmatrixを評価入力として利用する方法
- stateラベルをrunnerへ渡して結果を分岐する方法

これらは共通化、因果的NE、state非依存、決定論的再生成を損なうため採用しない。

## Consequence

Exercise C matrix完成後、標準演習A・B・Cの4状態校正が揃う。次工程は35マイクロアンカー作成とする。

## Relations

- follows [[Exercise C System Failure v0.1 Decision]]
- follows [[Exercise C High Low Calibration v0.1 Decision]]
- informed_by [[Exercise B Four-State Matrix v0.1 Decision]]
- updates [[GD Evaluation Lab Current Status]]
