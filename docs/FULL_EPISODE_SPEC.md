# 12完全Episode仕様 v0.1

## 1. 目的

マイクロアンカーでは測れない、複数軸の相互作用、評価機会、AI品質、時間経過を含む校正用完全Episodeを12本作る。

このPRでは完成Episodeそのものではなく、作成・検査・受入れ仕様を確定する。

## 2. 必須構成

標準演習3種について、次の4状態を1本ずつ作る。

| 状態 | 目的 |
|---|---|
| high | 複数軸で3〜4の行動が観察される |
| medium | 2〜3が混在し、境界判断が必要 |
| low | 機会は十分だが1〜2の行動が中心 |
| system_failure | AI・進行不良により一部軸がNEになる |

合計12本とする。

対象演習:

1. 曖昧な課題の構造化
2. 利害対立と統合
3. 時間制約下の意思決定

## 3. 必須データ

各Episodeセットは次を含む。

- Scenario
- Episode
- SystemQualityResult
- expected opportunity resolution
- 人間評価者AのRater Sheet
- 人間評価者BのRater Sheet
- Adjudication Record
- expected 3-domain narrative summary

## 4. Episode作成原則

- 7軸を一律に同じ点へしない
- highでも弱点を最低1つ残す
- lowでも観察された強みを最低1つ残す
- system_failureは利用者低得点へ変換しない
- 発言数だけでhigh/lowを作らない
- 4点には異なる時点の独立証拠を含める
- AIの役割とhidden constraintが会話へ反映される
- 最終結論の正しさだけで能力点を決めない

## 5. 期待評価の作成

期待値は一人の執筆者だけで決定しない。

1. 執筆者がScenarioとEpisodeを作る
2. 評価者2名が独立採点する
3. 調停者が不一致を解決する
4. ルーブリック問題があればEpisodeより先にアンカーを改訂する
5. 承認済み結果をexpected annotationとする

## 6. 難易度と評価機会

normal版3演習を先に完成させる。

各Episodeは、シナリオ集合全体で各7軸に最低2つの評価機会を提供するよう設計する。

評価機会の存在と、利用者が期待行動を実行したかを別々に記録する。

## 7. 受入れ条件

- 全データがSchema検査を通る
- 全証拠IDが対象Episodeに存在する
- 数値証拠が利用者本人の発言である
- System Quality GateとNEマッピングが矛盾しない
- 二重評価と調停履歴が残る
- high/medium/lowの差を発言量以外で説明できる
- 3領域フィードバックが7軸評価と整合する

## 8. 将来の保存先

```text
fixtures/calibration/full-episodes/<exercise>/<state>/
```
