# seed_conversations.ps1
#
# Script to seed realistic travel conversations for testing the AI assistant (/chat).
#
# Usage:
#   .\seed_conversations.ps1 -Username <username>
#   .\seed_conversations.ps1 -Username <username> -Clear

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Username,

    [Parameter(Mandatory = $false)]
    [switch]$Clear
)

$ErrorActionPreference = "Stop"

$Username = $Username.Trim()
if ([string]::IsNullOrWhiteSpace($Username)) {
    throw "Username cannot be empty or whitespace-only."
}

$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$PythonWin = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
$PythonNix = Join-Path $RepoRoot "backend\.venv\bin\python"
$Python = if (Test-Path $PythonWin) { $PythonWin } elseif (Test-Path $PythonNix) { $PythonNix } else { $PythonWin }
$SeedScript = Join-Path $ScriptDir "seed_conversations.py"

if (-not (Test-Path $Python)) {
    throw "Canonical virtual environment Python not found: $Python"
}

$PyArgs = @($SeedScript, $Username)
if ($Clear) {
    $PyArgs += "--clear"
}

Write-Output "Running conversation seed script for user: $Username"
& $Python @PyArgs

if ($LASTEXITCODE -ne 0) {
    throw "Conversation seed script failed with exit code $LASTEXITCODE"
}
