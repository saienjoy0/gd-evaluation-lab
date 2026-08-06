---
title: Micro Anchor Progress Completion v0.1 Decision
type: decision
tags: [gd, evaluation, micro-anchor, calibration]
permalink: micro-anchor-progress-completion-v0-1-decision
updated: 2026-08-06
---

# Decision

Decision and ConsensusとProcess and Time Managementのscore 1 / 2 / 3 / 4 / NEを既存基盤へ追加し、35 / 35を完成する。

## Observations

- 既存5軸はscore 1 / 2 / 3 / 4 / NEまで実装済みである
- 残る2軸も同じSchema、controlled ladder、Manifest、Blind Pack契約で表現できる
- 35件完成後も個別アンカーは人間校正前の`draft`である
- 次工程は2名による10件のBlindパイロットである

## Boundaries

- 1点は十分な機会があるが対象行動が不足または議論を妨げる
- NEはAI先回りまたは記録欠損で評価機会が成立しない
- 3点は議論を具体的に前進させる
- 4点は異なるphaseの二証拠で全体構造を改善する

## Approval

Anchor Setは35件完成後`blind_calibration_pending`とする。各アンカーは人間評価前のため`draft`を維持し、`approved`にはしない。

## Next

2名の評価者による10件のBlindパイロットを実施する。

## Relations

- follows [[Micro Anchor Thinking and Collaboration v0.1 Decision]]
- follows [[Micro Anchor Foundation and Issue Framing v0.1 Decision]]
- part_of [[GD Evaluation Lab Project Overview]]
