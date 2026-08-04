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
- `docs/MICRO_ANCHOR_SPEC.md`
- `docs/FULL_EPISODE_SPEC.md`
- `docs/CANDIDATE_ASSESSMENT_SCENARIO_PACK.md`
- `docs/SCENARIO_OPPORTUNITY_MATRIX.md`
- `docs/EXERCISE_A_MEDIUM_VERTICAL_SLICE.md`

機械可読な正本:

- `rubrics/candidate-behavior/v0.1.json`
- `rubrics/ai-participant/v0.1.json`
- `contracts/move-vocabulary-v0.1.json`
- `contracts/deterministic-rule-vocabulary-v0.1.json`
- `schemas/common/ne-reason-codes-v0.1.json`
- `schemas/`

## 役割分担

- `docs/`: 人間向けの評価仕様と検証計画
- `annotation/`: 人間評価者の手順
- `rubrics/`: 版管理された行動アンカーとJudge質問
- `contracts/`: moveとdeterministic ruleの共通語彙
- `schemas/`: gd-appと評価ラボ間のJSON契約
- `fixtures/`: 匿名化・合成の検証データ、標準演習、評価機会ケース、完全Episode
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
python scripts/check_exercise_a_medium_vertical_slice.py
```

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
