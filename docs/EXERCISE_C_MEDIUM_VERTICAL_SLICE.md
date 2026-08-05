# Exercise C Medium Vertical Slice v0.1

## 1. 目的

Exercise C「時間制約下の意思決定」を、共通Full-Episode runnerでScenarioからFeedbackまで決定論的に再生成する。

本成果物は研究・校正用の合成Episodeであり、採用合否の自動決定には使用しない。

## 2. 演習内容

新卒研修を、対面・オンライン・ハイブリッドの三案から720秒で決定する。

- 参加者120名
- 地域採用者45名
- 予算600万円
- 準備期限30日
- 完了率90%以上
- 配属前の基礎演習が必要
- 地域採用者が参加可能であること

## 3. medium Episode

候補者は、二日間の対面必須実技とオンライン事前・事後学習を組み合わせた条件付きハイブリッドを提案する。

オンライン部分は会社管理端末または指定会場端末に限定する。入社前日まで移動できない地域採用者には、遠隔導入と後日実技を例外対応として設ける。

7日以内に次を確認する。

- 必要端末数
- 例外対象者数
- 会場割当
- 確認責任者

## 4. 時間設計

| 要素 | 時刻 |
|---|---:|
| 40%時間通知 | 290,000ms |
| 40%後の候補者優先順位更新 | 309,000ms |
| 三案比較 | 356,000ms |
| 遅延リスク開示 | 478,000ms |
| リスク後の案修正 | 500,000ms |
| 75%時間通知 | 544,000ms |
| 75%後の候補者優先順位更新 | 562,000ms |
| decision開始 | 566,000ms |
| 最終要約 | 680,000ms |

時間通知の存在だけでなく、通知後90秒以内に候補者ターンが残され、候補者が未解決論点の優先順位を更新したことを検査する。

## 5. 決定論的rule

### C-R01

40%・75%付近に時間通知があり、その後に候補者ターンが確保される。

### C-R02

決定前に、正本AI participantへ紐付いた遅延リスクが最低1件開示される。

### C-R03

候補者が時間通知後に、二項目以上の検討順序または残作業を明示する。

### C-R04

候補者が三案を二基準以上で比較し、遅延リスク後に案または実施条件を修正する。

### C-R05

最終要約に次の三項目を含める。

- `mode`
- `exception`
- `next_check`

## 6. System Quality禁止条件

### C-PROH-01 `finalize_before_risk_reveal`

AIが遅延リスク開示前に結論を確定した場合、System Qualityをfailとする。

### C-PROH-02 `skip_summary`

候補者要約がない、または要約前にセッションを閉じた場合にfailとする。

mediumでは両条件ともpassする。

## 7. 評価機会

Exercise Cには15件の評価機会がある。

| Dimension | 機会数 |
|---|---:|
| `issue_framing` | 1 |
| `logical_reasoning` | 2 |
| `listening_and_response` | 2 |
| `valuable_contribution` | 2 |
| `collaboration_and_relationship` | 2 |
| `decision_and_consensus` | 3 |
| `process_and_time_management` | 3 |

mediumでは次を正本とする。

```json
{
  "offered": 15,
  "not_offered": 0,
  "invalid": 0,
  "with_candidate_response": 15
}
```

## 8. medium校正スコア

| Dimension | Score |
|---|---:|
| `issue_framing` | 2 |
| `logical_reasoning` | 3 |
| `listening_and_response` | 3 |
| `valuable_contribution` | 2 |
| `collaboration_and_relationship` | 2 |
| `decision_and_consensus` | 3 |
| `process_and_time_management` | 3 |

score profileは`2/3/3/2/2/3/3`である。

## 9. Episode正本

Episodeは次の圧縮正本から決定論的に復元する。

```text
fixtures/calibration/full-episodes/time-boxed-decision/medium/episode.json.gz.b64
```

復元入口:

```bash
python scripts/materialize_exercise_c_medium_episode.py
```

復元後の`transcript_hash`は次で固定する。

```text
84ddd149a37e39fff933357d1a60e75ca1dde9afaa73724a8ebdf55c1b9ca1f6
```

## 10. 検査

```bash
python scripts/materialize_exercise_c_medium_episode.py
python scripts/generate_exercise_c_medium.py
python scripts/check_exercise_c_medium.py
```

checkerは正常系に加え、時間通知欠落、時刻逸脱、リスクの決定後開示、誤ったconcern、優先順位更新欠落、三案比較不足、revision欠落、要約field欠落、AI先回り決定、summary欠落、証拠所有者不整合をfail-closedで検査する。

## 11. 完了条件

- C-R01〜C-R05がpassする
- C-PROH-01・C-PROH-02がpassする
- System Qualityがpassする
- 15機会すべてがofferedかつobservedになる
- 全7軸が数値評価でNEがない
- score profileが`2/3/3/2/2/3/3`になる
- 40%・75%時間通知後に候補者の優先順位更新がある
- 遅延リスク後に案が修正される
- 要約に`mode / exception / next_check`が含まれる
- 5種goldenが共通runnerから決定論的に再生成される
- Exercise A・Bの既存検査を壊さない

次は、AI発言・System Quality・15機会を統制したまま、Exercise C high / lowを校正する。
