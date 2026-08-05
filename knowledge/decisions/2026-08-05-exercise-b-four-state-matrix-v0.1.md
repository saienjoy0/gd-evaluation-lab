---
title: Exercise B Four-State Matrix v0.1 Decision
type: decision
tags: [gd, evaluation, calibration, exercise-b, matrix]
permalink: exercise-b-four-state-matrix-v0-1-decision
updated: 2026-08-05
---

# Exercise B Four-State Matrix v0.1 Decision

## Observations

- Exercise Bにはhigh、medium、low、system_failureの4完全Episodeが存在する
- 正常3状態は同じAI品質・同じ15評価機会で校正されている
- lowは全7軸を数値評価し、NEを含まない
- system_failureは`B-PROH-01`による4機会invalidと2軸NEを持つ
- system_failureの影響外5軸はmediumと同値である
- Exercise Aには同じ目的の4状態マトリクスcheckerがある
- A専用checkerを複製すると、state非依存検査やSchema処理が二重管理になる

## Decision

Exercise AとBの4状態横断検査を`scripts/calibration_four_state_matrix.py`へ共通化する。

演習別checkerは、case root、正本パス、Opportunity件数、system_failureのNE範囲、失敗ruleだけを設定する。評価中核の`gd_eval`へstate名やcase IDによる分岐を追加しない。

既存の`exercise-four-state-matrix-v0.1.schema.json`は、Exercise AとBの両マトリクスを条件付きで厳密に検証できる共通Schemaへ拡張する。

## Matrix profile

| state | System Quality | offered | invalid | 数値軸 | NE軸 |
|---|---|---:|---:|---:|---:|
| high | pass | 15 | 0 | 7 | 0 |
| medium | pass | 15 | 0 | 7 | 0 |
| low | pass | 15 | 0 | 7 | 0 |
| system_failure | fail | 11 | 4 | 5 | 2 |

## Causal separation

system_failureでNEにするのは次の2軸だけとする。

- `issue_framing`
- `decision_and_consensus`

次の5軸はmediumと同じ数値を維持する。

- `logical_reasoning`
- `listening_and_response`
- `valuable_contribution`
- `collaboration_and_relationship`
- `process_and_time_management`

候補者発言はmediumと完全同一にし、AI差分はm004の本文とmoveだけに限定する。

## Consequence

Exercise Bの候補者underperformanceとAI品質不良を、一つの決定論的マトリクスで説明・再生成できる。

Exercise AとBが共通の4状態検査基盤を使用するため、次のExercise C展開では演習固有差分だけを追加すればよい。

## Relations

- follows [[Exercise B System Failure v0.1 Decision]]
- informed_by [[Exercise A Four-State Matrix v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
- part_of [[GD Evaluation Lab Project Overview]]
