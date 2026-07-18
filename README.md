<div align="center">
  <img src="apps/web/public/evolastra-mark.svg" alt="Evolastra mark" width="92" />
  <h1>Evolastra Observatory</h1>
  <p><strong>A local-first mission control for agentic analysis, evidence, and provenance.</strong></p>
  <p>Watch an investigation become a navigable 3D galaxy without surrendering its data.</p>

  <p>
    <a href="https://github.com/paureel/evolastra/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/paureel/evolastra/actions/workflows/ci.yml/badge.svg" /></a>
    <a href="https://github.com/paureel/evolastra/stargazers"><img alt="Repository stars" src="docs/badges/stars.svg" /></a>
    <img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" />
    <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white" />
    <img alt="React 18" src="https://img.shields.io/badge/React-18-149ECA?logo=react&logoColor=white" />
    <img alt="Private by design" src="https://img.shields.io/badge/data-local--first-71E6E1?labelColor=071B26" />
  </p>
</div>

![Evolastra 3D galaxy map](output/playwright/galaxy-3d.png)

Evolastra receives durable analytical events, projects them into a semantic evidence graph, and renders that graph through two spatial lenses: a strategic Galaxy Map for the full investigation and an orbital System View for a single analytical branch. The visualization is disposable; the append-only event log and semantic model remain the source of truth.

## Why Evolastra

- **See the analysis happen.** Runs, branches, agents, tools, artifacts, findings, anomalies, and approvals become distinct inspectable objects.
- **Navigate in 3D.** Both maps support perspective depth, drag rotation, tilt, pan, zoom, and keyboard camera controls.
- **Never lose the trail.** Replay, deterministic projections, typed relationships, and portable exports preserve how a conclusion was reached.
- **Keep data local.** The companion, SQLite database, artifacts, Codex outbox, and access capability remain on the user’s machine.
- **Integrate without lock-in.** CloudEvents, W3C trace concepts, JSONL, OpenLineage exports, SDKs, and narrow adapters provide explicit boundaries.
- **Stay connected.** Claimed systems and the generated frontier are built as a single traversable hyperlane graph—no isolated islands.

## How it works

```mermaid
flowchart LR
    A[Agents and analysis tools] --> B[Validated CloudEvents]
    B --> C[(Append-only local event log)]
    C --> D[Deterministic semantic projection]
    D --> E[Resumable live stream]
    E --> F[3D Galaxy and System views]
    C --> G[Replay and portable exports]
```

The architecture deliberately separates three concerns:

| Layer | Owns | Never owns |
| --- | --- | --- |
| Operational telemetry | Traces, spans, logs, metrics | Analytical meaning |
| Semantic graph | Runs, evidence, lineage, findings, approvals | Camera or layout state |
| Visualization | Coordinates, animation, camera, visual aggregation | Canonical evidence |

Read the [architecture overview](docs/architecture/overview.md) and [shared contract](docs/architecture/shared-contract.md) for the complete model.

## Quick start

### Prerequisites

- Windows PowerShell 5.1 or newer
- Python 3.12
- Node.js 20 and npm 10

Docker is not required.

```powershell
git clone https://github.com/paureel/evolastra.git
Set-Location evolastra
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
npm run demo
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). The API and its OpenAPI UI are available locally at [http://127.0.0.1:8000](http://127.0.0.1:8000) and [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Use `npm run dev` for an empty observatory or `npm run seed` to load the demonstration immediately.

## Camera and map controls

| Input | Action |
| --- | --- |
| Drag | Rotate the 3D camera |
| Shift-drag or middle/right drag | Pan |
| Mouse wheel or `+` / `-` | Zoom |
| `W` / `S` | Tilt |
| `A` / `D` | Rotate |
| Arrow keys | Inspect the previous or next object |
| `Home` | Reset the camera |
| Double-click a claimed star | Enter its System View |

## Connect Evolastra to Codex

Install and start the Local Private companion once:

```powershell
& .\.venv\Scripts\evolastra.exe service install
& .\.venv\Scripts\evolastra.exe service start
```

Restart Codex, review the managed hooks through `/hooks`, and pair a browser tab with:

```powershell
& .\.venv\Scripts\evolastra.exe pair
```

The included [`evolastra` Codex skill](skills/evolastra/SKILL.md) can install, start, pair, and diagnose the companion. See [Codex hooks](docs/integration/codex-hooks.md) and [Local Private deployment](docs/deployment/local-private.md) for operational details.

## Privacy model

The hosted viewer is static presentation code. It contains no API, ingestion service, database, or analytical storage. Each browser pairs directly with a loopback companion using a one-use code and receives a short-lived, origin-bound grant. Redaction occurs before local persistence.

See the [privacy model](docs/security/privacy-model.md), [threat model](docs/security/threat-model.md), and [redaction policy](docs/security/redaction-policy.md).

## Integrations and exports

### Input surfaces

- HTTP: `POST /api/v1/events` and `POST /api/v1/events/batch`
- JSONL: `POST /api/v1/imports/jsonl`
- Live stream: `GET /api/v1/runs/{run_id}/events/stream?after=<sequence>`
- Python SDK: [`sdk/python/galaxy_sdk`](sdk/python/galaxy_sdk)
- Codex hook examples: [`examples/integrations/codex`](examples/integrations/codex)
- Narrow adapters: AG-UI, A2A, OpenAI Agents tracing, OTLP JSON, and OpenLineage

### Export formats

CloudEvents JSONL, OpenLineage JSON, W3C PROV JSON-LD, Obsidian notes, a non-executable reproduction ZIP, and portable `.evolastra` analyses.

The [integration matrix](docs/integration/README.md) distinguishes implemented, fixture-tested, interface-only, and deferred surfaces.

## Development

```powershell
npm run verify       # complete release gate
npm run benchmark    # deterministic reducer benchmark
npm run lint
npm run typecheck
npm test
npm run build
npm run security
```

Database helpers are `npm run migrate`, `npm run reset`, and `npm run seed`.

## Repository map

```text
apps/api/       FastAPI companion, event store, projection, exports
apps/web/       React/Vite observatory and Canvas renderer
integrations/   Protocol adapters and normalized event mappings
schemas/        Versioned CloudEvent and semantic event schemas
sdk/            Python and TypeScript client surfaces
skills/         Codex skill for operating Evolastra
tests/          Domain, contract, security, quality, property, chaos tests
docs/           Architecture, deployment, integration, security, user guides
```

Start with the [documentation index](docs/README.md), [contribution guide](CONTRIBUTING.md), and [testing strategy](docs/development/testing.md).

## Project status

Evolastra is an experimental, single-user, local-first observatory. SQLite is the verified persistence profile. The repository documents deferred production-scale components and verified support boundaries rather than presenting them as implemented. See the [gap matrix](docs/audit/gap-matrix.md) and [quality report](docs/audit/quality-report.md).

## License

This is a private repository. All rights are reserved; no license is granted unless the repository owner provides one separately.
