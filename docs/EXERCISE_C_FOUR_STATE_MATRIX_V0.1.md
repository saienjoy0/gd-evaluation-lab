# Exercise C Four-State Matrix v0.1

## 1. 目的

Exercise C「時間制約付き意思決定」の`high`、`medium`、`low`、`system_failure`を一つの横断マトリクスとして確定し、候補者行動差による数値評価と、AI品質不良による評価不能を同じ検査基盤で説明可能にする。

本成果物は合成Episodeによる練習・研究・校正用であり、採用合否の自動決定には使用しない。

## 2. 4状態

| state | System Quality | offered | invalid | 数値軸 | NE軸 |
|---|---|---:|---:|---:|---:|
| `high` | pass | 15 | 0 | 7 | 0 |
| `medium` | pass | 15 | 0 | 7 | 0 |
| `low` | pass | 15 | 0 | 7 | 0 |
| `system_failure` | fail | 8 | 7 | 4 | 3 |

得点順は次のとおりである。

| state | IF | LR | LS | VC | CR | DC | PT |
|---|---:|---:|---:|---:|---:|---:|---:|
| high | 3 | 4 | 4 | 4 | 4 | 4 | 4 |
| medium | 2 | 3 | 3 | 2 | 2 | 3 | 3 |
| low | 1 | 1 | 2 | 1 | 1 | 1 | 1 |
| system_failure | 2 | NE | NE | 2 | 2 | NE | 3 |

## 3. 正常3状態の統制

`high`、`medium`、`low`では、Scenario、AI参加者、AI発言、System Quality、15件の評価機会、runner・rubric・評価器versionを同一に固定する。

異なるのは候補者発言、候補者行動event、人間評価結果、Feedback、case固有IDだけである。

全7軸で`high > medium > low`を満たし、lowは15機会すべてが観察可能であるためNEへ置き換えない。

## 4. system_failureの分離

`system_failure`では、mediumのAI発言`m025`だけを変更する。

- medium: 遅延リスク開示前の通常challenge
- system_failure: 遅延リスク開示前に結論を確定する`propose_decision`

m025ではtextとmoveだけを変更し、message ID、参加者、phase、時刻、generation IDは維持する。候補者発言とm025以外のAI発言はmediumと同一に保つ。

この欠陥により`C-PROH-01`だけがfailし、次の7機会をinvalidとする。

- `C-OP-LO-01`
- `C-OP-LO-02`
- `C-OP-LI-01`
- `C-OP-LI-02`
- `C-OP-DE-01`
- `C-OP-DE-02`
- `C-OP-DE-03`

次の3軸だけを`NE / AI_QUALITY_FAILURE`とする。

- logical reasoning
- listening and response
- decision and consensus

issue framing、valuable contribution、collaboration and relationship、process and time managementはmediumと同じ数値を維持する。

## 5. state非依存

共通runnerはstateラベルを採点入力として受け取らない。checkerは`gd_eval`配下のPython ASTを走査し、状態文字列が評価中核へハードコードされていないことを確認する。

状態別期待値は校正checkerにのみ保持し、評価中核へ分岐を追加しない。

## 6. 実装

- 共通checker: `scripts/calibration_four_state_matrix.py`
- C専用入口: `scripts/check_exercise_c_four_state_matrix.py`
- Schema: `schemas/exercise-four-state-matrix-v0.1.schema.json`
- JSON正本: `fixtures/calibration/matrices/exercise-c-four-state-v0.1.json`
- Markdown正本: `fixtures/calibration/matrices/exercise-c-four-state-v0.1.md`

保存済みJSON・Markdownは生成入力に使用せず、4ケースをrunnerで再実行して得たmatrixとのoracle比較にのみ使用する。

## 7. CI検査

CIは次を確認する。

- 4ケースのgolden完全再生と決定性
- 正常3状態のAI発言、System Quality、15機会の一致
- 全7軸の`high > medium > low`
- lowの7軸数値・NEなし
- system_failureの失敗ruleが`C-PROH-01`だけ
- 7機会invalid・3軸NE
- 非影響4軸がmediumと同値
- mediumとsystem_failureの候補者発言が同一
- AI差分がm025のtextとmoveだけ
- Scenario、version、rubric、AI identityの統制
- runnerのstate非依存
- Schema、JSON、Markdown正本との完全一致
- 負例検査
- Exercise A・B matrixの回帰なし

## 8. 完了後

Exercise C matrixの完成により、標準演習A・B・Cすべてでhigh / medium / low / system_failureが揃う。次工程は7評価軸×5境界の35マイクロアンカー作成とする。
