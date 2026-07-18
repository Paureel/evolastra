$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
& .\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
npm --prefix apps/web ci
& .\.venv\Scripts\python.exe -m asterism_api.cli migrate
Write-Host "Setup complete. Run: npm run demo"
