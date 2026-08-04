# Scenario Opportunity Matrix v0.1

## 1. 目的

標準演習A・B・Cが、内部7サブディメンションを評価するための機会をどの程度提供するかを明示する。

各数値はScenario JSONの`evaluation_opportunities`配列から`check_candidate_scenario_pack.py`が導出する。表の手入力値だけを検査根拠にしない。

## 2. 導出結果

| Dimension | A 曖昧課題 | B 利害対立 | C 時間制約 | 合計 |
|---|---:|---:|---:|---:|
| `issue_framing` | 3 | 1 | 1 | 5 |
| `logical_reasoning` | 2 | 2 | 2 | 6 |
| `listening_and_response` | 2 | 3 | 2 | 7 |
| `valuable_contribution` | 2 | 2 | 2 | 6 |
| `collaboration_and_relationship` | 1 | 3 | 2 | 6 |
| `decision_and_consensus` | 1 | 3 | 3 | 7 |
| `process_and_time_management` | 1 | 1 | 3 | 5 |

全7軸についてScenario Pack全体で最低2機会を満たす。

## 3. 機会オブジェクト

各機会は次を持つ。

- 一意な`opportunity_id`
- 対象`dimension`
- 発生`phase`
- `trigger`
- `expected_actor`
- 必要な`required_context`
- 機会を無効化する`invalidated_by`

positive / negative / NE fixtureは、集計数ではなく具体的な`opportunity_id`を参照する。

## 4. シナリオ欠陥と利用者未行動

### 利用者未行動

- ScenarioとAI進行は有効
- 利用者へ明確な選択機会がある
- 利用者本人の発言・行動証拠がある
- 期待行動が不完全または逆効果

この場合はNEではなく、BARSに従い数値評価する。

### シナリオ欠陥

- AIが対象行動を先回りする
- required actionが発生しない
- private concernが不正な時点で開示される
- ユーザー入力前にphaseを終了する
- ログ欠損で機会の有無が判定できない

この場合は利用者へ低得点を付けず、共通NEコードを使用する。

## 5. 検査

`python scripts/check_candidate_scenario_pack.py`は次を確認する。

- 機会ID・action ID・禁止条件ID・rubric IDの一意性
- Opportunity Matrixを配列から再計算
- moveとdeterministic ruleが正本語彙に存在する
- required actionにactor・phase・最低回数がある
- rubricが構造化ruleを持つ
- candidate rubricが実在するJudge質問IDを参照する
- opportunity caseが実在する`opportunity_id`を参照する
- 負例が期待した理由で失敗する
