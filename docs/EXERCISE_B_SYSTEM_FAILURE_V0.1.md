# Exercise B system_failure 分離ケース v0.1

## 1. 目的

Exercise B「利害対立と統合」に`system_failure`完全Episodeを追加し、候補者本人の低い行動と、AIが評価機会を損なった場合の`NE`を分離する。

本ケースは合成Episodeによる校正用検証であり、採用判断には使用しない。

## 2. 発生させる欠陥

mediumのm004は、三案の比較基準を候補者へ質問するAI発言である。system_failureでは同じ発言ID、phase、時刻、generation IDを保ったまま、候補者の最初の発言より前に配分を確定する`propose_decision`へ変更する。

```text
追加予算は子育て1700万円、地域交通1300万円とし、
観光は既存事業で対応する形で進めましょう。
```

この一発言差を既存の`finalize_before_conflict`が検出する。

## 3. rule profile

- `B-R01`〜`B-R06`: pass
- `B-PROH-01`: fail
- `B-PROH-02`: pass
- System Quality: fail
- `user_agency`: 2

正式なdecision phase前には三立場とchallengeが存在し、候補者案の後にもAI challengeがあるため、B-R01とB-R05はpassを維持する。複数のsystem failureを一ケースへ混ぜない。

## 4. 無効化する評価機会

`B-PROH-01`と因果的に接続された次の4機会だけを`invalid`とする。

- `B-OP-IS-01`
- `B-OP-DE-01`
- `B-OP-DE-02`
- `B-OP-DE-03`

残る11機会は`offered + observed`を維持する。

## 5. 評価結果

主要機会がすべて無効になった次の2軸だけを`NE / AI_QUALITY_FAILURE`とする。

- `issue_framing`
- `decision_and_consensus`

影響外の5軸はmediumと同じ数値を維持する。

- `logical_reasoning`: 3
- `listening_and_response`: 3
- `valuable_contribution`: 3
- `collaboration_and_relationship`: 3
- `process_and_time_management`: 2

System Quality全体がfailでも、失敗rule、invalid機会、有効機会不足の因果が揃わない軸へNEを伝播させない。

## 6. lowとの違い

lowはAI品質が正常で、15機会すべてが提供されている。そのため7軸すべてを1〜2点の数値で評価する。

system_failureは候補者が同じmedium行動をしていても、AI先回りによって主要機会が損なわれた2軸だけを評価不能とする。

## 7. 成果物

```text
fixtures/calibration/full-episodes/stakeholder-conflict/system_failure/
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

生成入口：

```bash
python scripts/generate_exercise_b_system_failure.py
```

検査入口：

```bash
python scripts/check_exercise_b_system_failure.py
```

## 8. 検査

checkerは次を確認する。

- golden完全一致と2回実行の決定性
- AI差分がm004の本文とmoveだけであること
- 候補者発言がmediumと完全一致すること
- 明示的な禁止条件イベントへ依存せず、実発言順から失敗を検出すること
- failed ruleが`B-PROH-01`だけであること
- invalid機会が4件だけであること
- NEが2軸だけであること
- 影響外5軸がmediumと同じであること
- lowが7軸数値であること
- 一部有効機会が残る場合はNEを拒否し、数値評価を許可すること
- 無効機会への数値採点、偽NE、無関係証拠、B-PROH-02混入を拒否すること
- FeedbackにNE理由が残ること

## 9. 完了条件

- 一つのAI発言差だけでsystem failureを再現できる
- `B-PROH-01`だけがfailする
- 4機会だけがinvalidになる
- 2軸だけがNEになる
- 影響外5軸がmediumと同じ数値を維持する
- generatorが保存済み正本を完全再現する
- runnerへstate分岐を追加しない
- Exercise AとExercise B正常3状態の既存CIを維持する
