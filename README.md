# gd-evaluation-lab

GD appの評価基準、検証方法、企業導入可能性を継続的に研究するためのリポジトリです。

## 現在の評価仕様

Evaluation Contract v0.1では、次を正本として管理します。

- 利用者行動の内部7軸
- 利用者表示用の3領域
- 1〜4点と`NE`
- 発言ID付きの評価根拠
- AI参加者の品質ゲート
- シナリオ固有ルーブリック
- ルーブリック・モデル・プロンプト・評価器の版
- 旧評価と新評価のshadow mode比較

仕様入口:

- `docs/EVALUATION_PURPOSE.md`
- `docs/COMPETENCY_MODEL.md`
- `docs/RUBRIC_DESIGN.md`
- `docs/EVALUATION_CONTRACT_V0.1.md`

機械可読な正本:

- `rubrics/candidate-behavior/v0.1.json`
- `rubrics/ai-participant/v0.1.json`
- `schemas/`

## 役割分担

- `docs/`: 人間向けの評価仕様
- `rubrics/`: 版管理された行動アンカーとJudge質問
- `schemas/`: gd-appと評価ラボ間のJSON契約
- `fixtures/`: 匿名化・合成の検証データ
- `knowledge/`: 長期的に残す決定と現在地
- Beads (`bd`): 未完了タスクと依存関係
- `TASKS_FALLBACK.md`: Beads初期化前だけ使う一時タスクリスト

## 検査

```bash
python scripts/check_knowledge.py
python scripts/check_evaluation_contract.py
```

## 毎日の使い方

ChatGPTへ次のように指示します。

> 今日のGD評価研究の内容をリポジトリへ反映して。決定、発見、未解決、次のタスクに分けて。

## 利用制限

v0.1は練習・研究・shadow evaluation用です。採用合否の自動決定には使用しません。

実名、メールアドレス、Clerk ID、生音声、未匿名化の会話全文、企業機密はコミットしません。
