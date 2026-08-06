# Micro Anchor Foundation + Issue Framing v0.1

## 1. 目的

35マイクロアンカーの共通契約と検査基盤を作り、最初の縦切りとして`issue_framing`のscore 1 / 2 / 3 / 4 / NEを実装する。

本成果物は練習・研究・評価者校正用であり、採用合否の自動決定には使用しない。

## 2. 現在のカバレッジ

| Dimension | 1 | 2 | 3 | 4 | NE |
|---|---:|---:|---:|---:|---:|
| issue_framing | ✅ | ✅ | ✅ | ✅ | ✅ |
| logical_reasoning | - | - | - | - | - |
| listening_and_response | - | - | - | - | - |
| valuable_contribution | - | - | - | - | - |
| collaboration_and_relationship | - | - | - | - | - |
| decision_and_consensus | - | - | - | - | - |
| process_and_time_management | - | - | - | - | - |

実装済みは5 / 35件であり、anchor setのstatusは`partial`とする。

## 3. 共通契約

各アンカーは次を持つ。

- `anchor_id`
- `target_dimension`
- `target_score`
- `target_participant_id`
- scenario context
- evaluation opportunity
- participants
- 3〜8発言のmicro episode
- expected evidence
- NE reason
- rationale
- adjacent boundary note
- prohibited inference note
- author / reviewer / approval status

Schema:

- `schemas/micro-anchor-v0.1.schema.json`
- `schemas/micro-anchor-set-v0.1.schema.json`
- `schemas/micro-anchor-rating-v0.1.schema.json`

## 4. Issue Framingラダー

共通テーマは「若者に良い地域交流施設」の企画とする。

正常なscore 1〜4では、Scenario、参加者、非対象発言、発言順、候補者ターン数、opportunity IDを同一に固定する。異なるのは候補者本人のtextとmoveだけである。

### score 1

十分な機会があるが、個人的な案を繰り返し、目的、対象、制約、判断基準を構造化しない。

### score 2

費用、利用者数など一部の判断要素には触れるが、対象者、成功条件、主要論点の接続が不完全である。

### score 3

目的、対象、制約、判断基準を接続し、議論可能な構造を作る。

### score 4

初期の曖昧さ・論点漏れを特定し、新しい制約後に優先順位を更新する。`m003`と`m005`の異なるphaseを独立証拠とする。

### NE

AIが候補者の発言前に目的、対象、判断基準を確定し、課題設定機会を失効させる。理由は`AI_QUALITY_FAILURE`であり、score 1へ置き換えない。

## 5. ラダー統制

checkerは次を検証する。

- score 1〜4のscenario context一致
- opportunity ID一致
- participants一致
- 非対象発言の完全一致
- 候補者ターン位置とphaseの一致
- 候補者総文字数比1.8倍以内
- 数値評価の証拠1件以上
- score 4の2証拠以上かつ異なるphase
- NEの証拠0件と理由必須
- score 1のsufficient opportunity
- 証拠が対象候補者本人の発言
- move vocabulary適合
- 禁止推論不使用

## 6. Manifest

`fixtures/anchors/anchor-set-v0.1.json`を機械可読な入口とする。

Manifestは次を記録する。

- 期待総数35
- 実装数
- 軸別カバレッジ
- anchor IDとpath
- target score
- 各ファイルのSHA-256

一つの軸を追加する場合、1 / 2 / 3 / 4 / NEの5件を一つの完全なラダーとして追加し、途中状態を許可しない。

## 7. Blind Pack

`fixtures/anchors/blind/issue-framing-v0.1.json`は評価者向けのblind packである。

次を除去する。

- anchor ID
- target score
- expected evidence
- NE reason
- rationale
- boundary note
- approval status
- author / reviewer
- opportunity status

anchor IDのSHA-256順で並べ、score順の推測を避ける。`scripts/export_micro_anchor_blind_pack.py --check`で期待値漏洩とoracle一致を検査する。

## 8. 負例

`fixtures/negative/micro-anchors/cases.json`に17件の負例を置く。

主な検査対象:

- 数値なのに証拠なし
- score 4の証拠不足
- AI発言を候補者証拠へ指定
- 存在しない証拠ID
- NEへの証拠混入
- NE理由不足
- score 1の機会不足
- 発言数範囲違反
- ID重複
- path / dimension不一致
- ラダー欠損・重複
- 禁止推論
- reviewerなしのapproved

## 9. 承認境界

本PRで作るアンカーは`draft`とする。

AIによる作成とCI成功だけでは`approved`へ進めない。35件完成後、2名以上の独立評価、調停、1点以内一致、証拠確認を経て`blind_calibration_pending`から`approved`へ進める。

## 10. 次工程

次はThinking領域の残りとして、次の10件を追加する。

- logical_reasoning: 1 / 2 / 3 / 4 / NE
- valuable_contribution: 1 / 2 / 3 / 4 / NE

完成時の累計は15 / 35件とする。
