# Exercise C Medium Vertical Slice v0.1 実装設計書

## 1. 目的

Exercise C「時間制約下の意思決定」を、既存の共通Full-Episode runnerでScenarioからFeedbackまで決定論的に再生成できる状態にする。

本PRはExercise Cの`medium`だけを対象とする。`high`、`low`、`system_failure`、4状態マトリクスは後続PRへ分離する。

本成果物は合成Episodeによる研究・校正用検証であり、採用合否の自動決定には使用しない。

## 2. 現在地と未実装箇所

Exercise A・Bは4状態校正まで完了している。Exercise CのScenario、15件の評価機会、required action、禁止条件、instance rubricは既に正本として存在するが、共通runner側にC固有の実装がまだない。

現行コードで再利用できるもの:

- 共通Full-Episode loader / runner / manifest
- `summary_contains_fields`
- System Quality集約とNEマッピング
- Opportunity Eventと候補者応答の所有者・時刻・phase検査
- 人間Rater Sheet、Adjudication、Feedback生成
- state非依存のcase profile

新規実装が必要なもの:

### 決定論的rule

1. `time_checkpoints_followed_by_candidate_turn`
2. `private_concern_revealed_before_phase`
3. `candidate_prioritizes_after_time_check`
4. `candidate_compares_and_revises`

`summary_contains_fields`は既存共通handlerを再利用する。

### System Quality禁止条件

1. `finalize_before_risk_reveal`
2. `skip_summary`

### Opportunity trigger / context

Exercise C固有のtriggerとrequired contextをfail-closedで実装する。未実装名を推測で通さない。

## 3. 演習条件

テーマ:

> 新卒研修を対面、オンライン、ハイブリッドのどれで実施するか、限られた時間で決める。

共通条件:

- 参加者120名
- 地域採用者45名
- 予算600万円
- 実施準備期限30日
- 受講完了率90%以上
- 配属前の基礎演習が必要
- 地域採用者が参加可能であること
- セッション長720秒

AI参加者:

| ID | 立場 | 初期案 | private concern |
|---|---|---|---|
| `ai_c_learning` | 学習効果担当 | 対面 | 会場は二日間のみ確保可能 |
| `ai_c_operations` | 運用・セキュリティ担当 | オンライン | 個人端末から演習環境へ接続不可 |
| `ai_c_newhire` | 地域採用者代表 | ハイブリッド | 一部参加者は入社前日まで移動不可 |

## 4. PR境界

### このPRで行う

- C固有rule / quality / opportunity handler実装
- medium Episode 1本
- Rater Sheet 2本とAdjudication
- 5種golden成果物
- Feedback
- generatorとchecker
- 負例検査
- CI、README、Current Status、decision record更新

### このPRで行わない

- high / low会話の生成
- system_failure会話の生成
- C 4状態マトリクス
- 35マイクロアンカー
- LLM Judge
- gd-app接続
- 評価点の企業別重み付け

## 5. 実装アーキテクチャ

### 5.1 Rule層

新規ファイル:

```text
gd_eval/rules/time_boxed_decision.py
```

登録先:

```text
gd_eval/rules/registry.py
```

handlerはScenario IDやstate文字列で採点分岐しない。rule IDに対応する純粋な証拠検査として実装する。

### 5.2 System Quality層

新規ファイル:

```text
gd_eval/quality/time_boxed_decision.py
```

登録先:

```text
gd_eval/quality/system_quality.py
```

### 5.3 Opportunity層

新規ファイル:

```text
gd_eval/opportunities/time_boxed_decision.py
```

登録先:

```text
gd_eval/opportunities/resolver.py
```

Trigger handlerとContext handlerを分離する。

### 5.4 Fixture層

