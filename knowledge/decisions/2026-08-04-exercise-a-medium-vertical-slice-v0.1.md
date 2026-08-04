---
title: Exercise A Medium Vertical Slice v0.1 Decision
type: decision
tags: [gd, evaluation, vertical-slice, exercise-a, calibration]
permalink: exercise-a-medium-vertical-slice-v0-1
updated: 2026-08-04
---

# Exercise A Medium Vertical Slice v0.1

## Observations

- Contract and Scenario Hardening v0.1により、機会ID、構造化rule、証拠所有者、共通NEを利用できる
- SystemQualityResultとOpportunityResolutionの独立保存契約は未実装だった
- Judge導入前に、合成Episodeを最後まで通して契約境界を検査する必要がある

## Decision

- 最初の完全Episodeは標準演習Aのmediumケースとする
- 全7軸へ有効な評価機会を提供する
- 人間評価者2名の隣接差と調停履歴を含める
- LLMを呼ばず、構造化イベントから中間結果と最終結果を再生成する
- 3領域は数値化せず、coverage、bottleneck、文章要約を返す

## Consequence

この縦切りが通れば、同じ仕組みを演習Aのhigh、low、system_failureへ展開できる。

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Contract and Scenario Hardening v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
