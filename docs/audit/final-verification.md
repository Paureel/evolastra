# Final verification

Executed 2026-07-18 on Windows with Python 3.12, Node.js 20, and npm 10.

## Practical release gate

`.venv\Scripts\python.exe scripts\verify.py` passed:

- Ruff and strict mypy
- Nine repository harness checks covering navigation, links, accessible diagrams, architecture, privacy, Codex dispatch, and plan state
- 110 Python domain, API, contract, integration, security, quality, property, chaos, bootstrap, shipyard, and harness tests
- Alembic migration
- TypeScript typecheck and 27 Vitest tests
- Production Vite build: 259.43 kB JavaScript / 82.66 kB gzip; 52.12 kB CSS / 12.06 kB gzip
- Four Playwright scenarios covering live views, search, replay, stellar identity, ship construction, research hull unlocks, and an axe serious/critical scan
- Asset manifest and focused source-security scans
- npm audit and Python locked-requirements audit: no known vulnerabilities

## 3D map and graph verification

- Deterministic tests verify stable `z` coordinates, full 360° yaw/pitch perspective projection, angle wrapping, and return-to-origin after a complete turn.
- Breadth-first traversal verifies that claimed systems, all 200 generated frontier systems, and their bridges form one connected component.
- Radial-distribution checks verify that at least twelve unclaimed systems occupy the inner approach region while the frontier still reaches beyond 1,050 world units.
- The frontier minimum-spanning tree and local-neighbor lanes were visually inspected at 1728 x 960.
- Direct browser drags carried the Galaxy view from 33° to 181° tilt and the System view from 28° to 175°, both beyond the former 70° stop.
- Browser verification reported zero console errors.

## Two-way shipyard verification

- A Frigate, Mothership, and Colony ship are always available; completed tech-tree nodes deterministically add problem-specific specialist hulls.
- Browser verification opened the drydock from the command star, commissioned a core vessel, and opened an unlocked research hull from the tech tree.
- API tests verify pairing protection, durable ship lifecycle events, default-deny prompt capture, and the no-model-override / workspace-write / no-escalation app-server contract.
- A verification-only mission was launched through the installed signed-in Codex CLI over stdio. The turn completed successfully and persisted as a local Codex rollout without modifying the repository.
- The shipyard and tech tree have no Axe serious or critical accessibility violations.

## Publication boundary

- Local databases, pairing state, virtual environments, caches, test output, exports, and the private CNA working dataset are excluded by `.gitignore`.
- Only two curated browser captures are retained as repository documentation assets.
- All relative Markdown links resolve.
- Every supported Mermaid diagram exposes an accessibility title and description.
- No intended repository file exceeds 50 MB.
- Secret-pattern review found only deliberate redaction-test fixtures and no real credentials.

## Installation verification

- `npm run bootstrap:check` returned machine-readable prerequisite and repository-path data.
- `npm run doctor` confirmed supported tool versions, the repository-local Python environment, frontend dependencies, and optional GitHub CLI.
- Root development and release commands pin `.venv\Scripts\python.exe`; a regression test prevents fallback to an incompatible global Python.
- The complete bootstrap was executed idempotently with `-NoBrowser`; it installed locked dependencies, rebuilt the viewer, preserved all 10 managed hooks, restarted the Local Private companion, and reported `running: true`.
- A bootstrap regression test invokes the script from outside the checkout to verify location-independent path handling.
- Reinstallation tests verify that a moved checkout refreshes the configured static viewer path instead of retaining a retired location.
- PowerShell parser validation passed for `setup.ps1` and `bootstrap.ps1`; all repository-document links resolve.

## Remaining boundaries

Unverified production boundaries remain recorded in the [gap matrix](gap-matrix.md): PostgreSQL and external infrastructure, live third-party collector integrations, full manual assistive-technology review, 6k/20k browser rendering, crash injection, and long-soak operation.
