---
title: Exercise B Medium Vertical Slice v0.1 Decision
type: decision
tags: [gd, evaluation, exercise-b, stakeholder-conflict, calibration]
permalink: exercise-b-medium-v0-1
updated: 2026-08-05
---

# Exercise B Medium Vertical Slice v0.1

## Observations

- Exercise Bは三つの利害、反対意見、少数意見、配分制約、未採用施策への緩和策を扱う
- Scenarioには15評価機会があるが、B固有のrule、quality rule、trigger、contextは共通runnerへ未接続だった
- B-PROH-01とB-PROH-02の影響軸は、実際に無効化できるOpportunity dimensionと一致していなかった
- 自然言語だけでは、懸念への応答、複数立場の統合、予算総額、重点施策数を安定して監査できない
- high / low / system_failureを追加する前に、mediumを縦に通してB固有契約を固定する必要がある

## Decision

- B固有の決定論的ruleをID registryへ追加し、exercise IDによる分岐は作らない
- 懸念応答、立場統合、配分、緩和策、少数意見を構造化Episode Eventとして記録する
- B-PROH-01の影響軸へ`issue_framing`を追加する
- B-PROH-02の影響軸へ`listening_and_response`を追加する
- 配分総額3000万円と重点施策二つ以下をB-R06で検査する
- 数値制約ハンドラは既存形式との後方互換性を維持する
- mediumでは全15機会を`offered + observed`とし、全7軸を数値評価する
- medium score profileを`3/3/3/3/3/3/2`とする
- runner出力、Schema、manifest、9件の負例をCIで検査する

## Consequence

Exercise BはScenarioからFeedbackまで共通runnerで再生成できる。次はAI発言、System Quality、15機会を統制したまま候補者行動だけを変え、high / lowを校正する。

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise A Four-State Matrix v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