```text
fixtures/calibration/full-episodes/time-boxed-decision/medium/
├── case.json
├── episode.json
├── rater-sheet-a.json
├── rater-sheet-b.json
├── adjudication.json
├── deterministic-rule-result.json
├── system-quality-result.json
├── opportunity-resolution.json
├── evaluation-result.json
└── expected-feedback.json
```

## 6. 決定論的rule詳細

## 6.1 C-R01 `time_checkpoints_followed_by_candidate_turn`

目的:

- 経過40%と75%付近で時間圧が提示されたか
- 提示後に候補者が応答できるターンが残されたか

入力params:

```json
{
  "checkpoints_percent": [40, 75],
  "minimum_candidate_turns_after_each": 1,
  "tolerance_percent_of_duration": 5,
  "maximum_response_delay_ms": 90000
}
```

Scenario JSONへ後ろ2項目を明示追加する。暗黙の定数にしない。

判定:

1. `duration_seconds * 1000`から期待時刻を計算する。
2. 各checkpointについて`TIME_CHECKPOINT_REACHED`イベントを1件以上要求する。
3. `checkpoint_percent`が期待値と一致することを要求する。
4. イベント時刻が期待時刻の±5%セッション長以内であることを要求する。
5. イベントが参照するmessageはAI発言、`move=time_check`であることを要求する。
6. その後90秒以内かつ次checkpoint前に、候補者本人の発言を最低1件要求する。
7. 候補者発言がcheckpointより前ならfailする。

mediumの期待時刻:

| checkpoint | 理論時刻 | 設計イベント時刻 |
|---|---:|---:|
| 40% | 288,000ms | 290,000ms |
| 75% | 540,000ms | 544,000ms |

## 6.2 C-R02 `private_concern_revealed_before_phase`

目的:

最終判断前に重大リスクが最低1件、正規のtriggerを経て開示されたことを保証する。

判定:

- `PRIVATE_CONCERN_REVEALED`を対象にする。
- `late_risk=true`を要求する。
- `concern_id`がScenario内AI participantのprivate concernと対応することを要求する。
- 開示messageが実在し、AI発言であることを要求する。
- 最初の`decision` phase発言開始より前に開示されることを要求する。
- `minimum_concerns`以上の一意なconcernを要求する。

mediumではセキュリティ制約を遅延リスクとして使う。

## 6.3 C-R03 `candidate_prioritizes_after_time_check`

目的:

候補者が時間通知を聞いただけでなく、未解決論点の順番または残作業を具体的に変更したことを確認する。

判定:

- `TIME_CHECKPOINT_REACHED`後の候補者発言を対象にする。
- `move=prioritize`を要求する。
- 発言は対象checkpoint後、次checkpointまたはセッション終了前であることを要求する。
- `PRIORITY_UPDATE_RECORDED`イベントが候補者message IDを参照することを要求する。
- イベントに`ordered_items`が2件以上あることを要求する。
- `minimum_occurrences`以上を要求する。

mediumでは40%・75%の両方で行うが、Scenario rubricの合格条件は最低1回のままとする。checkerではmedium固有条件として2回を要求する。

## 6.4 C-R04 `candidate_compares_and_revises`

目的:

三案比較と、遅延リスクを受けた意思決定修正を別々に観察する。

判定:

### 比較

- 候補者の`move=compare_options`を要求する。
- `OPTIONS_COMPARED`イベントが存在することを要求する。
- `options`に`対面 / オンライン / ハイブリッド`の3案すべてを要求する。
- `criteria`が2件以上あることを要求する。

### 修正

- `late_risk=true`のrisk reveal後に候補者発言を要求する。
- `DECISION_REVISION_RECORDED`イベントを要求する。
- `before_message_id`と`after_message_id`が実在することを要求する。
- `after_message_id`は候補者本人かつrisk reveal後であることを要求する。
- `changed_fields`が1件以上あることを要求する。
- `requires_risk_response=true`なら比較だけではpassさせない。

## 6.5 C-R05 `summary_contains_fields`

既存共通handlerを再利用する。

