# GD Evaluation Lab — Agent Instructions

このリポジトリは、GD appの評価基準と検証方法を継続的に研究するための正本です。

## セッション開始時

必ず次の順で確認する。

1. `knowledge/project-overview.md`
2. `knowledge/current-status.md`
3. `knowledge/decisions/`の最新ノート
4. `knowledge/inbox/`の最新ノート
5. Beadsが利用可能なら `bd ready --json`
6. Beadsが未初期化なら `TASKS_FALLBACK.md`

## 情報の役割

- `knowledge/`: 長期的に残す知識。Basic Memory形式のMarkdownを使う。
- `knowledge/inbox/`: ChatGPT等の会話から抽出した、その日の作業・発見・疑問。
- `knowledge/decisions/`: 確定した判断と理由。
- `knowledge/current-status.md`: 最新状態だけを書く。
- Beads: 未完了タスク、依存関係、優先度、ブロッカーを管理する。

## ChatGPT会話を反映するとき

1. 会話全文を貼らず、事実・決定・疑問・次の行動だけを抽出する。
2. `knowledge/inbox/YYYY-MM-DD-<topic>.md`を作成または更新する。
3. 確定事項は`knowledge/decisions/`へ昇格する。
4. 現在地が変わった場合だけ`knowledge/current-status.md`を更新する。
5. Beadsが利用可能ならタスクを作成・更新し、依存関係を設定する。
6. Beadsが利用できない場合だけ`TASKS_FALLBACK.md`を更新する。

## Basic Memoryノート形式

```markdown
---
title: Note title
type: note
tags: [gd, evaluation]
permalink: stable-permalink
---

# Note title

## Observations
- [decision] ...
- [fact] ...
- [question] ...
- [todo] ...

## Relations
- relates_to [[Other Note]]
- depends_on [[Another Note]]
```

## タスク管理

- 作業開始前に`bd ready --json`を確認する。
- タスクには完了条件を書く。
- 大きな作業は親子タスクへ分ける。
- 依存関係をBeadsに登録する。
- GitHub IssueとBeadsを同じ目的で二重管理しない。
- 完了した知見は必要に応じて`knowledge/`へ残す。

## 禁止事項

- 個人情報・生音声・未匿名化ログをコミットしない。
- 推測を確定事項として記録しない。
- 既存バージョンを上書きしない。
- 会話全文を大量に保存しない。
