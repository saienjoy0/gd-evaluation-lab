---
title: Exercise C High Low Calibration v0.1 Decision
type: decision
tags: [gd, evaluation, exercise-c, calibration]
permalink: exercise-c-high-low-calibration-v0-1-decision
status: accepted
updated: 2026-08-06
---

# Exercise C High Low Calibration v0.1 Decision

## Observations

- [decision] Exercise Cの正常3状態は、同一Scenario、同一AI発言、同一System Quality、同一15評価機会を維持し、候補者発言と人間評価だけを変える
- [decision] 点数プロファイルはhigh `3/4/4/4/4/4/4`、medium `2/3/3/2/2/3/3`、low `1/1/2/1/1/1/1`とする
- [decision] issue_framingはC-OP-IS-01の単一評価機会しかないため、score 4に必要な複数証拠を捏造せずhighを3とする
- [decision] highのscore 4は、同一phaseだけの反復ではなく複数phaseの候補者証拠を必須とする
- [decision] lowは評価機会不足ではなく観察された低品質行動として扱い、全7軸を数値評価しNEを使わない
- [decision] lowではC-R01とC-R02をpassに保ち、候補者起因のC-R03、C-R04、C-R05だけをfailにする
- [decision] lowのFeedbackはstrengthを空とし、各表示領域は不足行動を要約する
- [decision] generatorはmedium fixtureからhigh/lowを決定論的に再構成し、CIは保存fixtureとの差分ゼロを要求する
- [constraint] runtimeへhigh、medium、lowのstate名を渡さず、評価コアに状態別分岐を追加しない
- [constraint] system_failureは候補者品質の校正と混ぜず、次の独立PRでAI起因の機会欠損として作る

## Score Matrix

| Dimension | High | Medium | Low |
|---|---:|---:|---:|
| issue_framing | 3 | 2 | 1 |
| logical_reasoning | 4 | 3 | 1 |
| listening_and_response | 4 | 3 | 2 |
| valuable_contribution | 4 | 2 | 1 |
| collaboration_and_relationship | 4 | 2 | 1 |
| decision_and_consensus | 4 | 3 | 1 |
| process_and_time_management | 4 | 3 | 1 |

## Deterministic Rule Profiles

| State | C-R01 | C-R02 | C-R03 | C-R04 | C-R05 |
|---|---|---|---|---|---|
| high | pass | pass | pass | pass | pass |
| medium | pass | pass | pass | pass | pass |
| low | pass | pass | fail | fail | fail |

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise C Medium Vertical Slice v0.1 Decision]]
- updates [[Current Status]]
- next [[Exercise C System Failure Separation v0.1 Decision]]
