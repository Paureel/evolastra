# Final verification

Executed 2026-07-19 on Windows with Python 3.12, Node.js 20, and npm 10.

## Practical release gate

`npm run verify` passed against a fresh isolated SQLite database:

- Ruff and strict mypy
- Ten repository harness checks covering navigation, links, accessible diagrams, architecture, privacy, Codex dispatch, multiplayer boundaries, and plan state
- 122 Python domain, API, contract, integration, security, quality, property, chaos, bootstrap, shipyard, multiplayer, simulation, and harness tests
- Alembic migration
- TypeScript typecheck and 37 Vitest tests
- Production Vite build: 282.37 kB JavaScript / 88.79 kB gzip; 72.59 kB CSS / 15.81 kB gzip
- Six Playwright scenarios covering live views, search, replay, stellar identity, ship construction, research hull unlocks, multiplayer entry, explicit map zoom, safe figures, and an axe serious/critical scan
- Asset manifest and focused source-security scans
- npm audit and Python locked-requirements audit: no known vulnerabilities

## Multiplayer Phase 1 verification

- Single player remains the default and its canonical event replay is byte-for-byte
  unchanged after hosting, joining, claiming, publishing, leaving, and reset flows.
- Host, invite, project-fingerprint, unique-color, claim, publication, departure,
  closed-session, restart, and run-deletion regressions pass.
- Guest member grants remain process-memory-only; the database and migration do not
  persist the raw grants, and the harness enforces that boundary.
- Federation routes require both a scoped bearer grant and Tailscale identity in the
  Local Private profile. Remote targets are restricted to HTTPS `.ts.net` roots and
  HTTP clients ignore ambient proxy settings.
- The static viewer exposes opt-in host/join controls, player-colored territory rings,
  a roster, claims, and explicit bounded finding publication. Netlify stores no room
  or project data.
- The browser release suite covers the federation entry point alongside the default
  single-player flow, with no serious or critical Axe violations.

## Safe figures and map zoom verification

- Structured numeric artifacts render as local scientific figures without executing
  artifact-provided HTML, JavaScript, SVG behavior, notebooks, or generated code.
- CNA-frequency rows use a zero-centered loss/gain display, redundant high-level
  event marks, and exact percentages; unsupported payloads show a textual empty state
  instead of an uninformative black panel.
- Both 3D maps expose a percentage slider, keyboard-operable minus/plus controls,
  wheel zoom, and reset behavior while retaining unrestricted camera rotation.
- Camera state is independent of streamed layout updates, so arriving analysis
  events animate ships and territory without resetting the operator's zoom or
  orientation. The exact zoom browser scenario passed three consecutive runs.
- Unit tests cover CNA rendering and the empty state. Playwright covers exact zoom,
  figure discovery, modal opening, and the figure dialog's accessibility surface.
- A local end-to-end check against the completed STAD CNA run found all six bounded
  analysis figures, opened the CNA plate at 185% map zoom, and reported no browser
  console errors.

## Replay frame-continuity verification

- Canvas backing-store dimensions are assigned only when the CSS viewport or
  device-pixel ratio actually changes. Replay/layout effect restarts preserve
  the last complete bitmap instead of clearing it to black.
- Deterministic tests cover unchanged and changed viewport sizes. A headed
  browser replay of the STAD run sampled 180 consecutive rendered frames across
  timestep changes and observed zero blank frames and zero application console
  errors.

## Three-empire STAD simulation verification

- The ignored private simulation result records three synthetic empires, six
  falsifiable hypothesis systems, six multiplayer hypothesis claims, one command
  capital claim, and six deliberately published bounded summaries.
- The Amplification Dominion explores MYC–ATR and CCNE1 replication stress; the
  Loss Cartographers explore CDKN2A checkpoint and ARID1A chromatin loss; the
  Constellation Pact explores ERBB2–CCNE1 and TERT–RICTOR combinations.
- Weighted semantic distance uses declared program, gene, cytoband, mechanism,
  therapeutic, alteration, and validation features. Coordinates are derived in
  the browser and never persisted in canonical event payloads.
- The frozen 600-iteration method failed its registered threshold (`rho=0.7366`).
  Root-cause investigation identified incomplete convergence; the documented
  exploratory 1,200-iteration product revision reproduced `rho=0.8455`, mean
  within-program distance `514.70` versus `797.02` between programs, and six of
  six program-local nearest neighbors. This is method validation, not biological
  confirmation.
- Live browser inspection at 1728 × 960 confirmed three colored influence
  corridors, the semantic-geography key, three online synthetic players, all six
  publications, and textual semantic details for one system per empire. The
  browser reported zero errors.

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
- A two-session regression verifies that simulator activity and interactive ship
  construction serialize against the latest committed event head instead of
  quarantining a valid build as a sequence conflict.
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
