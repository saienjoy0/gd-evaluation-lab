---
title: Exercise B High Low Calibration v0.1 Decision
type: decision
tags: [gd, evaluation, calibration, exercise-b]
permalink: exercise-b-high-low-v0-1-decision
date: 2026-08-05
---

# Exercise B High / Low Calibration v0.1 Decision

## Decision

Exercise Bの正常3状態を、同一AI発言・同一System Quality・同一15評価機会で校正する。

スコア正本は次とする。

- high: `4/4/4/4/4/4/3`
- medium: `3/3/3/3/3/3/2`
- low: `1/1/2/1/1/1/1`

全7軸で`high > medium > low`を要求する。

## Evidence policy

- lowでも15機会すべてに候補者応答を残し、機会不足を低得点へ混ぜない
- 4点は最低2証拠かつ複数phaseを要求する
- 同軸primary opportunityの最低数を満たしたうえで、明示的なauxiliary opportunityを許可する
- auxiliary-only scoringは禁止する
- 候補者本人のOpportunity応答以外を数値証拠に使用しない

## State independence

状態名はcase profileと検査コードだけで扱う。`RuntimeCase`と`gd_eval`評価コアへstateを渡さず、状態別の分岐を追加しない。

共通校正支援は`scripts/calibration_controlled_states.py`へ置く。`gd_eval`配下は生成・評価コアとして状態語彙ゼロを維持する。

## Low rule profile

lowでは次を候補者行動のfailとして扱う。

- B-R02: 懸念への有効な直接応答なし
- B-R03: 複数立場の統合なし
- B-R04: 緩和策を含む結論なし

一方、AI品質と予算契約は正常に保つ。

- B-R01: pass
- B-R05: pass
- B-R06: pass
- B-PROH-01: pass
- B-PROH-02: pass

## Consequences

この決定により、Exercise B system_failureでは候補者低品質とAI品質不良を独立して比較できる。次のPRでは、AIが対立前に配分を確定する失敗を作り、影響軸だけをNEにする。

## Relations

- follows [[Exercise B Medium Vertical Slice v0.1 Decision]]
- informed_by [[Exercise A Four-State Matrix v0.1 Decision]]
- part_of [[GD Evaluation Lab Project Overview]]
