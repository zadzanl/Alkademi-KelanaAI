# seed_trips.ps1
#
# Script to inject 11 dummy trips into the database for a specific user to test pagination.
#
# Usage: .\seed_trips.ps1 -Username <username>

param(
    [Parameter(Mandatory = $true)]
    [string]$Username
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$Python = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
$SeedScript = Join-Path $ScriptDir "seed_trips.py"

if (-not (Test-Path $Python)) {
    throw "Canonical virtual environment Python not found: $Python"
}

Write-Output "Running seed script for user: $Username"
& $Python $SeedScript $Username

if ($LASTEXITCODE -ne 0) {
    throw "Seed script failed with exit code $LASTEXITCODE"
}
