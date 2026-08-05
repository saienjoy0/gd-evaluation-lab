# Exercise B Medium Vertical Slice v0.1

## 1. 目的

Exercise B「利害対立と統合」を、共通Full-Episode runnerでScenarioからFeedbackまで決定論的に再生成できる状態にする。

本成果物は合成Episodeによる校正用検証であり、採用合否の自動決定には使用しない。

## 2. 演習内容

市の追加予算3000万円を次の三施策へ配分する。

- 子育て支援
- 地域交通
- 観光振興

決定条件は次のとおりである。

- 重点施策は二つ以下
- 判断基準を明示する
- 採用しない施策への緩和策を含める
- 配分総額を3000万円に保つ

## 3. medium Episode

mediumでは、候補者が次の配分を提案する。

| 施策 | 配分 |
|---|---:|
| 子育て支援 | 1700万円 |
| 地域交通 | 1300万円 |
| 観光振興 | 重点追加予算なし |

観光振興は、既存広報枠と地域事業者ネットワークを使った小規模な通年企画として残し、半年後に再配分を検討する。

## 4. 評価機会

Exercise Bには15件の評価機会がある。

| Dimension | 機会数 |
|---|---:|
| `issue_framing` | 1 |
| `logical_reasoning` | 2 |
| `listening_and_response` | 3 |
| `valuable_contribution` | 2 |
| `collaboration_and_relationship` | 3 |
| `decision_and_consensus` | 3 |
| `process_and_time_management` | 1 |

medium Episodeでは全15件を`offered + observed`にする。

```json
{
  "offered": 15,
  "not_offered": 0,
  "invalid": 0,
  "with_candidate_response": 15
}
```

各数値評価は、対象dimensionのOpportunity Eventと、そのイベントへ登録された候補者本人の応答メッセージへ追跡可能でなければならない。

## 5. 構造化証拠

自然言語の単語一致だけで利害統合や配分制約を判定しない。Episodeには次の構造化イベントを記録する。

- `PRIVATE_CONCERN_REVEALED`
- `CONFLICT_SUMMARY_RECORDED`
- `POSITIONS_INTEGRATED`
- `MINORITY_VIEW_PRESENT`
- `BUDGET_SPLIT_PROPOSED`
- `BUDGET_SPLIT_RECORDED`
- `MITIGATION_REQUIRED`
- `DECISION_ALLOCATION_RECORDED`
- `MINORITY_CONCERN_STATUS`

懸念開示イベントには、対応した候補者応答IDも記録する。

## 6. 決定論的ルール

### B-R01

三つの異なるAI立場と、少なくとも一件のchallengeがdecision phase前に存在する。

### B-R02

候補者が開示された懸念へ直接応答または案修正を行う。

### B-R03

`POSITIONS_INTEGRATED`イベントで二つ以上の立場が統合される。

### B-R04

最終決定に次の三項目が含まれる。

- `criteria`
- `allocation`
- `mitigation`

### B-R05

候補者の最初の案へAIが即時同意せず、decision phase前にchallengeを提示する。

### B-R06

`DECISION_ALLOCATION_RECORDED`イベントについて次を検査する。

- `allocation_total_yen == 30000000`
- `priority_count <= 2`

数値制約ハンドラは、既存の単一field形式と複数checks形式の両方を扱う。

## 7. System Quality禁止条件

### B-PROH-01: finalize_before_conflict

利用者の実質入力または現実的な対立より前に、AIが配分を確定した場合にfailとする。

影響候補軸は次のとおりである。

- `issue_framing`
- `listening_and_response`
- `collaboration_and_relationship`
- `decision_and_consensus`

### B-PROH-02: silence_minority_concern

`MINORITY_CONCERN_STATUS / silenced`が記録された場合にfailとする。

影響候補軸は次のとおりである。

- `listening_and_response`
- `collaboration_and_relationship`
- `decision_and_consensus`

mediumでは両禁止条件ともpassし、System Qualityをpassとする。

## 8. medium校正スコア

| Dimension | Score |
|---|---:|
| `issue_framing` | 3 |
| `logical_reasoning` | 3 |
| `listening_and_response` | 3 |
| `valuable_contribution` | 3 |
| `collaboration_and_relationship` | 3 |
| `decision_and_consensus` | 3 |
| `process_and_time_management` | 2 |

processだけ2とする。終了前の時間確認と未解決点整理は行うが、中盤での進捗・時間配分調整は限定的だからである。

## 9. fail-closed検査

専用checkerは、正常系に加えて次の負例を確認する。

1. 三立場が揃わない
2. 候補者案の後にchallengeがない
3. private concernへの応答がない
4. 利害統合イベントがない
5. mitigation fieldがない
6. 配分総額が3000万円でない
7. 重点施策が三件になる
8. concern IDが誤っている
9. Opportunity Eventより前に候補者応答が始まっている

未実装のrule、trigger、contextは既存registryと同様に例外として拒否する。

## 10. 成果物

```text
fixtures/calibration/full-episodes/stakeholder-conflict/medium/
├── case.json
├── episode.json
├── rater-sheet-a.json
├── rater-sheet-b.json
├── adjudication.json
├── deterministic-rule-result.json
├── system-quality-result.json
├── opportunity-resolution.json
├── evaluation-result.json
└── expected-feedback.json
```

検査入口：

```bash
python scripts/check_exercise_b_medium.py
```

## 11. 完了条件

- B-R01〜B-R06がpassする
- B-PROH-01とB-PROH-02がpassする
- System Qualityがpassする
- 15機会すべてがofferedかつobservedになる
- 7軸すべてが数値でNEがない
- score profileが`3/3/3/3/3/3/2`になる
- 配分総額、重点施策数、観光緩和策を機械検査できる
- 全成果物がrunner出力から決定論的に再生成される
- 9件の負例が期待した理由で失敗する

この完了後、同じAI発言と15機会を統制してExercise B high / lowを作成する。
