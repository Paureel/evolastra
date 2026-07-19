# Security best-practices report

Reviewed: 2026-07-19
Frameworks: FastAPI/Pydantic/SQLAlchemy and React/Vite/TypeScript
Deployments rated: development loopback, Local Private, private tailnet federation, and static hosted viewer

## Executive summary

No critical issue was found under the verified profiles. Local Private requires bearer authorization, exchanges one-use codes for short-lived origin-bound sessions, handles private-network preflight only for exact origins, and keeps its root token out of Codex hook configuration and browser responses. The hosted deployment remains static-only and exposes one aggregate, read-only showcase. Optional multiplayer exposes only a federation path through Tailscale Serve and requires a separate scoped bearer; guest grants are memory-only and cannot authorize the ordinary companion API. Codex missions now separate trusted developer instructions from untrusted mission/reference context, run without command network or web search, inherit no ambient credentials, and cannot escalate approval. These controls reduce prompt-injection likelihood and blast radius; they do not make an LLM immune to adversarial input. Full npm and Python manifest audits report no known vulnerabilities.

## Critical findings

None for the stated profiles. Exposing the ordinary local Python API—or using a
public Funnel—would violate the product contract and remains explicitly
unsupported. The reviewed exception is the bounded federation route family for
known tailnet members.

## High findings and remediation status

### SEC-001 — Vulnerable multipart parser is reachable through JSONL import

- **Status:** Resolved and verified in the repository-local runtime.
- **Rule ID:** FASTAPI-SUPPLY-001 / FASTAPI-UPLOAD-001
- **Severity:** High
- **Location:** `requirements.txt:9`; `pyproject.toml:18`; `apps/api/asterism_api/api.py:196-218`
- **Evidence:** Both manifests and the repository-local virtual environment use `python-multipart==0.0.31`. A fresh full `pip-audit -r requirements.txt` reports no known vulnerabilities.
- **Impact:** A hostile local webpage or adapter can force expensive multipart parsing before handler-level `read(max_request_bytes + 1)` executes, degrading or denying the single API worker.
- **Fix:** Completed: the updated manifests were installed, `multipart.__version__` is `0.0.31`, and the complete test and dependency-audit gates pass.
- **Mitigation:** The new unsafe-origin gate and ASGI byte counter reduce browser and oversized-body exposure while deployment is refreshed.
- **False positive notes:** The reported arbitrary-write advisory requires non-default library options not used here. The multipart CPU advisories are reachable because FastAPI parses this upload route.

### SEC-002 — CORS does not authorize state-changing loopback requests

- **Status:** Resolved with bearer authorization plus browser-origin controls in Local Private.
- **Rule ID:** FASTAPI-CORS-001 plus local-service request-authority control
- **Severity:** High
- **Location:** `apps/api/asterism_api/main.py:80-101`
- **Evidence:** Unsafe methods now reject an `Origin` outside configured UI origins and reject `Sec-Fetch-Site: cross-site` before routing. Fresh tests exercise both variants and receive 403.
- **Impact:** A hostile webpage can attempt persistent work/import and availability attacks against a service running on the user's loopback interface.
- **Fix:** Completed. Protected routes require a constant-time validated bearer; browsers receive only short-lived origin-bound grants after a one-use exchange.
- **Mitigation:** Keep binding strictly on `127.0.0.1` and add rate limits for expensive routes.
- **False positive notes:** Browser Private Network Access can reduce reachability in some browsers, but it is not a portable authorization control. CSRF tokens are not otherwise required because no authentication cookie exists.
- **Regression evidence:** `test_unsafe_origin_cannot_trigger_state_change` passes.

### SEC-003 — Request-size middleware trusts an optional declared length