対象イベント:

```text
SUMMARY_RECORDED
```

必須field:

- `mode`
- `exception`
- `next_check`

medium checkerでは、field名だけでなく値が空でないことも追加検査する。

## 7. System Quality禁止条件

## 7.1 C-PROH-01 `finalize_before_risk_reveal`

対象はAI・システム側の先回りである。候補者の暫定案は違反扱いしない。

fail条件:

- 必須late riskがまだ開示されていない
- その時点でAIが次のmoveを行う
  - `propose_decision`
  - `confirm_consensus`
  - `summarize`
- または明示的`PROHIBITED_CONDITION_TRIGGERED / C-PROH-01`が存在する

影響軸:

- `logical_reasoning`
- `listening_and_response`
- `decision_and_consensus`

mediumではpassする。

## 7.2 C-PROH-02 `skip_summary`

fail条件:

- 候補者本人の`phase=summary / move=summarize`がない
- または`SESSION_CLOSED`が候補者summaryより前に発生する
- または明示的`PROHIBITED_CONDITION_TRIGGERED / C-PROH-02`が存在する

影響軸:

- `decision_and_consensus`
- `process_and_time_management`

severityはScenario正本どおり`major`とする。mediumではpassする。

## 8. Opportunity trigger設計

C固有triggerを次のように定義する。

| Trigger | 成立条件 |
|---|---|
| `after_success_requirements` | `SUCCESS_REQUIREMENTS_PRESENTED`が先行し、3要件が記録済み |
| `after_three_options_present` | `OPTIONS_PRESENTED`が先行し、3案すべてが記録済み |
| `after_late_risk_reveal` | `late_risk=true`の`PRIVATE_CONCERN_REVEALED`が先行 |
| `after_security_question` | `SECURITY_CONCERN_STATUS / open`が先行 |
| `after_constraint_collision` | `CONSTRAINT_COLLISION_RECORDED`が先行し、2制約以上が衝突 |
| `before_final_alignment` | 将来に候補者`confirm_consensus`が存在 |
| `after_criteria_defined` | 候補者`define_criteria`と`CRITERIA_RECORDED`が先行 |
| `before_consensus_confirmation` | 将来に候補者`confirm_consensus`が存在 |
| `at_40_percent_time_checkpoint` | 40%の`TIME_CHECKPOINT_REACHED`と時刻許容範囲が成立 |
| `at_75_percent_time_checkpoint` | 75%の`TIME_CHECKPOINT_REACHED`と時刻許容範囲が成立 |

`before_session_close`は既存共通handlerを再利用する。

## 9. Opportunity context設計

| Context | 成立条件 |
|---|---|
| `decision_criteria_incomplete` | `CRITERIA_RECORDED`がまだ存在しない |
| `three_options_available` | `OPTIONS_PRESENTED.options`が3案を含む |
| `risk_requires_reassessment` | late risk開示後、revision前 |
| `security_concern_open` | `SECURITY_CONCERN_STATUS.status=open` |
| `risk_requires_response` | late riskが開示され、将来に候補者ターンがある |
| `solution_space_open` | 候補者の最終合意がまだ記録されていない |
| `hybrid_solution_possible` | `CONSTRAINT_COLLISION_RECORDED.candidate_modes`に`ハイブリッド`がある |
| `multiple_positions_active` | 既存共通判定を使い、checkerで3AI立場を追加確認 |
| `regional_access_concern_present` | `REGIONAL_ACCESS_CONCERN_STATUS.status=open` |
| `decision_requires_revision` | 暫定案とlate riskがあり、revisionがまだない |
| `implementation_condition_required` | 最終合意前かつ実施条件が未記録 |
| `remaining_time_visible` | 既存共通判定に加えtrigger側で40%checkpointを厳密検査 |
| `unresolved_items_visible` | `UNRESOLVED_ITEMS_RECORDED.items`が1件以上 |
| `summary_required` | 最終決定済みで`SUMMARY_RECORDED`がまだない |

