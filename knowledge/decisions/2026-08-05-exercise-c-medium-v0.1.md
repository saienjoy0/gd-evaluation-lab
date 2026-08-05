---
title: Exercise C Medium Vertical Slice v0.1 Decision
type: decision
tags: [gd, evaluation, exercise-c, time-boxed-decision, calibration]
permalink: exercise-c-medium-v0-1
updated: 2026-08-05
---

# Exercise C Medium Vertical Slice v0.1

## Observations

- Exercise A・Bでは課題構造化と利害対立を校正したが、時間圧下の優先順位変更は未検証だった
- Exercise C Scenarioには40%・75%時間通知、遅延リスク、三案比較、条件付き合意、最終要約が定義済みだった
- 現行runnerにはC固有のrule、System Quality禁止条件、Opportunity trigger/contextが未接続だった
- 時間通知の存在だけでは候補者の時間管理機会を保証できず、通知後の候補者ターンと優先順位更新を検査する必要がある
- AIが遅延リスク前に結論を確定した場合、候補者の論理・応答・合意形成機会が失われる

## Decision

- C固有ruleを純粋な証拠検査として専用モジュールへ追加し、stateやexercise IDによる採点分岐は作らない
- 40%・75%時間通知の時刻許容幅をセッション長の5%、候補者応答猶予を90秒とする
- `TIME_CHECKPOINT_REACHED`、`PRIORITY_UPDATE_RECORDED`、`OPTIONS_COMPARED`、`DECISION_REVISION_RECORDED`を主要構造化証拠とする
- 遅延リスクはScenario内AI participantのprivate concernと完全一致させ、decision開始前の開示を要求する
- `finalize_before_risk_reveal`と`skip_summary`をSystem Quality禁止条件として追加する
- mediumでは15機会すべてを`offered + observed`とし、NEを使用しない
- medium score profileを`2/3/3/2/2/3/3`とする
- 最終結論は条件付きハイブリッドとし、`mode / exception / next_check`を要約へ含める
- Episodeは圧縮正本から決定論的に復元し、5種goldenを共通runnerで再生成する
- 正常系、Schema、manifest、17件の負例、A・B回帰をCIで検査する

## Consequence

Exercise C mediumはScenarioからFeedbackまで共通runnerへ接続され、時間通知後の候補者調整、遅延リスク後の案修正、条件付き合意を評価できる。次は同じAI発言、System Quality、15機会を統制したままhigh / lowを校正する。

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise B Four-State Matrix v0.1 Decision]]
- informs [[GD Evaluation Current Status]]
