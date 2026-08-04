# 35マイクロアンカー仕様 v0.1

## 1. 目的

人間評価者が、7サブディメンションの1・2・3・4・NEを同じ基準で判断できるよう、短い局所Episodeを35件作る。

このPRでは完成した35件そのものではなく、作成・検査・受入れの仕様を確定する。

## 2. 必須カバレッジ

7軸それぞれについて次を1件ずつ作る。

- score 1
- score 2
- score 3
- score 4
- NE

合計35件とする。

## 3. ID規則

```text
anchor-<dimension-short>-<score-or-ne>-<serial>
```

例:

- `anchor-if-1-001`
- `anchor-ls-4-001`
- `anchor-dc-ne-001`

短縮名:

| Dimension | Short |
|---|---|
| issue_framing | if |
| logical_reasoning | lr |
| listening_and_response | ls |
| valuable_contribution | vc |
| collaboration_and_relationship | cr |
| decision_and_consensus | dc |
| process_and_time_management | pt |

## 4. 1件の構成

各アンカーは次を持つ。

- anchor_id
- rubric_version
- target_dimension
- target_score
- scenario_context
- opportunity_description
- participants
- 3〜8発言のmicro_episode
- expected_evidence_message_ids
- expected_not_evaluable_reason
- rationale
- boundary_note
- prohibited_inference_note
- author
- reviewer
- approval_status

## 5. 作成原則

- 対象軸以外の情報を必要最小限にする
- 点数差が発言量だけで決まらないようにする
- 1とNEを明確に分ける
- 4は複数場面の独立証拠を含める
- 2と3は「行動の有無」ではなく、完全性・一貫性・議論への作用で差を作る
- 名前、性別、年齢、アクセント等を判断材料にしない
- AI側の失敗を含む場合はNEアンカーとして明示する

## 6. 境界の確認

各アンカーは隣接点との違いを説明する。

例:

- なぜ1ではなく2か
- 何が追加されれば2から3になるか
- なぜ3ではなく4か
- なぜ低得点ではなくNEか

## 7. 受入れ条件

- 2名以上の評価者が独立採点する
- 期待点との差が1点以内
- 4点アンカーは証拠2件以上
- NEアンカーは評価機会不足等が明示される
- 証拠IDが実在し、対象利用者の発言である
- 境界説明を第三者が再現できる

## 8. 将来の保存先

```text
fixtures/anchors/<dimension>/<anchor-id>.json
```

SchemaはPR #4またはアンカー実装PRで追加し、本仕様を正本とする。