## 10. medium Episode設計

## 10.1 phase配分

| Phase | 時間帯 |
|---|---:|
| problem_definition | 0〜90秒 |
| idea_generation | 90〜320秒 |
| option_comparison | 320〜565秒 |
| decision | 565〜655秒 |
| summary | 655〜720秒 |

40% checkpointをidea_generation、75% checkpointをoption_comparisonに置く。

## 10.2 発言シーケンス

以下をepisode実装時の正本骨格とする。文面の微修正は許すが、message ID、phase、move、時刻、証拠役割は維持する。

| ID | 時刻ms | 話者 | phase | move | 目的 |
|---|---:|---|---|---|---|
| m001 | 10000-20000 | learning | problem_definition | propose_idea | 対面案 |
| m002 | 22000-32000 | operations | problem_definition | propose_idea | オンライン案 |
| m003 | 34000-44000 | newhire | problem_definition | propose_idea | ハイブリッド案 |
| m004 | 48000-56000 | operations | problem_definition | ask_question | 成功要件と比較軸を候補者へ残す |
| m005 | 58000-72000 | candidate | problem_definition | define_criteria | 完了率、演習、参加可能性、費用、セキュリティを列挙 |
| m006 | 90000-100000 | learning | idea_generation | challenge | 会場二日制約 |
| m007 | 105000-115000 | operations | idea_generation | ask_question | セキュリティ問い |
| m008 | 118000-132000 | candidate | idea_generation | respond_to_question | 管理端末利用を検討 |
| m009 | 136000-146000 | newhire | idea_generation | challenge | 地域採用者の移動制約 |
| m010 | 150000-166000 | candidate | idea_generation | propose_idea | ハイブリッド初案 |
| m011 | 170000-180000 | learning | idea_generation | challenge | 実技品質への懸念 |
| m012 | 184000-198000 | candidate | idea_generation | integrate | 対面核＋オンライン準備を統合 |
| m013 | 205000-215000 | operations | idea_generation | challenge | 端末運用コスト |
| m014 | 220000-236000 | candidate | idea_generation | respond_to_question | 対象演習限定を提案 |
| m015 | 242000-252000 | learning | idea_generation | compare_options | 学習効果比較を促す |
| m016 | 256000-274000 | candidate | idea_generation | propose_idea | 暫定検討順を示す |
| m017 | 284000-290000 | operations | idea_generation | time_check | 40%時間通知 |
| m018 | 294000-309000 | candidate | idea_generation | prioritize | セキュリティ→参加可能性→学習効果の順に整理 |
| m019 | 322000-334000 | learning | option_comparison | challenge | 対面の学習効果を再主張 |
| m020 | 338000-356000 | candidate | option_comparison | compare_options | 三案を基準比較 |
| m021 | 360000-370000 | newhire | option_comparison | challenge | 地域参加の弱点 |
| m022 | 374000-388000 | candidate | option_comparison | integrate | 例外参加を含む統合案 |
| m023 | 392000-402000 | operations | option_comparison | ask_question | セキュリティ条件確認 |
| m024 | 406000-422000 | candidate | option_comparison | propose_decision | 暫定ハイブリッド案 |
| m025 | 430000-440000 | learning | option_comparison | challenge | 二日間で実技不足の懸念 |
| m026 | 444000-458000 | candidate | option_comparison | prioritize | 必須実技と事前学習を分離 |
| m027 | 466000-478000 | operations | option_comparison | challenge | 個人端末接続不可をlate riskとして開示 |
| m028 | 482000-500000 | candidate | option_comparison | integrate | 管理端末・共有会場を条件へ追加し案修正 |
| m029 | 505000-515000 | newhire | option_comparison | challenge | 入社前日まで移動不可 |
| m030 | 520000-535000 | candidate | option_comparison | integrate | 遅延参加者の例外対応 |
| m031 | 538000-544000 | operations | option_comparison | time_check | 75%時間通知 |
| m032 | 548000-562000 | candidate | option_comparison | prioritize | 未解決項目を端末数・例外対象・確認責任者へ限定 |
| m033 | 566000-584000 | candidate | decision | propose_decision | 条件付きハイブリッド最終案 |
| m034 | 588000-598000 | learning | decision | support | 実技条件付き賛成 |
| m035 | 600000-610000 | operations | decision | support | 管理端末条件付き賛成 |
| m036 | 612000-622000 | newhire | decision | ask_question | 例外対象確認 |
| m037 | 624000-638000 | candidate | decision | integrate | 遅延参加者例外と確認指標を追加 |
| m038 | 640000-650000 | candidate | decision | confirm_consensus | 最終合意確認 |
| m039 | 660000-680000 | candidate | summary | summarize | mode / exception / next_checkを要約 |

