# gd-evaluation-lab

GD appの評価基準、検証方法、企業導入可能性を継続的に研究するためのリポジトリです。

## 現在の評価仕様

Evaluation Contract v0.1では、次を正本として管理します。

- 利用者行動の内部7軸
- 利用者表示用の3領域
- 1〜4点と`NE`
- 発言ID付きの評価根拠
- AI参加者の品質ゲート
- ID付き評価機会
- 構造化されたシナリオ固有ルール
- ルーブリック・モデル・プロンプト・評価器の版
- 旧評価と新評価のshadow mode比較

仕様入口:

- `docs/EVALUATION_PURPOSE.md`
- `docs/COMPETENCY_MODEL.md`
- `docs/RUBRIC_DESIGN.md`
- `docs/EVALUATION_CONTRACT_V0.1.md`

検証・人間評価入口:

- `docs/VALIDATION_PLAN.md`
- `annotation/HUMAN_ANNOTATION_GUIDE.md`
- `annotation/MICRO_ANCHOR_RATING_GUIDE.md`
- `docs/MICRO_ANCHOR_SPEC.md`
- `docs/MICRO_ANCHOR_FOUNDATION_ISSUE_FRAMING_V0.1.md`
- `docs/FULL_EPISODE_SPEC.md`
- `docs/CANDIDATE_ASSESSMENT_SCENARIO_PACK.md`
- `docs/SCENARIO_OPPORTUNITY_MATRIX.md`
- `docs/EXERCISE_A_MEDIUM_VERTICAL_SLICE.md`
- `docs/GENERIC_FULL_EPISODE_RUNNER_V0.1.md`
- `docs/EXERCISE_A_HIGH_LOW_V0.1.md`
- `docs/EXERCISE_A_SYSTEM_FAILURE_V0.1.md`
- `docs/EXERCISE_A_FOUR_STATE_MATRIX_V0.1.md`
- `docs/EXERCISE_B_MEDIUM_VERTICAL_SLICE.md`
- `docs/EXERCISE_B_HIGH_LOW_CALIBRATION.md`
- `docs/EXERCISE_B_SYSTEM_FAILURE_V0.1.md`
- `docs/EXERCISE_B_FOUR_STATE_MATRIX_V0.1.md`
- `docs/EXERCISE_C_MEDIUM_VERTICAL_SLICE.md`
- `docs/EXERCISE_C_HIGH_LOW_CALIBRATION_V0.1.md`
- `docs/EXERCISE_C_SYSTEM_FAILURE_V0.1.md`
- `docs/EXERCISE_C_FOUR_STATE_MATRIX_V0.1.md`

機械可読な正本:

- `rubrics/candidate-behavior/v0.1.json`
- `rubrics/ai-participant/v0.1.json`
- `contracts/move-vocabulary-v0.1.json`
- `contracts/deterministic-rule-vocabulary-v0.1.json`
- `schemas/common/ne-reason-codes-v0.1.json`
- `schemas/exercise-four-state-matrix-v0.1.schema.json`
- `schemas/micro-anchor-v0.1.schema.json`
- `schemas/micro-anchor-set-v0.1.schema.json`
- `schemas/micro-anchor-rating-v0.1.schema.json`
- `fixtures/calibration/matrices/exercise-a-four-state-v0.1.json`
- `fixtures/calibration/matrices/exercise-b-four-state-v0.1.json`
- `fixtures/calibration/matrices/exercise-c-four-state-v0.1.json`
- `fixtures/calibration/full-episodes/time-boxed-decision/medium/episode.json`
- `fixtures/anchors/anchor-set-v0.1.json`
- `fixtures/anchors/issue_framing/`
- `fixtures/anchors/blind/issue-framing-v0.1.json`
- `schemas/`

## 役割分担

- `docs/`: 人間向けの評価仕様と検証計画
- `annotation/`: 人間評価者の手順
- `rubrics/`: 版管理された行動アンカーとJudge質問
- `contracts/`: moveとdeterministic ruleの共通語彙
- `schemas/`: gd-appと評価ラボ間のJSON契約
- `fixtures/`: 匿名化・合成の検証データ、標準演習、評価機会ケース、完全Episode、マイクロアンカー
- `knowledge/`: 長期的に残す決定と現在地
- Beads (`bd`): 未完了タスクと依存関係
- `TASKS_FALLBACK.md`: Beads初期化前だけ使う一時タスクリスト

## 検査

```bash
python scripts/check_knowledge.py
python scripts/check_evaluation_contract.py
python scripts/check_annotation_foundation.py
python scripts/check_candidate_scenario_pack.py
python scripts/check_contract_hardening.py
python scripts/check_full_episode_runner.py
python scripts/check_exercise_a_high_low.py
python scripts/check_exercise_a_system_failure.py
python scripts/check_numeric_evidence_provenance.py
python scripts/check_exercise_a_four_state_matrix.py
python scripts/check_exercise_b_medium.py
python scripts/check_exercise_b_high_low.py
python scripts/check_exercise_b_system_failure.py
python scripts/check_exercise_b_four_state_matrix.py
python scripts/generate_exercise_c_medium.py
python scripts/check_exercise_c_medium.py
python scripts/check_exercise_c_high_low.py
python scripts/check_exercise_c_system_failure.py
python scripts/check_exercise_c_four_state_matrix.py
python scripts/check_micro_anchor_contract.py
python scripts/check_micro_anchor_set.py
python scripts/export_micro_anchor_blind_pack.py --check
python scripts/check_micro_anchor_negative_fixtures.py
```

## マイクロアンカー現在地

35件中5件を実装済みです。

- Issue Framing: score 1 / 2 / 3 / 4 / NE
- Anchor set status: `partial`
- 各アンカーのapproval status: `draft`
- 人間二重評価: 未実施

次はLogical ReasoningとValuable Contributionの10件を追加します。

## 評価者の基本手順

1. AIスコアを非表示にする
2. 評価機会IDを確認する
3. 点数より先に利用者本人の証拠発言を選ぶ
4. BARSアンカーへ照合する
5. 1〜4またはNEを記録する
6. 二重評価後に不一致理由を調停する

## 利用制限

v0.1は練習・研究・shadow evaluation用です。採用合否の自動決定には使用しません。

実名、メールアドレス、Clerk ID、生音声、未匿名化の会話全文、企業機密はコミットしません。
