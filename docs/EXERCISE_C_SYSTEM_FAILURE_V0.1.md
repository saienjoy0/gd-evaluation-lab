# Exercise C System Failure Separation v0.1

## Purpose

Exercise Cの`system_failure`を、候補者の低品質行動ではなく、AIが評価機会を壊した状態として分離する。

## Single Defect

故障は`C-PROH-01: finalize_before_risk_reveal`の1件だけとする。

mediumでは、候補者が暫定案を示した後もAIは結論を確定せず、m027で遅延リスクを開示してから候補者が案を修正する。

system_failureでは、m025のAI発言だけを次のように変更する。

- `move`: `challenge` → `propose_decision`
- `text`: 遅延リスク開示前にハイブリッド案を確定する内容

時刻、phase、generation ID、AI参加者、候補者発言、候補者eventは変更しない。

## Causal Invalidation

C-PROH-01によって無効化される評価機会は、Scenario契約で指定された次の7件だけである。

- logical reasoning: C-OP-LO-01 / C-OP-LO-02
- listening and response: C-OP-LI-01 / C-OP-LI-02
- decision and consensus: C-OP-DE-01 / C-OP-DE-02 / C-OP-DE-03

それ以外の8機会はoffered / observedを維持する。

## Expected Evaluation

| Dimension | system_failure | Reason |
|---|---:|---|
| issue framing | 2 | C-PROH-01の影響外 |
| logical reasoning | NE | 主要2機会がinvalid |
| listening and response | NE | 主要2機会がinvalid |
| valuable contribution | 2 | C-PROH-01の影響外 |
| collaboration and relationship | 2 | C-PROH-01の影響外 |
| decision and consensus | NE | 主要3機会がinvalid |
| process and time management | 3 | C-PROH-01の影響外 |

NE reasonは3軸すべて`AI_QUALITY_FAILURE`とする。

## Low Versus System Failure

lowはAI品質が正常で15機会すべてがobservedされ、候補者行動が低品質なため7軸すべて数値評価となる。

system_failureは候補者発言をmediumと同一に保つが、AIの早期確定により3軸の主要機会が失われるためNEとなる。

## Validation

CIは次をfail closedで確認する。

- C-PROH-01だけがfailし、C-PROH-02はpassする
- C-R01〜C-R05は候補者行動どおりpassする
- invalid機会は正確に7件
- offered / observedは正確に8件
- NEは正確に3軸で、reasonはAI_QUALITY_FAILURE
- 影響外4軸はmediumと同じ数値
- lowは7軸数値、NEなしを維持する
- AI差分はm025のtextとmoveだけ
- 候補者発言はmediumと同一
- 故障を除去した状態でAI_QUALITY_FAILUREのNEを拒否する
- invalid機会への数値評価を拒否する
- 一部に有効機会が残る場合の不正NEを拒否する
- C-PROH-02を混在させて影響外数値を残す誤りを拒否する
- generator再実行でfixture差分ゼロ

## Scope Boundary

このPRはExercise C system_failureだけを扱う。high / medium / low / system_failureの4状態マトリクスは次のPRで確定する。
