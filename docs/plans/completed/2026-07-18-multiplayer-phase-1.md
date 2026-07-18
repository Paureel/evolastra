# Plan: multiplayer Phase 1

_Host-authoritative collaboration without hosted project storage_

---

Status: completed
Owner: Codex
Last updated: 2026-07-18

## Outcome

Several researchers can join the same locally stored analysis, identify themselves
with distinct territory colors, claim systems, run their own local Codex ships, and
deliberately publish findings to a host-authoritative session. Netlify remains a
static viewer and single-player behavior remains the default.

## Context

The existing companion is loopback-only and the semantic event log is local and
append-only. Phase 1 adds a narrow collaboration overlay transported through
Tailscale Serve. It does not replicate prompts, datasets, artifacts, credentials,
or the complete private event stream.

## Scope

- Included: host and join flows, expiring invites, scoped member grants, presence,
  player colors, system claims, explicit finding publication, paused-host state,
  local persistence, map overlays, tests, migration, and operator guidance.
- Excluded: public internet rooms, chat, raw artifact transfer, concurrent document
  editing, automatic project replication, host migration, combat, and matchmaking.

## Steps

- [x] Define multiplayer trust, session, and compatibility contracts
- [x] Implement host-authoritative collaboration API and persistence
- [x] Add lobby, presence, territory rings, claims, and publication controls
- [x] Update architecture, privacy, security, deployment, and setup guidance
- [x] Pass focused and complete release verification

## Decisions and surprises

- Tailscale Serve proxies a narrow federation API while the companion itself keeps
  listening only on loopback.
- Peers must already have the matching portable analysis loaded; the invite carries
  only a non-secret project fingerprint, not project content.
- Multiplayer facts live in separate tables rather than entering canonical semantic
  events, so entering or leaving a session cannot change single-player replay.
- Published findings are bounded summaries selected by the player. Raw finding
  payloads and supporting artifacts stay local.
- Scoped guest grants are kept only in process memory. A companion restart pauses a
  guest session and requires a fresh join instead of persisting a reusable secret.

## Validation

- `npm run doctor`: ready for development, including GitHub CLI.
- `npm run check`: passed with ten harness checks, Ruff, mypy, 120 Python tests,
  TypeScript, and 32 Vitest tests.
- Isolated Alembic migration and production Vite build: passed.
- Playwright: six scenarios passed, including the multiplayer entry point and Axe
  accessibility scan with no serious or critical violations.
- Asset verification, focused source security scan, and `git diff --check`: passed.
- npm and Python locked-requirements audits reported no known vulnerabilities.