- **Status:** Resolved for actual ASGI request bytes.
- **Rule ID:** FASTAPI-LIMITS-001
- **Severity:** High
- **Location:** `apps/api/asterism_api/main.py:22-59`, `88`; `apps/api/asterism_api/api.py:196-218`
- **Evidence:** `RequestSizeLimitMiddleware` counts every `http.request` body frame and returns 413 above the configured limit before replaying the bounded body downstream. The route-level JSONL limit remains.
- **Impact:** A local producer can consume memory/CPU with oversized bodies and compound the cost through deep copies/projection work.
- **Fix:** Implemented. Add server/header time budgets and rate limits as defense in depth.
- **Mitigation:** Concurrency/rate limits and a smaller ingestion-specific ceiling.
- **False positive notes:** The middleware intentionally buffers up to the limit so it can replay the request; memory remains bounded by the configured maximum per concurrent request.
- **Regression evidence:** `test_streamed_body_without_content_length_is_limited` passes.

### SEC-004 — Known semantic events lacked registered payload validation

- **Status:** Resolved for every registered v1 entity/action family.
- **Rule ID:** FASTAPI-VALID-001
- **Severity:** High
- **Location:** `apps/api/asterism_api/event_store.py:128-140`, `235-271`; `apps/api/asterism_api/reducer.py:103-161`
- **Evidence:** Runtime validation dispatches through the reducer's complete `SUPPORTED_ACTIONS` registry. Every registered v1 event now requires an entity object, prefixed UUIDv4, schema version 1, and matching run relationship; core created-event fields receive additional checks. Malformed artifact and claim fixtures are both rejected.
- **Impact:** Before remediation, malicious or buggy producers could merge structurally malformed lineage/status/approval-shaped data and undermine provenance integrity.
- **Fix:** Completed for the reported structural gap. Continue with action-specific Pydantic/JSON-Schema models and referenced-entity existence checks as defense in depth.
- **Mitigation:** Quarantine relationship/ID anomalies and expose counts in health.
- **False positive notes:** The generic validator establishes a consistent structural floor; it is not a claim that every action-specific business invariant or cross-entity reference is already enforced.
- **Regression evidence:** `test_known_artifact_event_requires_artifact_schema` and `test_other_known_event_families_require_payload_schema` pass.

### SEC-005 — Run deletion leaves snapshots and quarantine payloads

- **Status:** Resolved for logical run-owned database rows; physical-copy policy remains.
- **Rule ID:** privacy deletion and data-lifecycle control
- **Severity:** High
- **Location:** `apps/api/asterism_api/api.py:119-129`; `apps/api/asterism_api/database.py:28-36`
- **Evidence:** The deletion transaction now removes events, snapshots, quarantine records, and the run. SQLite connections enable `PRAGMA secure_delete=ON`. Focused tests confirm run-owned snapshot/quarantine rows disappear and the pragma is active.
- **Impact:** Objectives, claims, artifact metadata, or missed secrets remain in SQLite after the user deletes a run. Orphaned records also frustrate retention and forensic expectations.
- **Fix:** Completed for current tables. Before claiming secure erasure, define WAL checkpoint/truncation, backup/export handling, future blob dereferencing, and a content-free audit tombstone.
- **Mitigation:** Describe this as logical database deletion, not recall of exports/backups.
- **False positive notes:** The audit row intentionally may survive, but it should contain opaque IDs and no run title/content.
- **Regression evidence:** `test_run_deletion_removes_all_sensitive_run_payloads` and `test_sqlite_secure_delete_is_enabled` pass.

### SEC-006 — Redaction implementations diverge and miss common secret shapes

