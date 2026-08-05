# Exercise A system_failure 分離ケース v0.1

## 1. 目的

Exercise Aの`system_failure`ケースを追加し、利用者本人の弱い行動による低得点と、AI・進行側の欠陥によって評価機会が失われた場合の`NE`を分離する。

本ケースは合成Episodeによる校正用検証であり、採用判断には使用しない。

## 2. lowとの違い

`low`ケースではAI品質と12の評価機会が正常であり、利用者が機会を十分に活用しなかった結果を1〜2点で評価する。評価機会が存在するため、低い行動を`NE`へ変換しない。

`system_failure`ケースでは、AIが利用者の最初の発言より前に優先対象と中心案を定義する。この先回りにより、一部の評価機会が利用者へ公平に提供されなかったため、その影響軸だけを`NE`とする。

## 3. 発生させるシステム欠陥

最初のAI発言が`define_scope`を実行し、次を発生させる。

- `A-R01`: fail
- `A-PROH-01`: fail
- System Quality status: `fail`
- `user_agency`: 2

非公開懸念の開示順序は正常に維持し、`A-R04`と`A-PROH-02`はpassとする。

## 4. 無効化する評価機会

`A-PROH-01`の影響を受ける次の5機会を`invalid`とする。

- `A-OP-IS-01`
- `A-OP-IS-02`
- `A-OP-IS-03`
- `A-OP-VA-01`
- `A-OP-VA-02`

残る7機会は`offered`かつ利用者応答ありとして維持する。

## 5. 評価結果

システム欠陥の影響を受けた次の2軸だけを`NE`とする。

- `issue_framing`: `NE / AI_QUALITY_FAILURE`
- `valuable_contribution`: `NE / AI_QUALITY_FAILURE`

影響を受けていない5軸は利用者本人の証拠発言から数値評価する。

- `logical_reasoning`: 2
- `listening_and_response`: 3
- `collaboration_and_relationship`: 3
- `decision_and_consensus`: 3
- `process_and_time_management`: 2

System Quality全体がfailであっても、無関係な軸へ一括して`NE`を伝播させない。

## 6. EvaluationResult検査の強化

`AI_QUALITY_FAILURE`を理由とする`NE`には、次を必須とする。

1. 対象dimensionが失敗したSystem Quality ruleの影響軸に含まれる
2. 対象dimensionに`invalid`な評価機会が存在する
3. 最終証拠発言は空である

無効化された機会への数値採点は拒否する。一方、NEの原因説明として無効化イベントIDをRater Sheetへ保存することは許可する。

## 7. CI検査

`scripts/check_exercise_a_system_failure.py`で次を確認する。

- system_failure成果物のgolden完全一致
- 2回実行の決定性
- System Qualityの失敗ルールが`A-R01`と`A-PROH-01`だけである
- 5機会だけがinvalidになる
- 2軸だけがNEになる
- 非影響5軸がmediumと同じ数値を維持する
- lowケースはSystem Quality passかつ全7軸が1〜2点の数値である
- invalid機会への数値採点を拒否する
- 無効化されていない軸を`AI_QUALITY_FAILURE`でNEにすることを拒否する

## 8. 完了条件

- lowとsystem_failureの差を機械検査で説明できる
- candidate underperformanceをNEへ逃がさない
- system failureをcandidate low scoreへ転嫁しない
- 影響範囲外の数値評価を保持する
- runnerは`state`ラベルを評価生成に使用しない