## 10.3 最終決定

mediumの決定内容:

- mode: 条件付きハイブリッド
- 対面: 二日間の必須実技
- オンライン: 事前知識と事後復習
- セキュリティ: 会社管理端末または指定会場端末を使用
- exception: 入社前日まで移動できない地域採用者は遠隔導入と後日実技
- next_check: 7日以内に端末数、対象者数、会場割当、責任者を確認

最終案は実務上の唯一の正解として扱わない。評価対象は比較・修正・合意・時間管理行動である。

## 11. 構造化イベント

最低限、次をepisodeへ記録する。

```text
OPTIONS_PRESENTED
SUCCESS_REQUIREMENTS_PRESENTED
CRITERIA_RECORDED
SECURITY_CONCERN_STATUS
REGIONAL_ACCESS_CONCERN_STATUS
CONSTRAINT_COLLISION_RECORDED
TIME_CHECKPOINT_REACHED
PRIORITY_UPDATE_RECORDED
OPTIONS_COMPARED
PRELIMINARY_DECISION_RECORDED
PRIVATE_CONCERN_REVEALED
DECISION_REVISION_RECORDED
UNRESOLVED_ITEMS_RECORDED
IMPLEMENTATION_CONDITION_RECORDED
SUMMARY_RECORDED
OPPORTUNITY_OFFERED
```

イベントは自然言語単語一致の代替ではなく、発言と評価機会を追跡する索引として使用する。全イベントのmessage ID、timestamp、candidate response IDをcheckerで検証する。

## 12. 15評価機会の割当

| Opportunity | Response |
|---|---|
| C-OP-IS-01 | m005 |
| C-OP-LO-01 | m020 |
| C-OP-LO-02 | m028 |
| C-OP-LI-01 | m008 |
| C-OP-LI-02 | m028 |
| C-OP-VA-01 | m010 |
| C-OP-VA-02 | m022 |
| C-OP-CO-01 | m012 |
| C-OP-CO-02 | m037 |
| C-OP-DE-01 | m020 |
| C-OP-DE-02 | m028 |
| C-OP-DE-03 | m037 |
| C-OP-PR-01 | m018 |
| C-OP-PR-02 | m032 |
| C-OP-PR-03 | m039 |

期待summary:

```json
{
  "offered": 15,
  "not_offered": 0,
  "invalid": 0,
  "with_candidate_response": 15
}
```

## 13. medium校正スコア

最終期待値:

| Dimension | Score | 主証拠 | 理由 |
|---|---:|---|---|
| issue_framing | 2 | m005 | 基準は列挙するが優先順位と論点構造がまだ弱い |
| logical_reasoning | 3 | m020, m028 | 三案比較とrisk後修正が明確 |
| listening_and_response | 3 | m008, m028 | 問いとlate riskへ直接応答 |
| valuable_contribution | 2 | m010, m022 | 実行案は出すが重要な制約発見はAI依存 |
| collaboration_and_relationship | 2 | m012, m037 | 統合はするが参加促進・対立調整は限定的 |
| decision_and_consensus | 3 | m020, m028, m033, m037, m038 | 基準比較、修正、条件付き合意がある |
| process_and_time_management | 3 | m018, m032, m039 | 両checkpoint後に優先順位を調整し要約する |

