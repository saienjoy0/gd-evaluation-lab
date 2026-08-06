---
title: Current Status
type: status
tags: [gd, evaluation, status]
permalink: gd-evaluation-current-status
updated: 2026-08-06
---

# Current Status

## Observations

- [phase] Exercise C system_failure分離の準備
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
- [completed] 演習B high / medium / lowを同じAI品質・同じ15機会で校正し、全7軸の`high > medium > low`を固定した
- [completed] 正常3状態のgolden再生、AI品質、機会供給、score 4複数phase証拠、lowのNE逃げを共通checkerで検証した
- [completed] 演習B system_failureで候補者前のAI配分確定を発生させ、4機会をinvalid、影響2軸だけをNEへ分離した
- [completed] system_failureの影響外5軸をmediumと同じ数値に保ち、lowの7軸数値評価との違いを固定した
- [completed] 演習A・Bの4状態横断検査を共通matrix checkerへ統合した
- [completed] 演習Bの4状態をSchema・JSON・Markdownの横断マトリクスとして確定した
- [completed] 演習C固有の時間通知、遅延リスク、三案比較、優先順位更新、要約ruleを共通runnerへ接続した
- [completed] 演習C mediumをScenarioからFeedbackまで通し、15機会すべてobserved、7軸を`2/3/3/2/2/3/3`で数値評価した
- [completed] 40%・75%時間通知後の候補者ターン、リスク後の案修正、条件付き合意を構造化証拠で固定した
- [completed] 演習C high / medium / lowを同じAI発言・同じSystem Quality・同じ15機会で校正した
- [completed] 演習Cの点数順をhigh `3/4/4/4/4/4/4`、medium `2/3/3/2/2/3/3`、low `1/1/2/1/1/1/1`として全7軸で固定した
- [completed] lowは15機会を維持したままC-R03 / C-R04 / C-R05だけを失敗させ、7軸すべて数値・NEなし・strengthなしに固定した
- [completed] highの6つのscore 4について複数phase証拠を要求し、issue_framingは単一機会契約を守ってscore 3を上限にした
- [next] 演習C system_failureでAI起因の評価機会欠損と影響軸NEを分離する
- [next] 演習Cの4状態マトリクスを作成する
- [next] 35マイクロアンカーを仕様に従って作成する
- [later] System Quality Gateのgd-app接続、Evidence-first Judge、GD APP Episode Exporterへ進む

## Relations

- part_of [[GD Evaluation Lab Project Overview]]
- follows [[Exercise C High Low Calibration v0.1 Decision]]
- informed_by [[Exercise C Medium Vertical Slice v0.1 Decision]]
- informed_by [[Exercise B Four-State Matrix v0.1 Decision]]
