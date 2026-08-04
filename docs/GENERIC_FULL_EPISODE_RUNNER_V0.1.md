# Generic Full-Episode Runner v0.1

## 1. ゴール

GD Evaluation Labのゴールは、発言量や総合印象で利用者を採点することではない。次を分離し、再現・監査・校正できる評価基盤を作ることである。

1. Scenarioが提供した評価機会
2. AI／進行システムの品質
3. 利用者本人の観察可能な行動
4. 二重人間評価と調停
5. 最終評価と改善フィードバック

現段階は研究・練習・shadow evaluation用であり、自動採用判断には使用しない。将来のLLM Judgeは、人間校正データと一致率・再採点安定性・公平性を検証してから接続する。

## 2. PR #7の目的

Exercise A medium専用の縦切りを、演習・ケース状態に依存しない共通runnerへ移す。PR #7では新しいhigh／low／system_failure Episodeを追加せず、既存mediumの5つの生成成果物を完全再現する。

```text
Scenario + Episode
        ↓
DeterministicRuleResult
        ↓
SystemQualityResult
        ↓
OpportunityResolution
Rater A + Rater B + Adjudication
        ↓
EvaluationResult
        ↓
Feedback
全入力・生成物・oracle
        ↓
Dependency-aware Manifest
```

## 3. 元設計から修正した点

### 3.1 `state`はメタデータだけ

`high / medium / low / system_failure`はケース分類と横断検査のための値であり、点数・NE・文言の生成入力にしない。生成用`RuntimeCase`には`state`フィールド自体を渡さない。CIは生成モジュール内の`state`参照をASTで拒否し、stateだけを変更しても意味成果物が変わらないことを確認する。

### 3.2 Case ProfileはRubric参照を持つ

共通Evaluation Result Builderが7軸、表示領域、版情報を決定できるよう、Case ProfileへCandidate RubricとAI Quality Rubricの参照を追加する。これらは`source`であり、期待出力ではない。

### 3.3 Opportunityイベントを自己申告として信用しない

`OPPORTUNITY_OFFERED`が存在するだけでは`offered`にしない。共通Resolverは次を確認する。

- ScenarioにOpportunity IDがある
- trigger handlerが実際のメッセージ／イベント順で成立する
- required contextが成立する
- Opportunityのphaseと応答messageのphaseが一致する
- target participant本人の応答である
- 応答がtrigger後に存在する
- System Quality違反による無効化条件がない

未実装triggerまたはcontextは無視せず実行失敗にする。

### 3.4 v0.1の`invalid`表記を維持

既存`opportunity-resolution-v0.1`は状態名として`invalid`を使用している。`invalidated`へ変更するとmedium goldenの契約を破るため、PR #7では`invalid`を「無効化済み」の意味で維持する。

元設計の`uncertain`もv0.1 Schemaには存在しない。曖昧なtriggerを推測して`uncertain`にするのではなく、未検証条件としてfail closedにする。名称変更や`uncertain`追加は契約v0.2で行う。

### 3.5 旧Manifestをoracleとして残す

既存`manifest.json`を直接置換すると「mediumの既存成果物を再現する」と「依存関係付きManifestへ変更する」が衝突する。そこで、旧Manifestは`test_oracle`として保持し、runnerは新しい`full-episode-manifest-v0.1`を最後に生成する。

新Manifestは各artifactへ次を保存する。

- `path`
- `sha256`
- `role`: `source / human_authored / generated / test_oracle`
- `depends_on`

生成artifactから`test_oracle`への依存、循環依存、EvaluationResultからFeedbackへの逆依存を拒否する。Manifest自身は自己hashしない。

### 3.6 expected出力を生成へ渡さない

Case Profileは検査用oracle pathを持つが、generation用`RuntimeCase`からoracleを除外する。runnerはScenario、Episode、Rubric、Rater Sheets、Adjudicationだけで成果物を生成した後、checkerが別経路でoracleと比較する。

FeedbackはEvaluationResultからのみ生成する。EvaluationResultはFeedbackを読まない。

### 3.7 人間作成データは自動生成しない

Rater SheetsとAdjudicationは校正データであり、runnerは作成・修正しない。runnerは評価者重複、調停者の重複、点数対応、証拠所有者、Score 4のphase多様性、NE伝播だけを検査する。

## 4. 実装構成

```text
gd_eval/
├── vertical_slice/
│   ├── loader.py
│   ├── manifest.py
│   ├── models.py
│   └── runner.py
├── rules/
│   ├── common.py
│   ├── exercise_a.py
│   └── registry.py
├── quality/system_quality.py
├── opportunities/resolver.py
├── results/evaluation_result.py
└── feedback/builder.py
scripts/
├── run_full_episode.py
└── check_full_episode_runner.py
```

旧`evaluate_exercise_a_medium.py`と`check_exercise_a_medium_vertical_slice.py`は共通runnerを呼ぶ互換入口だけにする。

## 5. 依存方向

- DeterministicRuleResult: Scenario + Episode
- SystemQualityResult: Scenario + Episode + DeterministicRuleResultのAI/system対象のみ
- OpportunityResolution: Scenario + Episode + SystemQualityResult
- EvaluationResult: Episode + Rubrics + OpportunityResolution + SystemQualityResult + Rater Sheets + Adjudication
- Feedback: EvaluationResult
- Manifest: 全artifact生成後

Candidate ruleをSystemQualityへ混入させない。OpportunityResolverは人間点数を読まない。FeedbackとoracleはEvaluationResultの入力にならない。

## 6. PR #7の完了条件

- medium専用の中核ロジックが互換入口から除去されている
- 未実装rule・trigger・contextをfail closedで拒否する
- mediumのDeterministicRuleResult、SystemQualityResult、OpportunityResolution、EvaluationResult、Feedbackが既存oracleと完全一致する
- 同一入力2回で全意味成果物と新Manifestが一致する
- target participant以外の証拠を拒否する
- AI/system違反の影響軸を数値採点できない
- 人間評価者の重複、調停点不一致、Score 4の単一phase証拠を拒否する
- Manifestのtest-oracle依存、循環、Feedback逆依存を拒否する
- state分岐を生成コードで拒否する
- 既存CIと共通runner CIが成功する

## 7. 次の順序

1. PR #8: Exercise A high / low
2. PR #9: Exercise A system_failure
3. PR #10: Exercise A 4状態マトリクス
4. Exercise B / Cへ同じ契約を展開
5. 35 micro-anchorと12 full-Episode校正集合を完成
6. 人間一致率を測定後、証拠付きLLM Judgeをshadow modeで接続

PR #7の成功は「ケース数が増えたこと」ではなく、今後のケースが同じ評価契約・同じ依存方向・同じfail-closed検査で追加できることにある。
