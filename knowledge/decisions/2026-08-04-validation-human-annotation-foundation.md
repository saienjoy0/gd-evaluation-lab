---
title: Validation and Human Annotation Foundation Decision
type: decision
tags: [gd, evaluation, validation, annotation]
permalink: validation-human-annotation-foundation-decision
updated: 2026-08-04
---

# Validation and Human Annotation Foundation Decision

## Observations

- [decision] Judge、GD APP接続、結果UIより先に、人間が同じ手順で証拠先行採点できる基盤を確定する
- [reason] 人間基準がなければJudgeの良否を判定できない
- [reason] 評価機会不足と低得点の混同を防ぐ必要がある
- [reason] AI品質不良を利用者能力へ転嫁してはならない
- [reason] 不一致を点数差だけでなく、機会・証拠・アンカーの問題へ分解する必要がある
- [scope] 検証計画、人間評価ガイド、Rater Sheet Schema、Adjudication Schemaを作る
- [scope] 35マイクロアンカー仕様、12完全Episode仕様、正例fixture、負例CIを作る
- [non_goal] 35アンカー実データ、標準3演習、LLM Judge、GD APP Episode Exporter、本番UIは後続PRへ分離する
- [consequence] PR #4以降は、本決定で定めた評価者手順と検証ゲートを満たす

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Evaluation Contract v0.1 Decision]]
- updates [[Current Status]]
