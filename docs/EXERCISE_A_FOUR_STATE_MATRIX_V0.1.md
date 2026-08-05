# Exercise A Four-State Matrix v0.1

## 1. 目的

Exercise Aの`high`、`medium`、`low`、`system_failure`を一つの横断マトリクスとして確定し、利用者行動差による数値評価と、システム欠陥による評価不能を同じ検査基盤で説明可能にする。

本成果物は合成Episodeによる校正用検証であり、採用合否の自動決定には使用しない。

## 2. 4状態

| state | System Quality | offered | invalid | 数値軸 | NE軸 |
|---|---|---:|---:|---:|---:|
| `high` | pass | 12 | 0 | 7 | 0 |
| `medium` | pass | 12 | 0 | 7 | 0 |
| `low` | pass | 12 | 0 | 7 | 0 |
| `system_failure` | fail | 7 | 5 | 5 | 2 |

## 3. 正常3状態の統制

`high`、`medium`、`low`では次を同一に固定する。

- Scenarioとscenario version
- AI発言本文、phase、move、時刻、generation ID
- System Qualityのrule結果とdimension score
- 12個の評価機会と候補者応答の供給
- runner、rubric、評価器のversion

異なるのは利用者本人の発言と、それに基づく人間評価結果だけである。

全7軸で次を満たす。

```text
high > medium > low
```

`low`は観察可能な機会が十分にあるため、低い行動を`NE`へ置き換えない。

## 4. system_failureの分離

`system_failure`ではAIが利用者より先にscopeを決定し、`A-R01`と`A-PROH-01`がfailする。

この欠陥により次の5機会をinvalidとする。

- `A-OP-IS-01`
- `A-OP-IS-02`
- `A-OP-IS-03`
- `A-OP-VA-01`
- `A-OP-VA-02`

影響を受ける次の2軸だけを`NE / AI_QUALITY_FAILURE`とする。

- `issue_framing`
- `valuable_contribution`

非影響5軸はmediumと同じ数値を維持する。

## 5. state非依存

共通runnerは`CaseProfile.state`を入力として受け取らない。`RuntimeCase`にもstate fieldを持たせない。

さらにcheckerは`gd_eval`配下のPython ASTを走査し、`high`、`medium`、`low`、`system_failure`という状態文字列が評価中核へハードコードされていないことを確認する。

これにより、state名やcase IDによる採点固定を防ぐ。

## 6. 機械可読成果物

- Schema: `schemas/exercise-four-state-matrix-v0.1.schema.json`
- JSON正本: `fixtures/calibration/matrices/exercise-a-four-state-v0.1.json`
- Markdown正本: `fixtures/calibration/matrices/exercise-a-four-state-v0.1.md`
- Checker: `scripts/check_exercise_a_four_state_matrix.py`

checkerは4ケースを共通runnerで再生成し、各caseの既存goldenと照合した後、横断マトリクスを組み立てる。保存済みJSON・Markdownは生成入力に使用せず、生成完了後のoracle比較にのみ使用する。

## 7. CI検査

次を一回の検査で確認する。

- 4つの完全Episodeのgolden完全一致
- 各caseとマトリクスの決定性
- 正常3状態のAI発言、System Quality、12機会の完全一致
- 全7軸の`high > medium > low`
- lowの7軸数値・NEなし
- system_failureの失敗ruleが`A-R01`と`A-PROH-01`だけ
- system_failureの5機会invalid・2軸NE
- 非影響5軸がmediumと同値
- runnerがstate labelを受け取らない
- 評価中核にstate文字列のハードコードがない
- JSON Schema適合
- JSON／Markdown正本との完全一致

## 8. 完了条件

- Exercise Aの4状態を一つの表で説明できる
- 利用者の低得点とシステム起因NEを混同しない
- stateラベルやcase IDに依存せず同じrunnerで再生成できる
- 保存済みマトリクスが決定論的に再現される
- CIが全成功する

この完了後、Exercise Aはv0.1校正セットとして一区切りとし、Exercise B・Cの完全Episode展開へ進む。