- **Status:** Demonstrated camelCase miss resolved; cross-language convergence remains medium priority.
- **Rule ID:** data minimization / secret handling
- **Severity:** High
- **Location:** `apps/api/asterism_api/security.py:8-43`; `integrations/core.py:25-113`; `sdk/typescript/src/index.ts:28-47`; `apps/api/asterism_api/event_store.py:34-106`
- **Evidence:** API redaction now normalizes punctuation/case and explicitly covers `clientSecret` and `accessToken`. Python integration and TypeScript SDK still have different bounds, replacement strings, key sets, and token detectors. Locally created semantic run fields still bypass ordinary `ingest()` redaction.
- **Impact:** Credentials or sensitive raw content can persist into events, snapshots, SSE, quarantine, and exports; inconsistent producer behavior makes the guarantee untestable.
- **Fix:** Continue with the canonical policy: shared cross-language conformance corpus, equivalent bounds/truncation semantics, expanded high-confidence value detectors, and semantic-string scanning before local run persistence.
- **Mitigation:** Keep raw capture disabled and rotate any credential discovered in persisted data before cleanup.
- **False positive notes:** The specific camelCase regression is closed; no real credential was observed. Residual concern is policy drift and boundedness, not that the fixed examples still leak.
- **Regression evidence:** `test_redaction_covers_camel_case_secret_keys` passes.

### SEC-013 — Codex missions mixed trust levels and inherited ambient authority

- **Status:** Resolved with defense-in-depth controls; residual model risk remains.
- **Rule ID:** LLM authority separation / least privilege / secret handling
- **Severity:** High before remediation; Medium residual
- **Location:** `apps/api/asterism_api/shipyard.py`; `apps/api/asterism_api/codex_dispatch.py`; `apps/api/asterism_api/api.py`
- **Evidence:** Imported run and research-node titles/objectives previously shared one user message with role directives. The app-server child inherited the complete companion environment, while web search and per-turn command network policy were not explicitly disabled.
- **Impact:** Prompt-injected analytical metadata or repository content could influence repository edits or task output; inherited credentials and configurable network access could increase the consequences of a successful instruction override.
- **Fix:** Static safety and hull rules now use `thread/start.developerInstructions`; imported context is serialized, labeled as untrusted data, and kept at user authority. Every turn specifies workspace-write with `networkAccess: false`, web search is disabled, approval remains `never`, the child receives a non-secret environment allowlist, and client-visible startup errors are generic.
- **Mitigation:** Dispatch remains explicit, paired, loopback-only, and human-reviewed. Keep credentials and unrelated confidential material outside the workspace.
- **Residual risk:** No prompt hierarchy can guarantee that a model will ignore every adversarial instruction. Direct mission text and repository files remain readable, and Codex app-server is experimental.
- **Regression evidence:** Adversarial-context, environment-filtering, protocol-policy, and API-dispatch tests in `tests/test_shipyard.py` pass.

## Medium findings

### SEC-007 — Destructive/risky action audit coverage is incomplete

- **Rule ID:** audit and accountability
- **Severity:** Medium
- **Location:** `apps/api/asterism_api/api.py:97-105`, `123-130`, `207-215`, `256-307`; `apps/api/asterism_api/event_store.py:289-299`
- **Evidence:** Delete and projection rebuild call `audit`; quarantine retry, simulator speed, annotation command acceptance, and demo start do not. Retry deletes/commits the original quarantine record before re-ingestion.
- **Impact:** The operator cannot reconstruct all risk-relevant actions or a failed retry chain.
- **Fix:** Audit request, actor/source, redacted parameters, outcome, old/new IDs, and sequence for every destructive/risky action. Keep a tombstone rather than deleting retry provenance.
- **Mitigation:** Reconcile approvals/events/audits in a periodic integrity check.
- **False positive notes:** Approval decisions themselves are durable semantic events; the gap is uniform operational action audit and actor identity.

### SEC-008 — SSE and exports lack explicit resource budgets

- **Rule ID:** availability/resource control
- **Severity:** Medium
- **Location:** `apps/api/asterism_api/api.py:218-253`, `355-368`; `apps/api/asterism_api/exports.py:20-21`, `92-154`
- **Evidence:** SSE polls indefinitely per connection without a connection quota. Export loads all events and builds ZIP/JSON responses in memory.
- **Impact:** Multiple connections or large 100,000-event runs can increase DB sessions, heap, response latency, and event-loop/worker contention.
- **Fix:** Add per-run/client SSE quotas, cancellation/idle budgets, bounded queues, connection metrics, maximum export size, and streaming exports to temporary bounded files/iterators.
- **Mitigation:** Local process limits and one active UI stream per run.
- **False positive notes:** SSE fetches at most 250 rows per poll and sends heartbeats; event list pagination is capped.

