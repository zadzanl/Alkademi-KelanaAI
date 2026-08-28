# run_ai_smoke.ps1
#
# Manual smoke test for both AI recommendation providers (no HTTP server).
# Each provider receives six requests: Japan and Norway at Backpacker,
# Standard, and Luxury budget levels. Results are combined per provider.
#
# Auth: each Python subprocess loads the repo-root .env. No secret is printed.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$OutputDir = Join-Path $ScriptDir "outputs"
$Python = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"

function Invoke-AiSmoke {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("OpenRouter", "Bedrock")]
        [string]$Provider
    )

    $OutputFile = Join-Path $OutputDir ("ai-smoke-{0}-output.md" -f $Provider.ToLowerInvariant())
    Write-Output "=== $Provider ==="

    # Provider selection remains production-shaped. For the Bedrock smoke we
    # remove OpenRouter only inside the child process so normal precedence picks
    # Bedrock. The child validates the requested provider's complete config
    # before calling it, preventing a mislabeled fallback result.
    & $Python -c @"
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(r'$RepoRoot') / '.env')
provider = '$Provider'
if provider == 'OpenRouter':
    required = ('OPENROUTER_API_KEY', 'OPENROUTER_MODEL')
else:
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('OPENROUTER_MODEL', None)
    required = ('AWS_REGION', 'MODEL_ID')

missing = [name for name in required if not os.environ.get(name, '').strip()]
if missing:
    raise SystemExit(f'{provider} smoke skipped: missing or empty ' + ', '.join(missing))

from backend.services.ai_service import get_ai_recommendation
from backend.services.trip_service import (
    get_recommended_transportation,
    get_trip_category,
)

destinations = (
    {
        'destination': 'Tokyo',
        'country': 'Japan',
        'days': 5,
        'travel_month': 'December',
        'travel_season': 'Peak Season',
        'recommended_places': ['Tokyo Tower', 'Shibuya', 'Mount Fuji'],
    },
    {
        'destination': 'Oslo',
        'country': 'Norway',
        'days': 7,
        'travel_month': 'June',
        'travel_season': 'Holiday Season',
        'recommended_places': ['Oslo Opera House', 'Vigeland Park', 'Oslofjord'],
    },
)
budgets = (
    (750.0, 'Backpacker'),
    (1500.0, 'Standard'),
    (5000.0, 'Luxury'),
)

sections = []
durations = []
total_chars = 0
total_words = 0
for destination in destinations:
    for budget, expected_category in budgets:
        category = get_trip_category(budget)
        if category != expected_category:
            raise SystemExit(
                f'category setup error: {budget} produced {category}, expected {expected_category}'
            )

        start_time = time.perf_counter()
        result = get_ai_recommendation(
            destination=destination['destination'],
            country=destination['country'],
            days=destination['days'],
            budget=budget,
            currency='USD',
            travel_month=destination['travel_month'],
            category=category,
            recommended_places=destination['recommended_places'],
            recommended_transportation=get_recommended_transportation(category),
            travel_season=destination['travel_season'],
        )
        elapsed = time.perf_counter() - start_time
        durations.append(elapsed)

        if not isinstance(result, str) or not result.strip():
            raise SystemExit(
                f'{provider} smoke failed: {destination["country"]} {category} returned no non-empty text ({elapsed:.2f}s)'
            )

        result = result.strip()
        total_chars += len(result)
        total_words += len(result.split())
        sections.append(
            f'# {destination["country"]} — {category}\n\n'
            f'<!-- budget_usd={budget:.2f} days={destination["days"]} duration_sec={elapsed:.2f} -->\n\n'
            f'{result}'
        )
        print(
            f'PASS {len(sections)}/6: {destination["country"]} {category} '
            f'({len(result)} characters, {elapsed:.2f}s)'
        )

total_duration = sum(durations)
avg_duration = total_duration / len(durations) if durations else 0.0

output = (
    '<!--\nprovider=' + provider + '\nrequests=6\n'
    'countries=Japan,Norway\ncategories=Backpacker,Standard,Luxury\n'
    'len_chars=' + str(total_chars) +
    '\ntokens_est_words=' + str(round(total_words / 0.75)) +
    '\ntokens_est_chars4=' + str(total_chars // 4) +
    f'\ntotal_duration_sec={total_duration:.2f}' +
    f'\navg_duration_sec={avg_duration:.2f}' +
    '\n-->\n\n' + '\n\n---\n\n'.join(sections) + '\n'
)
Path(r'$OutputFile').write_text(output, encoding='utf-8')
print(
    f'PASS: {provider} completed all 6 requests '
    f'({total_chars} total characters | total time: {total_duration:.2f}s | avg time: {avg_duration:.2f}s)'
)
print(r'Output: $OutputFile')
"@

    if ($LASTEXITCODE -ne 0) {
        throw "$Provider smoke failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $Python)) {
    throw "Canonical virtual environment Python not found: $Python"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Push-Location $RepoRoot
try {
    Invoke-AiSmoke -Provider "OpenRouter"
    # Invoke-AiSmoke -Provider "Bedrock"
}
finally {
    Pop-Location
}
