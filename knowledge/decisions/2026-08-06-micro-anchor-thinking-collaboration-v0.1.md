---
title: Micro Anchor Thinking Collaboration v0.1 Decision
type: decision
tags: [gd, evaluation, micro-anchor, calibration]
permalink: gd-evaluation-micro-anchor-thinking-collaboration-v0-1
updated: 2026-08-06
---

# Micro Anchor Thinking + Collaboration v0.1 Decision

## Observations

- [decision] 既存基盤を再利用し、4軸20件だけを追加する
- [decision] 軸ごとの新しいSchema・checker・負例は作らない
- [decision] score 1〜4は同一会話骨格で候補者行動だけを変える
- [decision] score 4は異なるphaseの証拠を2件要求する
- [decision] NEは低品質行動ではなく評価機会不成立として作る
- [decision] Blind Pack全文の重複保存を避け、生成結果の件数とSHA-256を正本とする
- [completed] logical_reasoningの5アンカーを追加した
- [completed] valuable_contributionの5アンカーを追加した
- [completed] listening_and_responseの5アンカーを追加した
- [completed] collaboration_and_relationshipの5アンカーを追加した
- [completed] ManifestとBlind Pack oracleを25件へ更新した
- [next] decision_and_consensusとprocess_and_time_managementの10件を追加する

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Micro Anchor Foundation and Issue Framing v0.1 Decision]]
- informed_by [[35 Micro Anchors Specification v0.1]]
