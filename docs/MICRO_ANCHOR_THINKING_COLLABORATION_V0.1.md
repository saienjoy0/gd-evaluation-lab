# Micro Anchor Thinking + Collaboration v0.1

## 1. 目的

既存のMicro Anchor基盤へ、次の4軸のscore 1 / 2 / 3 / 4 / NEを追加する。

- logical_reasoning
- valuable_contribution
- listening_and_response
- collaboration_and_relationship

新しいSchema、専用checker、専用負例は追加しない。

## 2. カバレッジ

| Dimension | 1 | 2 | 3 | 4 | NE |
|---|---:|---:|---:|---:|---:|
| issue_framing | ✅ | ✅ | ✅ | ✅ | ✅ |
| logical_reasoning | ✅ | ✅ | ✅ | ✅ | ✅ |
| valuable_contribution | ✅ | ✅ | ✅ | ✅ | ✅ |
| listening_and_response | ✅ | ✅ | ✅ | ✅ | ✅ |
| collaboration_and_relationship | ✅ | ✅ | ✅ | ✅ | ✅ |
| decision_and_consensus | - | - | - | - | - |
| process_and_time_management | - | - | - | - | - |

実装済みは25 / 35件である。

## 3. 共通場面

- Logical Reasoning: 食品ロス削減策を費用、実現性、削減効果で比較する。
- Valuable Contribution: 広告強化と値下げという既出案を改善する。
- Listening and Response: 出社重視とリモート重視の懸念を扱う。
- Collaboration and Relationship: 強い反対意見と未発言者を扱う。

各軸のscore 1〜4では、Scenario、参加者、非対象発言、発言順、候補者ターン位置、opportunity IDを固定し、候補者のtextとmoveだけを変更する。

## 4. 境界

- score 1: 十分な機会があるが、期待行動が見られないか議論を妨げる。
- score 2: 一部行動はあるが、表面的または不完全。
- score 3: 期待行動が明確で、議論を前進させる。
- score 4: 異なるphaseの二証拠で、高度な統合・弱点処理・全体改善を示す。
- NE: AI品質不良、記録欠損、Scenario契約不良、機会不足で評価不能。

## 5. 検査

既存の次の検査だけを使用する。

```bash
python scripts/check_micro_anchor_contract.py
python scripts/check_micro_anchor_set.py
python scripts/export_micro_anchor_blind_pack.py --check
python scripts/check_micro_anchor_negative_fixtures.py
```

Manifestは25件へ更新する。Blind Packは生成時に期待値を除去し、件数とSHA-256を正本として保存する。各アンカーは人間校正前のため`draft`を維持する。

## 6. 次工程

次はdecision_and_consensusとprocess_and_time_managementの10件を追加し、35 / 35へ到達する。
