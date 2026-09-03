$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$Python = Join-Path $RepoRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { $Python = (Get-Command python).Source }
Push-Location $RepoRoot
try {
    & $Python (Join-Path $ScriptDir 'run_rag_smoke.py') @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
