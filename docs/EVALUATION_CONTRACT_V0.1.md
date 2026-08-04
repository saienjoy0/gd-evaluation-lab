# GD Evaluation Contract v0.1

## 1. 目的

この契約は、`gd-app`が出力する匿名化GDエピソードと、`gd-evaluation-lab`が返す評価結果の境界を定義する。

設計は次の分離を採用する。

- **Scenario:** GDテーマ、制約、AI参加者、評価機会、シナリオ固有ルール
- **Episode:** 実際に発生した発言・イベント・モデル版
- **Annotation:** 人間評価者が残す項目別採点と証拠
- **EvaluationResult:** AI品質ゲート、利用者7軸、証拠、版情報

## 2. 入力

- Scenario: `schemas/scenario-v0.1.schema.json`
- Episode: `schemas/episode-v0.1.schema.json`

## 3. 出力

- Evaluation Result: `schemas/evaluation-result-v0.1.schema.json`
- Human Annotation: `schemas/annotation-v0.1.schema.json`

## 4. ID規則

- `scenario_id`: シナリオの論理ID
- `session_id`: 1回のGD実行
- `message_id`: セッション内で一意な確定発言
- `event_id`: セッション内で一意なイベント
- `generation_id`: AI生成単位
- `participant_id`: 匿名化済み参加者ID
- `rubric_id`: シナリオ固有ルールID

実名、メールアドレス、Clerk IDをIDとして使用しない。

## 5. 版管理

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

## 6. 標準phase

1. `problem_definition`
2. `idea_generation`
3. `option_comparison`
4. `decision`
5. `summary`

## 7. 標準move例

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
- `summarize`
- `propose_decision`
- `confirm_consensus`

## 8. 評価順序

```text
Scenario + Episode
  ↓
Schema validation
  ↓
Deterministic AI quality gate
  ↓
Scenario-specific instance rubrics
  ↓
AI participant quality Judge
  ↓
Evaluation opportunity check
  ↓
Candidate 7-dimension Judge
  ↓
Evidence validation
  ↓
EvaluationResult
```

## 9. NEコード

- `INSUFFICIENT_OPPORTUNITY`
- `AI_QUALITY_FAILURE`
- `TRANSCRIPT_INCOMPLETE`
- `EVENT_ORDER_INVALID`
- `SYSTEM_ERROR`
- `SCENARIO_CONDITION_UNFAIR`
- `INSUFFICIENT_EVIDENCE`
- `JUDGE_FAILURE`

## 10. 本番利用制限

v0.1は練習・研究・shadow evaluation専用であり、採用合否の自動決定へ使用しない。
