[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot

try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python 3.12 or newer is required and was not found on PATH."
    }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "Node.js 20 with npm 10 or newer is required and npm was not found on PATH."
    }

    if (-not (Test-Path ".venv")) {
        Write-Host "[1/5] Creating Python virtual environment..." -ForegroundColor Cyan
        python -m venv .venv
    } else {
        Write-Host "[1/5] Reusing Python virtual environment..." -ForegroundColor Cyan
    }

    Write-Host "[2/5] Updating pip..." -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip

    Write-Host "[3/5] Installing locked Python dependencies..." -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m pip install --quiet --require-hashes -r requirements.lock

    Write-Host "[4/5] Installing Evolastra in editable mode..." -ForegroundColor Cyan
    & .\.venv\Scripts\python.exe -m pip install --quiet --no-build-isolation --no-deps -e .

    Write-Host "[5/5] Installing locked web dependencies and migrating local data..." -ForegroundColor Cyan
    npm --prefix apps/web ci --no-fund
    & .\.venv\Scripts\python.exe -m asterism_api.cli migrate

    Write-Host "Development setup complete." -ForegroundColor Green
} finally {
    Pop-Location
}
