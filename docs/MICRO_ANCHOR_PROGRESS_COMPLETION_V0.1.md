# Micro Anchor Progress Completion v0.1

## 1. 目的

既存のMicro Anchor基盤へ、残る2軸のscore 1 / 2 / 3 / 4 / NEを追加し、7軸×5状態の35件を完成する。

- decision_and_consensus
- process_and_time_management

新しい軸専用Schema、checker、negative fixtureは追加しない。

## 2. Decision and Consensus

共通場面は、新サービスの即時限定公開・一か月延期・段階公開から方針を選ぶ議論とする。

- score 1: 比較せず結論を固定し、反対意見を扱わない
- score 2: 一部の理由と条件はあるが、比較と合意形成が不完全
- score 3: 共通基準で比較し、開始・停止・再判断条件を示す
- score 4: 対立を共通基準へ変換し、少数意見、条件、担当、合意確認まで統合する
- NE: AIが候補者より先に最終案と条件を確定する

## 3. Process and Time Management

共通場面は、残り八分で議論が停滞し、一つの提案と二つのリスクへ収束する必要がある状況とする。

- score 1: 時間を無視して論点を増やす
- score 2: 時間不足を指摘するだけで手順を作らない
- score 3: 時間配分、役割、比較対象、収束規則を具体化する
- score 4: 停滞原因を診断し、対立時の代替経路まで含めてプロセスを再設計する
- NE: 時間通知後の主要な候補者発言が記録欠損する

## 4. 完成状態

- Anchor count: 35 / 35
- Coverage: 7 dimensions × score 1 / 2 / 3 / 4 / NE
- Anchor set status: `blind_calibration_pending`
- Individual anchor status: `draft`
- Human double rating: 未実施

35件が揃ったことは内容校正の完了を意味しない。次工程は2名による10件のBlindパイロットである。

## 5. 検査

既存の次の検査だけを使用する。

```bash
python scripts/check_micro_anchor_contract.py
python scripts/check_micro_anchor_set.py
python scripts/export_micro_anchor_blind_pack.py --check
python scripts/check_micro_anchor_negative_fixtures.py
```
