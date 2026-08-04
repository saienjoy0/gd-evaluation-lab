#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Basic Memory =="
if command -v uvx >/dev/null 2>&1; then
  uvx basic-memory project add gd-evaluation-lab "$repo_root/knowledge"
  uvx basic-memory status
else
  echo "uvx がありません。先に uv をインストールしてください。Markdownはそのまま利用可能です。"
fi

echo "== Beads =="
if ! command -v bd >/dev/null 2>&1; then
  curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
fi

cd "$repo_root"
if [ ! -d .beads ]; then
  bd init
fi
bd ready --json

echo "初期化完了。TASKS_FALLBACK.mdの項目をBeadsへ移行してください。"
