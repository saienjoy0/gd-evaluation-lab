# Exercise B Four-State Matrix v0.1

## 1. 目的

Exercise B「利害対立と統合」の`high`、`medium`、`low`、`system_failure`を一つの横断マトリクスとして確定し、候補者行動差による数値評価と、AI品質不良による評価不能を同じ検査基盤で説明可能にする。

本成果物は合成Episodeによる校正用検証であり、採用合否の自動決定には使用しない。

## 2. 4状態

| state | System Quality | offered | invalid | 数値軸 | NE軸 |
|---|---|---:|---:|---:|---:|
| `high` | pass | 15 | 0 | 7 | 0 |
| `medium` | pass | 15 | 0 | 7 | 0 |
| `low` | pass | 15 | 0 | 7 | 0 |
| `system_failure` | fail | 11 | 4 | 5 | 2 |

## 3. 正常3状態の統制

`high`、`medium`、`low`では次を同一に固定する。

- Scenarioとscenario version
- AI発言ID、本文、phase、move、時刻、generation ID
- System Qualityのrule結果とdimension score
- 15件の評価機会と候補者応答の供給
- runner、rubric、評価器のversion

異なるのは候補者本人の発言、候補者行動を表す構造化イベント、人間評価結果、Feedbackだけである。

全7軸で次を満たす。

```text
high > medium > low
```

`low`は全15機会が観察可能なため、低い行動を`NE`へ置き換えない。

## 4. system_failureの分離

`system_failure`では、mediumのAI発言`m004`だけを変更する。

```text
medium:
比較基準を候補者へ質問する ask_question

system_failure:
候補者の初回発言前に配分を確定する propose_decision
```

候補者発言と、m004以外のAI発言はmediumと同一に保つ。

この欠陥により`B-PROH-01`だけがfailし、次の4機会をinvalidとする。

- `B-OP-IS-01`
- `B-OP-DE-01`
- `B-OP-DE-02`
- `B-OP-DE-03`

影響を受ける次の2軸だけを`NE / AI_QUALITY_FAILURE`とする。

- `issue_framing`
- `decision_and_consensus`

非影響5軸はmediumと同じ数値を維持する。

## 5. state非依存

共通runnerはstateラベルを採点入力として受け取らない。

checkerは`gd_eval`配下のPython ASTを走査し、`high`、`medium`、`low`、`system_failure`という状態文字列が評価中核へハードコードされていないことを確認する。

状態別の期待値は校正checkerの設定として保持し、評価中核へ分岐を追加しない。

## 6. 共通matrix checker

Exercise Aで個別実装していた横断検査を、次の共通モジュールへ移す。

```text
scripts/calibration_four_state_matrix.py
```

共通モジュールは次を担当する。

- 4状態のSchema検証
- 全goldenの完全再生
- 同一runtimeの決定論的再実行
- 正常3状態のAI発言、System Quality、Opportunity供給の一致
- 全7軸の厳密な得点順序
- lowの全軸数値評価
- system_failureの因果的NE範囲
- 非影響軸のmedium同値
- runnerのstate非依存
- 評価中核のstate literal検査
- JSON／Markdown正本との完全一致

Exercise AとBの専用checkerは、演習固有の期待値だけを設定する薄い入口とする。

## 7. 機械可読成果物

- Schema: `schemas/exercise-four-state-matrix-v0.1.schema.json`
- JSON正本: `fixtures/calibration/matrices/exercise-b-four-state-v0.1.json`
- Markdown正本: `fixtures/calibration/matrices/exercise-b-four-state-v0.1.md`
- 共通checker: `scripts/calibration_four_state_matrix.py`
- B検査入口: `scripts/check_exercise_b_four_state_matrix.py`

保存済みJSON・Markdownは生成入力に使用せず、4ケースのrunner実行後に生成したマトリクスとのoracle比較だけに使用する。

## 8. CI検査

次を一回の検査で確認する。

- 4つの完全Episodeのgolden完全一致
- 各caseとマトリクスの決定性
- 正常3状態のAI発言、System Quality、15機会の完全一致
- 全7軸の`high > medium > low`
- lowの7軸数値・NEなし
- system_failureの失敗System Quality ruleが`B-PROH-01`だけ
- system_failureの4機会invalid・2軸NE
- 非影響5軸がmediumと同値
- mediumとsystem_failureの候補者発言が完全一致
- AI差分がm004の本文とmoveだけ
- runnerがstate labelを受け取らない
- 評価中核にstate文字列のハードコードがない
- 共通Schemaへの適合
- JSON／Markdown正本との完全一致
- 既存Exercise A matrix checkerの回帰がない

## 9. 完了条件

- Exercise Bの4状態を一つの表で説明できる
- lowとsystem_failureを機械的に区別できる
- 候補者の低得点をNEへ逃がさない
- AI欠陥の影響外までNEを広げない
- Exercise AとBのmatrix検査が共通実装を使用する
- stateラベルやcase IDに依存せず同じrunnerで再生成できる
- 保存済みマトリクスが決定論的に再現される
- CIが全成功する

この完了後、Exercise Bをv0.1校正セットとして一区切りとし、Exercise Cの完全Episode展開へ進む。
