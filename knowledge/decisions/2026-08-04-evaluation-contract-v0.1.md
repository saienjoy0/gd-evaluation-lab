---
title: Evaluation Contract v0.1 Decision
type: decision
tags: [evaluation, contract, rubric, scenario, evidence]
permalink: evaluation-contract-v0-1-decision
date: 2026-08-04
status: accepted
---

# Evaluation Contract v0.1 Decision

## Observations

- [decision] 利用者評価は内部7軸、画面表示は3領域とする
- [decision] 採点尺度は1〜4とNEを使用する
- [decision] 全スコアに実在する発言IDの証拠を要求する
- [decision] 4点には原則2件以上の独立した証拠を要求する
- [decision] AI参加者品質を利用者評価の前に判定する
- [decision] シナリオ、エピソード、人間注釈、評価結果を別オブジェクトとして保存する
- [decision] 各シナリオへ固有のbinary rubricと評価機会を持たせる
- [decision] 新評価は旧評価を直ちに置き換えずshadow modeで比較する
- [decision] v0.1は練習・研究用であり採用合否の自動決定には使用しない
- [reason] 発言量や総合印象への依存を減らし、再採点・監査・人間校正を可能にする
- [next] gd-appがEvaluation Contract v0.1のEpisodeを出力できるようにする
- [next] 6種類のシナリオとinstance-level rubricを追加する
- [next] 現在の決定論的品質ハーネスを新契約へ対応させる

## Relations

- governs [[GD Evaluation Lab Project Overview]]
- updates [[Current Status]]
- follows [[Memory and Task Architecture Decision]]