score profile:

```text
2 / 3 / 3 / 2 / 2 / 3 / 3
```

全7軸を数値評価し、NEは0件とする。

将来の4状態校正余白:

| State | 想定score profile |
|---|---|
| high | 3 / 4 / 4 / 3 / 3 / 4 / 4 |
| medium | 2 / 3 / 3 / 2 / 2 / 3 / 3 |
| low | 1 / 1 / 2 / 1 / 1 / 1 / 1 |

high / lowの値は後続PRで証拠に基づき最終確定するが、全7軸で`high > medium > low`を成立させられる設計とする。

## 14. 人間評価設計

### Rater A

```text
2 / 3 / 3 / 2 / 2 / 3 / 3
```

### Rater B

```text
3 / 3 / 3 / 2 / 2 / 3 / 3
```

想定不一致:

- issue_framingのみ2対3

Adjudication:

- 最終2
- m005は複数基準を提示するが、基準の重み・検討順・主要トレードオフをこの時点で構造化していない
- 後のm018は時間管理証拠として扱い、初期の課題設定を3へ引き上げる独立証拠とはしない

この境界説明を残し、将来のmicro anchor作成へ再利用する。

## 15. checker設計

新規:

```text
scripts/check_exercise_c_medium.py
```

正常系検査:

1. case profileのexercise/state/version
2. golden完全再生
3. 二回実行の決定性
4. manifest検証
5. 全Schema適合
6. C-R01〜C-R05がpass
7. C-PROH-01 / C-PROH-02がpass
8. System Qualityがpass
9. 15機会すべてoffered / observed
10. scoreが`2/3/3/2/2/3/3`
11. NEなし
12. 40% / 75% checkpoint時刻
13. checkpoint後の候補者prioritize
14. late riskがdecision前
15. revisionがlate risk後
16. summaryの3fieldと値
17. 数値証拠が候補者本人
18. Opportunity responseがtrigger後

## 16. 負例テスト

最低15件を実装する。

### Rule負例

1. 40% checkpointを削除 → C-R01 fail
2. 75% checkpointを削除 → C-R01 fail
3. checkpointを許容範囲外へ移動 → C-R01 fail
4. checkpoint後の候補者ターンを削除 → C-R01 fail
5. late riskをdecision後へ移動 → C-R02 fail
6. risk eventのconcern IDを壊す → C-R02 fail
7. candidate prioritizeを通常提案へ変更 → C-R03 fail
8. PRIORITY_UPDATE_RECORDEDを削除 → C-R03 fail
9. OPTIONS_COMPAREDから1案を削除 → C-R04 fail
10. revision eventを削除 → C-R04 fail
11. revisionをrisk前へ移動 → C-R04 fail
12. summaryからmodeを削除 → C-R05 fail
13. summaryからexceptionを削除 → C-R05 fail
14. summaryからnext_checkを削除 → C-R05 fail

### Quality負例

15. AIがlate risk前にpropose_decision → C-PROH-01 fail
16. candidate summaryを削除 → C-PROH-02 fail
17. SESSION_CLOSEDをsummary前へ移動 → C-PROH-02 fail

### Opportunity / Evidence負例

18. 未実装trigger名へ変更 → fail-closed
19. required contextを壊す → context invalid
20. Opportunity eventをresponse後へ移動 → response-before-trigger
21. AI発言IDをcandidate responseに設定 → evidence owner mismatch
22. response phaseを変更 → phase mismatch
23. Opportunity dimensionを変更 → dimension mismatch

