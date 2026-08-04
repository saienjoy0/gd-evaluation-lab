# GD Evaluation Contract v0.1

## 1. 目的

この契約は、`gd-app`が出力する匿名化GDエピソードと、`gd-evaluation-lab`が返す評価結果の境界を定義する。

設計は次の分離を採用する。

- **Scenario:** GDテーマ、制約、AI参加者、ID付き評価機会、構造化ルール
- **Episode:** 実際に発生した発言・イベント・モデル版
- **Annotation:** 人間評価者が残す項目別採点と証拠
- **EvaluationResult:** AI品質ゲート、利用者7軸、証拠、版情報

## 2. 入力

- Scenario: `schemas/scenario-v0.1.schema.json`
- Episode: `schemas/episode-v0.1.schema.json`

## 3. 出力

- Evaluation Result: `schemas/evaluation-result-v0.1.schema.json`
- Human Annotation: `schemas/annotation-v0.1.schema.json`
- Human Rater Sheet: `schemas/rater-sheet-v0.1.schema.json`
- Adjudication: `schemas/adjudication-v0.1.schema.json`

## 4. 共通語彙

- move正本: `contracts/move-vocabulary-v0.1.json`
- deterministic rule正本: `contracts/deterministic-rule-vocabulary-v0.1.json`
- NE理由正本: `schemas/common/ne-reason-codes-v0.1.json`

Scenario、Episode、rubric、検査コードは、これらの正本にない文字列を独自追加しない。

## 5. ID規則

- `scenario_id`: シナリオの論理ID
- `session_id`: 1回のGD実行
- `message_id`: セッション内で一意な確定発言
- `event_id`: セッション内で一意なイベント
- `generation_id`: AI生成単位
- `participant_id`: 匿名化済み参加者ID
- `rubric_id`: シナリオ固有ルールID
- `opportunity_id`: シナリオ内の独立した評価機会
- `action_id`: actor・move・phaseを持つ必須行動
- `condition_id`: 評価機会を無効化し得る禁止条件

実名、メールアドレス、Clerk IDをIDとして使用しない。

## 6. 版管理

各評価結果に次を必須とする。

- `contract_version`
- `rubric_version`
- `ai_quality_rubric_version`
- `scenario_version`
- `orchestrator_version`
- `prompt_version`
- `judge_model`
- `judge_version`
- `deterministic_evaluator_version`
- `transcript_hash`

## 7. 標準phase

1. `problem_definition`
2. `idea_generation`
3. `option_comparison`
4. `decision`
5. `summary`

## 8. 標準move

- `clarify_goal`
- `define_scope`
- `define_criteria`
- `propose_idea`
- `ask_question`
- `respond_to_question`
- `support`
- `challenge`
- `integrate`
- `compare_options`
- `invite_participant`
- `time_check`
- `prioritize`
- `summarize`
- `propose_decision`
- `confirm_consensus`

## 9. Scenarioの機械可読条件

### 評価機会

評価機会は整数ではなく、ID付きオブジェクトとして定義する。

```json
{
  "opportunity_id": "A-OP-IS-01",
  "dimension": "issue_framing",
  "phase": "problem_definition",
  "trigger": "after_initial_positions",
  "expected_actor": "candidate",
  "required_context": ["priority_target_undefined"],
  "invalidated_by": ["A-PROH-01"]
}
```

Opportunity Matrixの数値は、この配列から検査コードが導出する。手入力の集計値を正本にしない。

### 必須行動

```json
{
  "action_id": "A-ACT-01",
  "actor": "candidate",
  "move": "define_criteria",
  "phase": "problem_definition",
  "minimum_occurrences": 1
}
```

### 禁止条件

禁止条件はmoveと混在させず、独立したrule IDとして保存する。

### instance rubric

`pass_condition`の自由記述は使用しない。各rubricは次を持つ。

- `rule_type`: `deterministic` / `judge` / `hybrid`
- `deterministic_rule_id`
- `judge_question_ids`
- `params`

## 10. 評価順序

```text
Scenario + Episode
  ↓
Schema validation
  ↓
Deterministic AI quality gate
  ↓
Scenario-specific structured rules
  ↓
AI participant quality Judge
  ↓
Evaluation opportunity ID check
  ↓
Candidate 7-dimension Judge
  ↓
Target-user evidence validation
  ↓
EvaluationResult
```

## 11. 証拠

利用者能力の数値評価に使える証拠は、次を全て満たす。

- Episode内に実在する
- `speaker_type`が`user`
- `participant_id`が`target_participant_id`と一致する
- 4点は異なるphaseの証拠を2件以上持つ
- question-level probabilitiesの合計は1である

## 12. 利用者表示用3領域

人間校正が完了するまで、3領域へ恣意的な平均点を出さない。

- 評価済みサブディメンション数を`coverage`として出す
- 最低の評価済み軸を`bottleneck_dimension`として出す
- `aggregation_status`は`not_calibrated`または`not_evaluable`
- `not_calibrated`では`score`を`null`にする
- 全軸NEなら`score`を`NE`にする

## 13. 共通NEコード

- `INSUFFICIENT_OPPORTUNITY`
- `AI_QUALITY_FAILURE`
- `TRANSCRIPT_INCOMPLETE`
- `EVENT_ORDER_INVALID`
- `SYSTEM_ERROR`
- `SCENARIO_CONDITION_UNFAIR`
- `SCENARIO_CONTRACT_FAILURE`
- `INSUFFICIENT_EVIDENCE`
- `JUDGE_FAILURE`
- `OTHER_REVIEW_REQUIRED`

全Schemaは同一のコード集合を受け付ける。

## 14. 本番利用制限

v0.1は練習・研究・shadow evaluation専用であり、採用合否の自動決定へ使用しない。
