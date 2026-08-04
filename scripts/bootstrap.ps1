$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "== Basic Memory =="
if (Get-Command uvx -ErrorAction SilentlyContinue) {
    uvx basic-memory project add gd-evaluation-lab (Join-Path $RepoRoot "knowledge")
    uvx basic-memory status
} else {
    Write-Warning "uvx がありません。先に uv をインストールしてください。Markdownはそのまま利用可能です。"
}

Write-Host "== Beads =="
if (-not (Get-Command bd -ErrorAction SilentlyContinue)) {
    irm https://raw.githubusercontent.com/steveyegge/beads/main/install.ps1 | iex
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path ".beads")) {
        bd init
    }
    bd ready --json
} finally {
    Pop-Location
}

Write-Host "初期化完了。TASKS_FALLBACK.mdの項目をBeadsへ移行してください。"