checkerの負例は、単に例外が出たことではなく、期待したerror codeまたはrule IDで失敗したことを検証する。

## 17. generator設計

新規:

```text
scripts/generate_exercise_c_medium.py
```

役割:

- authored入力の`case.json / episode.json / rater sheets / adjudication`は変更しない
- 共通runnerを実行する
- 5種goldenをcanonical JSONで書き出す
- 再実行して差分0を保証する

CI:

```bash
python scripts/generate_exercise_c_medium.py
git diff --exit-code -- fixtures/calibration/full-episodes/time-boxed-decision/medium
python scripts/check_exercise_c_medium.py
```

## 18. CI追加順

既存A/B検査の後へ追加する。

```yaml
- name: Validate Exercise C medium vertical slice
  run: python scripts/check_exercise_c_medium.py

- name: Validate Exercise C medium generator reproducibility
  run: |
    python scripts/generate_exercise_c_medium.py
    git diff --exit-code -- \
      fixtures/calibration/full-episodes/time-boxed-decision/medium
    python scripts/check_exercise_c_medium.py
```

## 19. 変更予定ファイル

```text
docs/EXERCISE_C_MEDIUM_VERTICAL_SLICE.md
gd_eval/rules/time_boxed_decision.py
gd_eval/rules/registry.py
gd_eval/quality/time_boxed_decision.py
gd_eval/quality/system_quality.py
gd_eval/opportunities/time_boxed_decision.py
gd_eval/opportunities/resolver.py
fixtures/scenarios/candidate-assessment-c-time-boxed-decision-v0.1.json
fixtures/calibration/full-episodes/time-boxed-decision/medium/*
scripts/check_exercise_c_medium.py
scripts/generate_exercise_c_medium.py
.github/workflows/knowledge-health.yml
README.md
knowledge/current-status.md
knowledge/decisions/2026-08-05-exercise-c-medium-v0.1.md
```

Scenario変更はC-R01の許容幅と応答期限params追加だけに限定し、topic、opportunity ID、rubric ID、禁止条件IDを変更しない。

## 20. 実装順序

1. C rule moduleとregistry登録
2. C quality moduleとhandler登録
3. C opportunity trigger/context moduleとresolver登録
4. Scenario params追加
5. medium Episodeと構造化イベント作成
6. Rater Sheet 2本とAdjudication作成
7. generatorでgolden生成
8. checker正常系
9. checker負例23件
10. docs / decision / status / README更新
11. CI実行
12. review後にmerge

## 21. 完了条件

- C-R01〜C-R05がすべてpass
- C-PROH-01とC-PROH-02がpass
- System Qualityがpass
- 15機会すべてofferedかつobserved
- invalid 0
- not_offered 0
- 7軸すべて数値
- score profileが`2/3/3/2/2/3/3`
- NE 0
- 40%・75%の時間通知が許容範囲内
- 各通知後に候補者prioritizeがある
- late riskがdecision前に開示される
- risk後に候補者が案を修正する
- 最終summaryにmode / exception / next_checkがある
- Rater 2名とAdjudication履歴がある
- 5種goldenを決定論的に再生成できる
- 23件の負例が期待理由で失敗する
- Exercise A・Bの全CIが維持される
- runnerと評価中核に`medium`等のstate分岐を追加しない

## 22. 後続PR

### PR #16

Exercise C high / low校正。

- AI発言
- System Quality
- 15 Opportunity供給
- Scenario / rubric / version

を同一に保ち、候補者行動だけで全7軸の得点差を作る。

### PR #17

Exercise C system_failureと4状態マトリクス。

候補候補:

- AIがlate risk前に結論を確定しC-PROH-01を発生
- 必要に応じてsummary欠落を別fixtureまたは負例として扱う
- 影響軸だけNE、非影響軸はmediumと同じ数値

Cのsystem_failure範囲はPR #15のmedium実装と負例結果を確認してから最終決定する。
