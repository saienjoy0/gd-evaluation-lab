# gd-evaluation-lab

GD appの評価基準、検証方法、企業導入可能性を継続的に研究するためのリポジトリです。

## このリポジトリが解決する二つの問題

1. **過去の作業を次のAIセッションへ引き継ぐ**
   - Basic Memory互換Markdownで、事実・決定・疑問・関係を保存します。
2. **次に何をすべきかを明確にする**
   - Beadsでタスク、依存関係、優先度、ブロッカーを管理します。

## 役割分担

- `knowledge/`: 長期的に残す知識
- `knowledge/inbox/`: ChatGPT等の会話から抽出した作業記録
- `knowledge/decisions/`: 確定した判断
- `knowledge/current-status.md`: 現在地
- Beads (`bd`): 未完了タスクと依存関係
- `TASKS_FALLBACK.md`: Beads初期化前だけ使う一時タスクリスト

## 毎日の使い方

ChatGPTへ次のように指示します。

> 今日のGD評価研究の内容をリポジトリへ反映して。決定、発見、未解決、次のタスクに分けて。

AIは次を更新します。

1. `knowledge/inbox/YYYY-MM-DD-<topic>.md`
2. 必要な`knowledge/decisions/*.md`
3. `knowledge/current-status.md`
4. Beadsのタスクと依存関係

## 初期設定

`SETUP.md`を参照してください。

## データ取扱い

実名、メールアドレス、Clerk ID、生音声、未匿名化の会話全文、企業機密はコミットしません。
