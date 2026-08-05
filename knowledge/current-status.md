---
title: Current Status
type: status
tags: [gd, evaluation, status]
permalink: gd-evaluation-current-status
updated: 2026-08-05
---

# Current Status

## Observations

- [phase] Exercise B high / low校正の準備
- [completed] 評価研究を`gd-app`から別リポジトリへ分離した
- [completed] 利用者7軸、表示3領域、1〜4＋NE、AI品質分離の方針を決めた
- [completed] Scenario、Episode、Annotation、Evaluation Result契約v0.1を作成した
- [completed] 証拠先行の人間評価ガイド、Rater Sheet、Adjudication、検証計画を実装した
- [completed] 標準演習A・B・C、評価機会マトリクス、positive/negative/NE fixtureを実装した
- [completed] 評価機会ID、構造化rule、共通NE、証拠所有者、3領域暫定出力、move語彙を堅牢化した
- [completed] 演習A mediumをScenarioからFeedbackまで通した
- [completed] 共通Full-Episode runnerへ一般化し、stateに依存しない決定論的再生成を実装した
- [completed] 演習A high / medium / lowを同じAI品質・同じ12機会で校正し、全7軸の順序を検証した
- [completed] 演習A system_failureでAI先回りを発生させ、影響2軸だけをNE、非影響5軸を数値評価として分離した
- [completed] 演習Aの4状態をSchema・JSON・Markdownの横断マトリクスとして確定し、state非依存と決定論的再生成を検証した
- [completed] 演習B固有の利害対立rule、System Quality禁止条件、15評価機会trigger/contextを共通runnerへ接続した
- [completed] 演習B mediumをScenarioからFeedbackまで通し、15機会すべてobserved、7軸を`3/3/3/3/3/3/2`で数値評価した
- [next] 演習B high / lowを同じAI品質・同じ15機会で校正する
- [next] 演習B system_failureと4状態マトリクスを作成する
- [next] 演習Cへ共通runnerを展開し、残りの完全Episodeを作成する
- [next] 35マイクロアンカーを仕様に従って作成する
- [later] System Quality Gateのgd-app接続、Evidence-first Judge、GD APP Episode Exporterへ進む

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise A Four-State Matrix v0.1 Decision]]
- informed_by [[Exercise B Medium Vertical Slice v0.1 Decision]]