### SEC-009 — Untrusted preview/export content needs stricter schemas and downstream labeling

- **Rule ID:** REACT-FILE-001 / output safety
- **Severity:** Medium
- **Location:** `apps/api/asterism_api/api.py:346-352`; `apps/web/src/components/ArtifactPreview.tsx:3-27`; `apps/api/asterism_api/exports.py:92-140`
- **Evidence:** React safely renders preview text/labels through JSX and `<pre>`, but the API does not validate preview shape/row/value bounds. Obsidian titles, objective, summary, and statement are emitted as Markdown/YAML without escaping.
- **Impact:** Malformed previews can crash/overload the UI, and exported content can create misleading or active links/markup in permissive downstream tools/plugins.
- **Fix:** Define a strict discriminated preview schema with bounded rows/text/numbers; safely quote YAML; generate unique normalized filenames; mark untrusted sections and neutralize unsupported active links/HTML.
- **Mitigation:** Continue never rendering HTML/SVG/notebook code inline.
- **False positive notes:** No browser XSS sink was found. The current React preview is inert; downstream behavior requires another application/user action.

### SEC-010 — Dependency and release gates are not reproducible

- **Status:** Partially resolved; npm lock/audit and root security scripts now pass, Python transitive locking/runtime convergence remain.
- **Rule ID:** FASTAPI-SUPPLY-001 / REACT-SUPPLY-001
- **Severity:** Medium
- **Location:** `requirements.lock`; `pyproject.toml`; `apps/web/package-lock.json`; `package.json:14-17`
- **Evidence:** Clean installs from `requirements.lock` with `--require-hashes` and `apps/web/package-lock.json` with `npm ci` both pass their test/build gates; both audits report zero known vulnerabilities. Source and asset scans pass.
- **Impact:** Builds drift, audit coverage is incomplete, and compromised/transitively changed packages may enter unnoticed.
- **Fix:** Retain both lockfiles and executable root gates; add an SBOM and provenance review for distribution releases.
- **Mitigation:** Exact direct pins reduce but do not remove drift.
- **False positive notes:** The asset-specific manifest/verifier exists and currently passes with zero assets.

### SEC-011 — Static frontend security headers are not established for production hosting

- **Status:** Resolved for the checked-in Netlify deployment profile.
- **Rule ID:** REACT-HEADERS-001 / REACT-CSP-001
- **Severity:** Medium before remediation
- **Location:** `netlify.toml`; `apps/web/index.html`; `apps/api/asterism_api/main.py`
- **Evidence:** Netlify now sends header-delivered CSP with `frame-ancestors 'none'`, Trusted Types, nosniff, strict referrer and permissions policies, HSTS, COOP, and CORP. `index.html` is no-store. The local API mirrors applicable isolation and content controls.
- **Impact:** A future static deployment can omit clickjacking, nosniff, referrer, permissions, and header-delivered CSP protections.
- **Fix:** Completed for Netlify; retain the meta CSP as an early fallback and keep deployment-header regressions in the release gate.
- **Mitigation:** Any non-Netlify host must reproduce and verify the same headers.
- **Regression evidence:** `tests/test_static_viewer_privacy.py` and `tests/security/test_security_controls.py` assert the deployment and API policies.

## Low findings

### SEC-012 — Runtime envelope policy drifts from the durable JSON schema

