---
title: Memory and Task Architecture Decision
type: decision
tags: [architecture, memory, tasks, basic-memory, beads]
permalink: memory-and-task-architecture-decision
date: 2026-08-04
status: accepted
---

# Memory and Task Architecture Decision

## Observations

- [decision] 過去の知識と未完了タスクを同じファイルで管理しない
- [decision] 長期知識はBasic Memory互換Markdownとして`knowledge/`へ保存する
- [decision] 未完了作業、優先度、依存関係、ブロッカーはBeadsで管理する
- [decision] ChatGPT会話全文ではなく、決定・事実・疑問・次の行動だけを保存する
- [decision] Claude-MemはChatGPT Webの直接記録には依存させず、将来Codex等で必要になった場合の任意レイヤーとする
- [reason] Markdownは人間が読め、Gitで履歴管理でき、Basic Memoryで意味検索と関係探索が可能
- [reason] Beadsはタスクの依存関係と着手可能作業を決定的に管理できる
- [risk] Beads未初期化期間にタスクが散逸する可能性がある
- [mitigation] 初期化までは`TASKS_FALLBACK.md`を一時利用する

## Relations

- governs [[GD Evaluation Lab Project Overview]]
- updates [[Current Status]]
- derived_from [[Initial Chat Capture]]
