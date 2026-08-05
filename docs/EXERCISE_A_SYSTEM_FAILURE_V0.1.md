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

システム欠陥の影響を受け、数値評価に必要な有効機会が残らない次の2軸だけを`NE`とする。

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

数値評価に必要な有効機会数は、各dimensionの`minimum_valid_opportunities`を優先し、未定義の場合は`evidence_policy.minimum_for_scored_result`を使用する。v0.1の各軸では1件である。

`AI_QUALITY_FAILURE`を理由とする`NE`には、次を必須とする。

1. 対象dimensionに影響するSystem Quality ruleが実際にfailしている
2. `invalidated_by`がその失敗ruleと因果的に一致するinvalid機会が存在する
3. 有効な`offered + observed`機会が必要数未満である
4. 最終証拠発言は空である

`INSUFFICIENT_OPPORTUNITY`は、有効な`offered + observed`機会が必要数未満の場合だけ許可する。`INSUFFICIENT_EVIDENCE`など、原因を機械的に確認する契約がまだないNE理由はfail closedで拒否する。

一部機会がinvalidでも、必要数の有効機会が残る場合はNEを拒否し、利用者行動を数値評価する。無効化された機会への数値採点は拒否する一方、NEの原因説明として無効化イベントIDをRater Sheetへ保存することは許可する。

## 7. 数値評価の証拠連結

数値評価では、軸全体に有効機会が存在するだけでは不十分とする。各Rater Sheetは次を満たす。

1. `opportunity_evidence_event_ids`を1件以上持つ
2. 対象軸と同じdimensionの**主要機会**を必要数以上参照する
3. 参照した全機会が`offered + observed`である
4. 選択証拠が、参照した機会の`candidate_response_message_ids`に含まれる
5. rubricが要求する最低証拠数を満たす

一つの発言が複数軸を支える場合は、他dimensionの機会を**補助機会**として明示的に参照できる。ただし、補助機会だけでは数値評価できず、対象軸の主要機会が必ず必要である。

Adjudicationの最終証拠も、独立評価者が明示的に参照した主要・補助機会の応答IDへ結び付いていなければならない。これにより、無関係な利用者発言を使った数値採点を防ぎつつ、複数軸にまたがる実際の行動証拠を保持する。

## 8. Feedbackへの伝播

EvaluationResultだけでなく最終Feedbackにも、評価不能になった軸ごとに次を保存する。

- `evaluation_status: not_evaluable`
- `reason_code`
- 人間向けの理由文

これにより、空欄だけを表示してシステム欠陥の理由が失われることを防ぐ。

## 9. CI検査

`scripts/check_exercise_a_system_failure.py`で次を確認する。

- system_failure成果物のgolden完全一致
- 2回実行の決定性
- System Qualityの失敗ルールが`A-R01`と`A-PROH-01`だけである
- 5機会だけがinvalidになる
- 2軸だけがNEになる
- 非影響5軸がmediumと同じ数値を維持する
- lowケースはSystem Quality passかつ全7軸が1〜2点の数値である
- invalid機会への数値採点を拒否する
- 失敗ruleまたは因果的invalid機会がないNEを拒否する
- 一部invalidでも有効機会が残る軸のNEを拒否する
- 同じ一部invalidケースを数値評価できる
- 偽の`INSUFFICIENT_OPPORTUNITY`を拒否する
- 未実装NE理由をfail closedで拒否する
- 数値評価で空の機会参照をSchemaとEvaluatorの両方が拒否する
- 機会応答と無関係なRater証拠を拒否する
- 機会応答と無関係なAdjudication証拠を拒否する
- FeedbackにNE理由が残る

さらに`scripts/check_numeric_evidence_provenance.py`で、他軸の補助機会だけを使った数値採点を拒否する。

## 10. 完了条件

- lowとsystem_failureの差を機械検査で説明できる
- candidate underperformanceを別NE理由へ逃がさない
- system failureをcandidate low scoreへ転嫁しない
- 一部invalidでも有効機会が残る場合は数値評価を維持する
- 数値評価の証拠が有効機会の応答へ追跡可能である
- 補助機会だけでは数値採点できない
- 影響範囲外の数値評価を保持する
- Feedback上でもNE理由を説明できる
- runnerは`state`ラベルを評価生成に使用しない
