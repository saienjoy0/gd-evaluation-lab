---
title: Current Status
type: status
tags: [gd, evaluation, status]
permalink: gd-evaluation-current-status
updated: 2026-08-05
---

# Current Status

## Observations

- [phase] Exercise A system_failure縦切りの準備
- [completed] 評価研究を`gd-app`から別リポジトリへ分離した
- [completed] 利用者7軸、表示3領域、1〜4＋NE、AI品質分離の方針を決めた
- [completed] Scenario、Episode、Annotation、Evaluation Result契約v0.1を作成した
- [completed] 証拠先行の人間評価ガイド、Rater Sheet、Adjudication、検証計画を実装した
- [completed] 標準演習A・B・C、評価機会マトリクス、positive/negative/NE fixtureを実装した
- [completed] 評価機会ID、構造化rule、共通NE、証拠所有者、3領域暫定出力、move語彙を堅牢化した
- [completed] 演習A mediumをScenarioからFeedbackまで通した
- [completed] 共通Full-Episode runnerへ一般化し、stateに依存しない決定論的再生成を実装した
- [completed] 演習A high / medium / lowを同じAI品質・同じ12機会で校正し、全7軸の順序を検証した
- [next] 演習A system_failureを追加し、システム欠陥によるNEと利用者低得点を分離する
- [next] Exercise A 4状態マトリクスを完成させる
- [next] 35マイクロアンカーと残りの完全Episodeを仕様に従って作成する
- [later] 演習B・Cへの展開、System Quality Gateのgd-app接続、Evidence-first Judge、GD APP Episode Exporterへ進む

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise A Medium Vertical Slice v0.1 Decision]]
- informed_by [[Exercise A High Low Calibration v0.1 Decision]]
