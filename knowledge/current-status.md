---
title: Current Status
type: status
tags: [gd, evaluation, status]
permalink: gd-evaluation-current-status
updated: 2026-08-06
---

# Current Status

## Observations

- [phase] 35マイクロアンカーのProgress領域拡張準備（25 / 35実装済み）
- [completed] 評価研究を`gd-app`から別リポジトリへ分離した
- [completed] 利用者7軸、表示3領域、1〜4＋NE、AI品質分離の方針を決めた
- [completed] Scenario、Episode、Annotation、Evaluation Result契約v0.1を作成した
- [completed] 証拠先行の人間評価ガイド、Rater Sheet、Adjudication、検証計画を実装した
- [completed] 標準演習A・B・C、評価機会マトリクス、positive/negative/NE fixtureを実装した
- [completed] 評価機会ID、構造化rule、共通NE、証拠所有者、3領域暫定出力、move語彙を堅牢化した
- [completed] 演習A・B・Cのhigh / medium / low / system_failureを共通runnerとmatrix checkerで校正した
- [completed] 標準演習A・B・Cすべてで候補者行動差とAI品質不良を分離した
- [completed] Micro Anchor、Anchor Set Manifest、Blind Ratingの3つのSchemaを作成した
- [completed] contract checker、controlled ladder checker、blind exporter、17件のnegative suiteを実装した
- [completed] Issue Framingのscore 1 / 2 / 3 / 4 / NEを同一scenario familyと同一opportunityで実装した
- [completed] Logical Reasoningのscore 1 / 2 / 3 / 4 / NEを食品ロス施策比較で実装した
- [completed] Valuable Contributionのscore 1 / 2 / 3 / 4 / NEを既出案改善で実装した
- [completed] Listening and Responseのscore 1 / 2 / 3 / 4 / NEを勤務制度の対立処理で実装した
- [completed] Collaboration and Relationshipのscore 1 / 2 / 3 / 4 / NEを反対意見と発言偏り調整で実装した
- [completed] score 1〜4の非対象発言、発言順、候補者ターン位置を同一にし、候補者のtextとmoveだけを変える統制を維持した
- [completed] 各score 4は異なるphaseの2証拠を持ち、NEは評価機会不成立として数値評価から分離した
- [completed] candidate総文字数比を1.8倍以内に保ち、発言量を得点の代理変数にしない統制を維持した
- [completed] Manifestを25 / 35へ更新し、各アンカーを人間校正前のdraftとして維持した
- [completed] Blind Packは期待値を除去して生成し、25件の件数とSHA-256を正本として固定した
- [next] Decision and Consensusのscore 1 / 2 / 3 / 4 / NEを作成する
- [next] Process and Time Managementのscore 1 / 2 / 3 / 4 / NEを作成し、35 / 35を完成する
- [later] 35件の横断内容レビューとBlind Pack最終化を行い、blind_calibration_pendingへ進める
- [later] 2名以上のblind独立評価、調停、校正レポートを実施してapprovedへ進める
- [later] System Quality Gateのgd-app接続、Evidence-first Judge、GD APP Episode Exporterへ進む

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Micro Anchor Thinking Collaboration v0.1 Decision]]
- informed_by [[Micro Anchor Foundation and Issue Framing v0.1 Decision]]
- informed_by [[Exercise C Four-State Matrix v0.1 Decision]]
