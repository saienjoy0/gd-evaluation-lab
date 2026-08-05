# Exercise B High / Low Calibration v0.1

## 1. 目的

Exercise B「利害対立と統合」について、high / medium / lowの正常3状態を同じAI発言、同じSystem Quality、同じ15評価機会で校正する。

本成果物は合成Episodeによる研究・訓練用であり、採用合否の自動決定には使用しない。

## 2. 統制条件

3状態で次を同一に保つ。

- AI発言ID、本文、役割、phase、move、時刻、generation ID
- System Qualityのstatus、rule結果、8品質軸
- 15件のOpportunity ID、trigger時刻、候補者応答メッセージID
- Scenario、rubric、runner、resolverのversion

変更するのは候補者の発言内容、候補者行動を表す構造化イベント、人間評価入力、評価結果、Feedbackだけである。

## 3. 確定スコア

| State | IS | LO | LI | VA | CO | DE | PR |
|---|---:|---:|---:|---:|---:|---:|---:|
| high | 4 | 4 | 4 | 4 | 4 | 4 | 3 |
| medium | 3 | 3 | 3 | 3 | 3 | 3 | 2 |
| low | 1 | 1 | 2 | 1 | 1 | 1 | 1 |

全7軸で`high > medium > low`を満たす。

## 4. high行動

highでは、発言量ではなく次の行動品質を上げる。

- 初期の比較基準に既存資源との重複と見直し条件を含める
- 三者の懸念を言い換え、案修正後に残る反対条件を確認する
- 重点予算、既存資源、半年後の再配分を一つの段階的ポートフォリオへ統合する
- 各案の弱点、不確実性、撤退・縮小条件を明示する
- 少数意見を切り捨てず、最終合意前に再度反対できる場を作る
- 終盤の残時間を要約と未解決点確認へ具体的に配分する

4点を付ける6軸では、最低2件の証拠と複数phaseの証拠を必須とする。

`issue_framing`は直接機会が1件のため、`B-OP-IS-01`をprimary opportunityとし、後半の統合機会を明示的なauxiliary opportunityとして参照する。auxiliaryだけによる採点は許可しない。

## 5. low行動

lowでも全15機会を`offered + observed`にする。沈黙や機会欠落ではなく、観察可能な低品質行動として数値評価する。

- 比較基準を固定しない
- 懸念後に発言するが、内容を受け止めた修正を行わない
- 二施策を選ぶだけで複数立場の統合原則を示さない
- 観光側の少数意見に緩和策を置かない
- 判断基準や反対意見処理なしに配分を確定する
- 時間不足を理由に議論を終了する

予算総額3000万円と重点施策2件以下は維持する。契約違反ではなく、候補者行動の質として1〜2点を付けるためである。

## 6. deterministic rule profile

### high / medium

| Rule | Outcome |
|---|---|
| B-R01 | pass |
| B-R02 | pass |
| B-R03 | pass |
| B-R04 | pass |
| B-R05 | pass |
| B-R06 | pass |

### low

| Rule | Outcome |
|---|---|
| B-R01 | pass |
| B-R02 | fail |
| B-R03 | fail |
| B-R04 | fail |
| B-R05 | pass |
| B-R06 | pass |

B-PROH-01とB-PROH-02は3状態すべてpassし、System Qualityもpassする。candidate ruleのfailをSystem Quality failureへ混ぜない。

## 7. Opportunity profile

3状態すべて次を満たす。

```json
{
  "offered": 15,
  "not_offered": 0,
  "invalid": 0,
  "with_candidate_response": 15
}
```

lowのB-R02がfailしてもOpportunity responseは存在する。発言が存在することと、懸念へ有効に応答したことを分離する。

## 8. 共通校正checker

`scripts/calibration_controlled_states.py`へ次を共通化する。

- 全状態のSchema検証
- golden完全再生
- 同一runtimeの決定論的再実行
- manifest検証
- 厳密な得点順序
- AI発言、System Quality、Opportunity供給の一致
- 4点の複数phase証拠
- lowの全軸数値、NEなし
- lowの偽strength防止
- case、session、target IDの衝突防止

校正checkerは検査支援コードであり、`gd_eval`評価コアへstate分岐を持ち込まない。

## 9. 成果物

```text
fixtures/calibration/full-episodes/stakeholder-conflict/
├── high/
│   ├── case.json
│   ├── episode.json
│   ├── rater-sheet-a.json
│   ├── rater-sheet-b.json
│   ├── adjudication.json
│   └── 5種類のgolden
├── medium/
│   └── 既存の完全Episode
└── low/
    ├── case.json
    ├── episode.json
    ├── rater-sheet-a.json
    ├── rater-sheet-b.json
    ├── adjudication.json
    └── 5種類のgolden
```

検査入口：

```bash
python scripts/check_exercise_b_high_low.py
```

## 10. 完了条件

- 3状態の全goldenがrunner出力と完全一致する
- 全7軸で`high > medium > low`
- AI発言、System Quality、15機会が同一
- highの4点6軸が複数phase証拠を持つ
- lowが全7軸数値でNEを含まない
- lowのFeedbackに偽のstrengthがない
- evaluation coreへstateラベルや状態名分岐を追加しない
- 既存Exercise AとExercise B mediumの全CIを維持する

この完了後、Exercise B system_failureを追加し、影響軸だけを因果的NEとして分離する。
