# Scenario Opportunity Matrix v0.1

## 1. 目的

標準演習A・B・Cが、内部7サブディメンションを評価するための機会をどの程度提供するかを明示する。

数値は期待点ではなく、利用者が対象行動を選べる独立した場面の設計数である。

## 2. マトリクス

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

## 3. 機会の定義

評価機会は次を全て満たす場面である。

1. 利用者が複数の行動を選択できる
2. AIが期待行動を先回りして完了していない
3. 対象行動に必要な情報が共有または質問可能である
4. 利用者の応答後に議論状態が変化し得る
5. 発言・イベントIDとして記録できる

AIが結論を確定した後に形式的に意見を聞く場面は、有効な評価機会に数えない。

## 4. シナリオ欠陥と利用者未行動

### 利用者未行動

- ScenarioとAI進行は有効
- 利用者へ明確な選択機会がある
- 利用者本人の発言・行動証拠がある
- 期待行動が不完全または逆効果

この場合はNEではなく、BARSに従い数値評価する。

### シナリオ欠陥

- AIが対象行動を先回りする
- required eventが発生しない
- hidden constraintが結論後まで提示されない
- ユーザー入力前にphaseを終了する
- ログ欠損で機会の有無が判定できない

この場合は利用者へ低得点を付けず、`INSUFFICIENT_OPPORTUNITY`、`AI_QUALITY_FAILURE`、または`SCENARIO_CONTRACT_FAILURE`としてNEにする。

## 5. 検査

`python scripts/check_candidate_scenario_pack.py`は次を確認する。

- 標準3演習がScenario Schemaへ適合する
- AI役割・private concern・rubric IDが重複しない
- phase順序が標準順である
- required/forbidden moveが矛盾しない
- 各ScenarioにAI側と利用者側のrubricがある
- 全7軸に合計2機会以上ある
- positive / negative / NE fixtureの意味条件が一致する