- **Rule ID:** FASTAPI-VALID-001
- **Severity:** Low independently; overlaps SEC-004
- **Location:** `apps/api/asterism_api/schemas.py:36-85`; `schemas/events/durable-event-envelope.v1.schema.json:6-105`
- **Evidence:** Pydantic allows unknown top-level fields and accepts all-zero trace/span IDs, while the durable schema forbids extra properties and all-zero identifiers.
- **Impact:** Contract drift permits ambiguous stored envelopes and makes test/runtime behavior inconsistent.
- **Fix:** Align Pydantic with the accepted durable schema (`extra="forbid"`, zero-ID rejection, matching bounds/URI rules) or document/version any deliberate difference.
- **Mitigation:** Downstream code currently reads an explicit field set.
- **False positive notes:** Unknown **event types** must remain accepted and ignored by projection; that requirement does not require accepting unknown envelope fields.

## Verified controls

- FastAPI `debug=False`; docs/OpenAPI disabled in production (`main.py:69-77`).
- Trusted Host and explicit CORS origins; credentials disabled and methods/headers restricted (`main.py:80-87`).
- Unsafe browser-origin state changes are rejected using exact Origin allowlisting and Fetch Metadata (`main.py:91-101`).
- Actual ASGI request bytes are counted and capped before downstream parsing (`main.py:22-59`).
- API responses set nosniff, frame denial, no-referrer, Permissions Policy, and deny-by-default CSP (`main.py:91-117`).
- Netlify responses add header-delivered CSP, HSTS, COOP/CORP, frame denial, Trusted Types, and no-store HTML caching (`netlify.toml`).
- Pydantic write models reject extra fields for run/command/approval requests (`schemas.py:18-34`, `88-105`).
- ORM/parameterized queries are used; no string-built SQL, shell execution, dynamic template rendering, server-side arbitrary URL fetch, or redirect sink was found.
- JSONL import ignores the supplied filename, reads a configured maximum plus one byte, and never exposes an upload directory (`api.py:196-218`).
- Registered `run.created`, `node.created`, and `artifact.created` payloads enforce IDs, schema version, required fields, and run-ID consistency (`event_store.py:235-271`).
- Run deletion removes event/snapshot/quarantine/run rows and SQLite connections enable secure-delete (`api.py:119-129`; `database.py:28-36`).
- React uses normal JSX escaping; no `dangerouslySetInnerHTML`, `innerHTML`, document-write, iframe/object/embed preview, `eval`, Web Storage token, service worker, or third-party script was found.
- Artifact preview explicitly renders structured bars or text/JSON and executes no artifact content (`ArtifactPreview.tsx:3-27`).
- Vite production source maps are disabled (`apps/web/vite.config.ts:4-9`).
- Asset verification is fail-closed and currently covers an empty third-party inventory.
- Codex dispatch keeps trusted rules at developer authority and imported context at user authority; every turn is offline, approval-free, workspace-scoped, and launched with a filtered non-secret environment (`shipyard.py`; `codex_dispatch.py`).
- The standard MIT license and its warranty/liability disclaimer are checked by `tests/test_license.py`; responsible-use guidance does not add a non-open-source use restriction.

## Recommended integration order

1. Strengthen registered payload validation with action-specific field bounds and referenced-entity existence checks.
2. Unify redaction bounds/detectors and add cross-language conformance tests.
3. Define WAL/backup/export/blob behavior before making a secure-erasure claim.
4. Add SSE/export budgets and complete audit coverage.
5. Harden preview/export schemas and preserve deployment-header tests on every supported host.

## Review evidence

Commands executed:

```powershell
rg --files -I
rg --with-filename -n -I "<security sink patterns>" apps integrations sdk tests
npm run check
npm run verify
```

The practical release gate passed on 2026-07-19: **130 Python tests**, **45 frontend unit/component tests**, and **7 Playwright browser/accessibility flows** passed. Ruff, strict Python and TypeScript checks, the production build, harness, source scan, asset verification, and disposable database migrations passed. The full locked-requirements audit reports **no known vulnerabilities** and npm audit reports **0 vulnerabilities**. The repository-local environment imports `python-multipart 0.0.31`.
