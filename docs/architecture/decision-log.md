# Architecture decision log

## ADR-001 — New baseline is justified

Accepted. The audited workspace contained zero files and was not a Git repository. There is nothing to preserve or incrementally refactor.

## ADR-002 — FastAPI backend with a SQLite local profile

Accepted. FastAPI/Pydantic/SQLAlchemy follows the requested preferred stack. SQLite makes the required non-Docker workflow practical; PostgreSQL is the production target through the same models.

## ADR-003 — Server-Sent Events for durable browser delivery

Accepted provisionally. The durable feed is server-to-browser and benefits from native cursor semantics. Bidirectional commands do not require a permanently bidirectional socket and are expressed as validated HTTP commands. This decision can be revised only with benchmark or functional evidence.

## ADR-004 — React UI with rendering state outside React

Accepted. React owns accessible panels and interaction state. A Canvas scene store owns high-frequency rendering and receives coalesced projection updates so metric volume does not become React render volume.

## ADR-005 — Original procedural visual assets first

Accepted. Procedural stars, planets, probes, and territory marks avoid asset-license risk and prevent resemblance to a commercial game. External assets may be added only with a primary-source license record and checksum.

## ADR-006 — Local single-user security boundary

Accepted with limitation. Loopback local use is the verified first deployment profile. Production authentication, authorization, TLS, and multi-tenancy require deployment-specific configuration and are not implied by the demo.

## ADR-007 — Static-hosted UI with a local-private companion

Accepted. A CDN or Netlify may serve the disposable React bundle while authoritative events, projections, exports, and SQLite remain on the user's computer. The browser pairs to loopback using a one-use code. The companion returns a short-lived origin-bound bearer grant; it never exposes the root local capability. Authenticated live delivery uses fetch-based SSE parsing because native `EventSource` cannot attach the Authorization header.

## ADR-008 — Codex hooks spool locally; the companion drains

Accepted. Managed Codex hooks perform bounded redaction and atomic local writes only. The companion owns retry and API delivery, so hook latency and API outages cannot block Codex. Hook installation is additive and uninstall removes only Evolastra-managed commands.

## ADR-009 — Centralized Hosted Team profile rejected and removed

Superseded. Centralized VPS ingestion and persistence conflict with the product's local-data requirement. Public deployments contain static viewer assets only. Runtime endpoint validation and the deployment CSP limit API traffic to loopback companions; the supported Python service is local-private and rejects non-loopback clients in production.

## ADR-010 — Host-authoritative tailnet federation

Accepted for the Phase 1 multiplayer profile. One participant's Local Private
companion remains authoritative for a separate collaboration overlay containing
player identities, colors, presence, system claims, and explicitly published
finding summaries. Tailscale Serve exposes only `/api/v1/federation` to the
tailnet; invite and member capabilities are scoped to those routes and do not
authorize the ordinary companion API. The canonical event log, prompts, datasets,
artifacts, Codex credentials, and raw findings are not replicated. Guests must
load the same portable analysis locally, and host loss pauses the session.
