# Final verification

Executed 2026-07-18 on Windows with Python 3.12, Node.js 20, and npm 10.

## Practical release gate

`.venv\Scripts\python.exe scripts\verify.py` passed:

- Ruff and strict mypy
- 92 Python domain, API, contract, integration, security, quality, property, and chaos tests
- Alembic migration
- TypeScript typecheck and 25 Vitest tests
- Production Vite build: 251.66 kB JavaScript / 80.60 kB gzip; 41.97 kB CSS / 10.01 kB gzip
- Three Playwright scenarios covering live views, search, replay, stellar identity, and an axe serious/critical scan
- Asset manifest and focused source-security scans
- npm audit and Python locked-requirements audit: no known vulnerabilities

## 3D map and graph verification

- Deterministic tests verify stable `z` coordinates and yaw/pitch perspective projection.
- Breadth-first traversal verifies that claimed systems, all 200 generated frontier systems, and their bridges form one connected component.
- The frontier minimum-spanning tree and local-neighbor lanes were visually inspected at 1728 x 960.
- Direct browser drags changed yaw and tilt in both Galaxy and System views.
- Browser verification reported zero console errors.

## Publication boundary

- Local databases, pairing state, virtual environments, caches, test output, exports, and the private CNA working dataset are excluded by `.gitignore`.
- Only two curated browser captures are retained as repository documentation assets.
- All relative Markdown links resolve.
- No intended repository file exceeds 50 MB.
- Secret-pattern review found only deliberate redaction-test fixtures and no real credentials.

## Remaining boundaries

Unverified production boundaries remain recorded in the [gap matrix](gap-matrix.md): PostgreSQL and external infrastructure, live third-party collector integrations, full manual assistive-technology review, 6k/20k browser rendering, crash injection, and long-soak operation.
