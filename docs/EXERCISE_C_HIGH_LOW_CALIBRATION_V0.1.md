# Exercise C High / Medium / Low Calibration v0.1

## Purpose

Exercise Cの時間制約付き意思決定について、AI品質や評価機会の違いではなく、候補者行動の質だけでhigh・medium・lowを区別する。

## Controlled Environment

正常3状態では次を完全に固定する。

- Scenarioとversion
- AI参加者、発言本文、phase、move、時刻、generation ID
- System Qualityのstatus、dimension scores、rule results
- 15件の評価機会、offered / observed状態、候補者応答message ID
- prompt versionと評価器version

変化させるのは候補者発言、候補者行動event、人間Rater Sheet、Adjudication、最終評価、Feedbackだけである。

## Score Profiles

| Dimension | High | Medium | Low |
|---|---:|---:|---:|
| issue framing | 3 | 2 | 1 |
| logical reasoning | 4 | 3 | 1 |
| listening and response | 4 | 3 | 2 |
| valuable contribution | 4 | 2 | 1 |
| collaboration and relationship | 4 | 2 | 1 |
| decision and consensus | 4 | 3 | 1 |
| process and time management | 4 | 3 | 1 |

全7軸で`high > medium > low`を満たす。

issue framingは評価機会がC-OP-IS-01の1件だけであり、score 4の複数証拠要件を満たせない。契約を緩めたり別軸の証拠を捏造したりせず、highを3とする。

## High Behavior

highは次を満たす。

- 序盤で優先条件、比較軸、未確定事項を明示する
- 40%通知後にセキュリティ、地域採用者、実技品質の順へ論点を絞る
- 三案の利点・弱点・実施条件を同じ基準で比較する
- 遅延リスク後に端末条件、地域例外、補講条件を明示的に変更する
- 75%通知後に端末数、対象人数、会場、責任者へ残作業を限定する
- 最終合意へ実施方式、例外、確認事項、責任者、fallbackを含める

logical reasoning、listening and response、valuable contribution、collaboration and relationship、decision and consensus、process and time managementのscore 4は複数phaseの証拠を持つ。

## Low Behavior

lowでもAIは正常に動作し、15機会すべてがofferedかつobservedとなる。候補者は全機会に発言するが、次の低品質行動を示す。

- 比較軸を費用だけに縮退させる
- 時間通知後に優先順位を更新しない
- 三案を複数基準で比較しない
- 遅延リスク後も判断条件を変更しない
- 実施条件、例外、次の確認事項を要約しない

したがってlowはNEではなく7軸すべて数値評価となり、C-R03、C-R04、C-R05だけがfailする。System Quality、C-R01、C-R02はpassを維持する。

## Files

- `fixtures/calibration/full-episodes/time-boxed-decision/high/`
- `fixtures/calibration/full-episodes/time-boxed-decision/medium/`
- `fixtures/calibration/full-episodes/time-boxed-decision/low/`
- `scripts/generate_exercise_c_high_low.py`
- `scripts/check_exercise_c_high_low.py`

## Validation

CIは次を検査する。

- 3状態のgolden完全再生
- 2回実行時の決定論的一致
- generator再実行後のfixture差分ゼロ
- AI発言、System Quality、15機会の完全一致
- 15 offered / 15 observed / invalid 0
- 全7軸の厳密なscore順序
- highの6つのscore 4における複数phase証拠
- lowの7軸数値評価、NEなし、strengthなし
- lowに偽のpriority update、revision、complete summary eventがないこと
- case、session、target participant IDの一意性
- runtimeがstate labelを受け取らないこと

## Scope Boundary

この校正は正常3状態だけを扱う。AIが遅延リスクや時間管理の評価機会を壊す`system_failure`は別PRで作成し、その後にExercise Cの4状態マトリクスを確定する。
