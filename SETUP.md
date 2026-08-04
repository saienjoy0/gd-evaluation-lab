# Setup

## 1. Basic Memory

Basic Memoryは`knowledge/`をMarkdown知識ベースとして索引化します。

### 前提

- Python用の`uv` / `uvx`が利用できること

### 登録

リポジトリのルートで実行します。

```bash
uvx basic-memory project add gd-evaluation-lab ./knowledge
uvx basic-memory status
```

Codex CLIで使う場合は、ユーザー設定へMCPを登録します。

```toml
[mcp_servers.basic-memory]
command = "uvx"
args = ["basic-memory", "mcp"]
```

Basic MemoryがなくてもMarkdown自体はそのままGitで利用できます。

## 2. Beads

Beadsはタスクと依存関係を管理します。

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/steveyegge/beads/main/install.ps1 | iex
bd init
```

### macOS / Linux

```bash
curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
bd init
```

Codex CLIを使う環境では必要に応じて実行します。

```bash
bd setup codex
```

初期化後は以下で次に着手可能なタスクを確認します。

```bash
bd ready --json
```

## 3. 初期タスクの移行

`TASKS_FALLBACK.md`の項目をBeadsへ登録し、登録完了後に同ファイルを「移行済み」に更新します。

## 4. 知識ノート検査

```bash
python scripts/check_knowledge.py
```
