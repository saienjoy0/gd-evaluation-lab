---
title: Exercise C System Failure v0.1 Decision
type: decision
tags: [gd, evaluation, exercise-c, system-failure]
permalink: exercise-c-system-failure-v0-1-decision
updated: 2026-08-06
---

# Exercise C System Failure v0.1 Decision

## Decision

Exercise Cのsystem_failureは、AIが遅延リスク開示前に結論を確定する`C-PROH-01`単独故障として作成する。

AI差分はm025のtextとmoveだけに限定し、候補者発言、候補者event、時刻、phase、generation IDはmediumから変更しない。

## Causal Scope

Scenario契約で`C-PROH-01`に紐づく7評価機会だけをinvalidにする。

- logical reasoning: 2件
- listening and response: 2件
- decision and consensus: 3件

この3軸を`AI_QUALITY_FAILURE`でNEとし、issue framing、valuable contribution、collaboration and relationship、process and time managementはmediumの数値評価を維持する。

## Rejected Alternatives

- C-PROH-02を同時に失敗させる複合故障
- 候補者発言を弱くしてsystem_failureを作る方法
- invalid機会がある軸を無理に数値評価する方法
- 影響外軸まで一律NEにする方法

これらは候補者品質とAI品質の分離を曖昧にするため採用しない。

## Validation Boundary

system_failureではC-PROH-01のみfail、C-PROH-02とC-R01〜C-R05はpassを期待する。LowはAI品質pass、15機会observed、7軸数値を維持し、system_failureとの差を固定する。

## Consequence

この決定の完了後、Exercise Cのhigh / medium / low / system_failureを横断する4状態マトリクスを作成できる。

## Relations

- follows [[Exercise C High Low Calibration v0.1 Decision]]
- updates [[GD Evaluation Lab Current Status]]
