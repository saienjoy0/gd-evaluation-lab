---
title: Micro Anchor Foundation and Issue Framing v0.1 Decision
type: decision
tags: [gd, evaluation, micro-anchor, calibration, issue-framing]
permalink: micro-anchor-foundation-issue-framing-v0-1-decision
updated: 2026-08-06
---

# Micro Anchor Foundation and Issue Framing v0.1 Decision

## Observations

- 35件を無関係な短文例として作ると、シナリオ差や発言量が得点差へ混入する。
- 7軸それぞれを、同一状況から派生するscore 1 / 2 / 3 / 4 / NEの5件ラダーとして作る必要がある。
- score 1とNE、score 2と3、score 3と4の境界は、構造化されたboundary noteとして残す必要がある。
- score 4は異なるphaseの独立証拠2件以上を必要とする。
- AI品質不良により評価機会が失効した場合、候補者の低得点へ変換してはならない。
- 評価者へ期待点を見せないblind exportと、2名以上の独立評価を実装と承認で分離する必要がある。

## Decision

35 Micro Anchors v0.1は、7本のcontrolled ladderとして段階実装する。

最初のPRでは共通Schema、manifest、contract checker、set checker、blind export、negative suiteを作り、Issue Framingの5件だけを縦切りする。

正常なscore 1〜4では、Scenario、参加者、非対象発言、発言順、候補者ターン位置、opportunity IDを同一に固定し、候補者のtextとmoveだけを変更する。

Issue FramingのNEは、AIが候補者の発言前に目的、対象、判断基準を確定する`AI_QUALITY_FAILURE`として作る。

anchor setは5 / 35の間は`partial`とし、各アンカーは人間校正前のため`draft`とする。

## Validation Boundary

自動検査は構造、証拠所有者、機会状態、ラダー統制、発言量偏り、禁止推論、manifest hash、blind leakage、負例を担当する。

「発言が本当に期待点に相当するか」は単語条件で自動決定せず、35件完成後の独立人間評価と調停で確定する。

## Consequences

- Issue Framingはscore 1 / 2 / 3 / 4 / NEの完全ラダーになる。
- score 1〜4の候補者総文字数比は1.8倍以内に制御される。
- Blind Packから期待点、期待証拠、NE理由、rationale、boundary note、承認情報を除去できる。
- 残り6軸は同じ契約で5件単位に追加できる。
- 次工程はLogical Reasoning 5件とValuable Contribution 5件である。

## Relations

- follows [[Exercise C Four-State Matrix v0.1 Decision]]
- implements [[35マイクロアンカー仕様 v0.1]]
- updates [[GD Evaluation Lab Current Status]]
