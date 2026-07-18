# Asset and dependency supply-chain policy

Reviewed: 2026-07-17

## Current status

- No raster, SVG, font, audio, texture, 3D, or other third-party visual asset is shipped. The asset manifest is complete and empty (`docs/assets/asset-manifest.json`; `docs/assets/THIRD_PARTY_ASSETS.md`).
- The procedural-first asset direction reduces license, malware, and franchise-imitation risk.
- The PowerShell asset verifier passes with zero discovered assets, and the Python security test independently checks manifest/discovery parity.
- Python direct and transitive dependencies are version- and hash-locked in `requirements.lock`; `pyproject.toml` remains the human-edited source manifest.
- The web package has a lockfile. A fresh `npm --prefix apps/web audit --audit-level=high --json` reports zero vulnerabilities (`apps/web/package.json`; `apps/web/package-lock.json`).
- Root security and asset verification scripts now exist and execute successfully (`scripts/security_scan.py`; `scripts/verify_assets.py`; `package.json:14-17`).

## Security findings from dependency evidence

After remediation, `python -m pip_audit -r requirements.lock` reports no known vulnerabilities. In particular:

- `python-multipart==0.0.31` resolves the reachable parser advisories.
- `pytest==9.0.3` resolves PYSEC-2026-1845.
- `FastAPI==0.139.2` with `Starlette==1.3.1` resolves the Starlette advisories surfaced by the clean transitive audit.

Verification runs in the repository-local `.venv`. A separate clean virtual environment was installed with `--require-hashes` from `requirements.lock`; `pip check` and all 75 Python tests passed there.

## Visual-asset admission gate

Every shipped visual file—first-party or third-party—must have an exact repository-relative path and SHA-256 in the manifest. Third-party records additionally require:

- exact title/creator and primary source page;
- direct download/evidence URL and retrieval date;
- exact license/rights expression and version;
- explicit commercial-use, modification, redistribution, and attribution decisions;
- untouched-source and shipped-derivative checksums;
- transformation steps, application locations, reviewer, and approval state;
- verbatim attribution in `THIRD_PARTY_ASSETS.md` when required.

Reject search-engine copies, fan art, extracted game assets, unclear generated provenance, unclear authorship, noncommercial/no-derivatives terms, and unapproved share-alike. SVG is active content: sanitize it, remove scripts/external references/event handlers, and do not inline untrusted SVG. 3D/model/texture formats must be parsed only by pinned offline tooling and never opened automatically by the runtime.

## Dependency gate

Before release:

1. Retain the committed npm lockfile and use `npm ci`, not `npm install`, in automation.
2. Regenerate `requirements.lock` with the recorded `uv pip compile` command whenever `pyproject.toml` changes, and install it with `--require-hashes`.
3. Retain the verified `python-multipart==0.0.31`, `pytest==9.0.3`, `FastAPI==0.139.2`, and `Starlette==1.3.1` minimums when producing the hash-locked dependency set.
4. Run npm and Python audits from locks, not from the developer's global environment.
5. Generate an SBOM for Python, npm, and bundled assets; preserve tool versions and audit output.
6. Review install/build scripts and avoid third-party install scripts where feasible; never run unreviewed asset conversion tools with elevated privileges.
7. Fail on lock drift, unapproved advisories, unmanifested visual files, checksum changes, remote runtime product assets, and missing attribution.

An advisory exception must record package/version, advisory, reachability analysis, compensating control, owner, expiry, and approval. “Local only” can reduce urgency but does not justify leaving a parser DoS reachable from the browser/local adapters indefinitely.

## Build provenance and release evidence

Record:

- clean checkout/commit and operating system;
- Python/Node/package-manager versions;
- lockfile and SBOM checksums;
- exact install commands and whether install scripts ran;
- full audit outputs and accepted exceptions;
- production bundle checksum and source-map publication policy;
- asset-verifier summary and attribution checksum.

The SPA production build already disables source maps (`apps/web/vite.config.ts:4-9`) and loads no remote third-party script from `index.html`. The meta CSP restricts resources to self/local development endpoints, but production should deliver equivalent CSP, `frame-ancestors`, nosniff, referrer, and permissions policy as HTTP headers because meta CSP cannot enforce all directives (`apps/web/index.html:4-6`).

## Verification commands

Current repository-local commands:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/assets/verify-assets.ps1
python -m pytest tests/security -q -rxX
python -m pip_audit -r requirements.lock
npm --prefix apps/web audit --audit-level=high --json
```

Expected current outcomes: asset verification and focused source scanning pass; all 15 security tests pass; both Python and npm audits report no known vulnerabilities.
