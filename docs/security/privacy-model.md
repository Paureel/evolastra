# Privacy model

Reviewed: 2026-07-18
Applies to: Local Private companion and static hosted viewer

## Privacy posture

Evolastra is a local observability and provenance store, not an anonymous telemetry system. Even with raw content capture disabled, semantic fields such as objectives, node titles, claims, evidence summaries, dataset names, tool errors, and artifact descriptions are intentionally retained because they are the product. Operators must therefore assume a run can contain personal, confidential, regulated, or credential-adjacent information and choose an appropriate `privacyclass`.

The authoritative database, artifact directory, Codex outbox, exports, and root capability remain on the user's computer under `~/.evolastra`, `~/.codex`, and user-selected export locations. A Netlify/VPS-hosted interface is executable presentation code only and reads from the paired loopback companion. The centralized VPS storage profile and remote connector were removed.

`capture_content=false` is a collection-minimization control for raw prompts, completions, tool input/output, transcripts, and similarly shaped operational content. It is not a promise that a run contains no human-authored content or personal data (`apps/api/asterism_api/config.py:22-23`, `apps/api/asterism_api/security.py:18-43`, `integrations/core.py:55-113`).

## Data inventory

| Data class | Examples | Current collection/storage | Default handling |
|---|---|---|---|
| Semantic analysis content | Objectives, titles, claims, findings, evidence, descriptions | Event envelope, run projection, snapshots, exports | Collected; secret-value scanning should still apply |
| Operational raw content | Prompts, completions, tool input/output, transcripts | Event data/quarantine/spool | Default deny when recognized by redaction key |
| Telemetry metadata | IDs, timestamps, trace/span IDs, status, runtime, tokens, cost | Events, projection, SSE, exports | Collected |
| Dataset/artifact metadata | Names, schema summaries, filenames, hashes, preview values/text | Events/projection/preview/export | Collected; content itself is not currently stored by API |
| Approval/annotation data | Decision, note, actor label, requested action | Events/projection | Collected; actor is currently the fixed label `local-operator` |
| Quarantined input | Redacted invalid/out-of-order payload plus reason | SQLite quarantine table | Collected until manual reset/deletion; no automatic retention |
| Audit data | Action, target, fixed actor, redacted details | SQLite audit table | Minimal but incomplete action coverage |
| Configuration | Database URL, artifact root, allowed origins/hosts, capture flag | Environment/`.env` | Operator-controlled; `.env` should not be committed |
| Exports | Complete events, semantic summaries, lineage, Markdown, reproduction data | User-selected files outside application control | Portable copy; local deletion cannot recall it |
| Multiplayer overlay | Player display names/colors, presence, system IDs, and deliberately published finding summaries | Host companion SQLite; last host snapshot on guest companion | Opt-in; no raw prompts, datasets, artifacts, or full event stream |

The privacy labels `public`, `internal`, `confidential`, and `restricted` are validated on run/event envelopes (`apps/api/asterism_api/schemas.py:22-27`, `36-57`). They are descriptive metadata in the current profile; they do not trigger encryption, authorization, retention, or export restrictions.

## Processing flows

1. Adapters/SDKs should minimize and redact raw content before spooling or HTTP emission. The Python integration implementation bounds depth, item count, and string length (`integrations/core.py:55-113`).
2. The API redacts an ordinary event before envelope validation and persistence (`apps/api/asterism_api/event_store.py:102-109`). Invalid events are redacted again before quarantine (`event_store.py:273-291`).
3. Valid events are copied into the append-only event table, mutable semantic projection, and periodic full-state snapshots (`event_store.py:170-226`).
4. State and event data can leave the service through REST, SSE, search, preview metadata, and exports (`apps/api/asterism_api/api.py:132-176`, `268-303`, `360-430`).
5. The React client renders textual content through JSX or `<pre>` rather than HTML interpretation (`apps/web/src/components/ArtifactPreview.tsx:12-27`).
6. In multiplayer, a guest companion sends bounded collaboration operations to
   the host through an HTTPS `.ts.net` route. The Netlify viewer is not in this
   path. Invite secrets are user-carried; host stores only their digest, while
   guest member grants stay in process memory and disappear on restart.

## Existing controls

- Content capture defaults off (`config.py:22-23`).
- Secret-shaped keys, normalized camelCase variants, and selected secret values are redacted before ordinary event persistence (`security.py:7-56`).
- Integration redaction additionally bounds recursion, collection size, keys, and strings (`integrations/core.py:55-113`).
- Quarantine listing returns metadata/reasons but not raw payloads (`api.py:190-204`).
- The browser keeps only a short-lived, origin-bound pairing grant in that tab's `sessionStorage`. It is sent exclusively to the loopback companion, disappears when the tab session ends, and is never sent to the static host.
- Artifact preview does not execute HTML, SVG, notebooks, or code.
- Production mode disables interactive API docs (`main.py:28-36`).
- API responses use `no-referrer`, nosniff, frame denial, restricted Permissions Policy, and a deny-by-default API CSP (`main.py:91-117`).
- Unsafe cross-origin state changes and over-limit actual ASGI body bytes are rejected before routing (`main.py:22-59`, `91-108`).
- Federation calls require both a Tailscale Serve identity header and a scoped
  invite/member bearer. Those capabilities do not authorize ordinary run,
  event, export, pairing, or Codex routes.

## Retention and deletion

No time-based retention, automatic purge, per-privacy-class retention, or backup policy exists in repository code. `DELETE /api/v1/runs/{run_id}` now transactionally removes event, snapshot, run-scoped quarantine, and run rows (`api.py:119-129`). SQLite connections enable `PRAGMA secure_delete=ON` (`database.py:28-36`). Audit details can still retain the run title.

Logical deletion and secure-delete are verified by focused tests, but they do not guarantee recall/erasure from older WAL frames, filesystem snapshots, backups, exported ZIP/JSON files, or future content-addressed blobs. A defensible erasure policy should still:

1. retain the verified transactional deletion of run-owned rows and add future blob-reference cleanup;
2. keep only a content-free deletion tombstone containing opaque run ID, time, actor, and outcome;
3. garbage-collect a blob only after confirming no remaining reference;
4. define and test WAL checkpoint/truncation and `VACUUM` behavior appropriate to the retention promise;
5. document backup/export responsibility and allow the operator to locate portable copies;
6. verify zero orphaned rows/blobs after deletion.

The endpoint may be described as logical run deletion, not secure erasure or recall of copies.

## Data minimization rules

- Store semantic meaning, summaries, counts, hashes, and provenance rather than raw tool/prompt content by default.
- Never store credentials, authorization headers, cookies, session material, private keys, or database URLs with embedded credentials.
- Keep imported filenames as display metadata only; never use them as storage paths.
- Bound lists, maps, string lengths, preview rows, event batches, quarantine reasons, and export sizes.
- Preserve exact metrics only where necessary; avoid identifiers or dimensions that unnecessarily identify people.
- Require explicit operator opt-in for raw capture and surface a persistent UI/health warning while enabled.
- Raw-capture opt-in never disables secret redaction.

## Privacy-class expectations

| Class | Intended use | Minimum local-profile treatment | If future remote exposure is proposed |
|---|---|---|---|
| Public | Deliberately publishable synthetic/non-sensitive material | Normal retention; export allowed | Authenticated change control |
| Internal | Ordinary local project metadata | Default; content capture off | AuthN/authZ and encrypted transport/storage policy |
| Confidential | Proprietary analysis or personal data | Explicit retention; export warning; verified deletion | Object/tenant authorization, encryption, audit, retention enforcement |
| Restricted | Credentials must still never be stored; highly sensitive research/data | Avoid ingestion unless controls are validated; no raw capture | Separate hosted security review, least privilege, strong isolation and compliance controls |

## Privacy gaps and priorities

1. **Medium — redaction divergence:** the demonstrated API camelCase miss is fixed, but API, Python integration, and TypeScript SDK still use different bounds/value detectors.
2. **Medium — physical-copy lifecycle:** logical run-owned rows are deleted with secure-delete enabled, while WAL/backups/exports and future blobs still need an explicit erasure/retention policy.
3. **Medium — capture semantics are easy to misunderstand:** semantic objectives/claims remain captured when raw capture is disabled; product UI/docs should state this explicitly.
4. **Medium — no retention enforcement:** privacy class currently has no operational effect.
5. **Medium — exports replicate data without a manifest of sensitivity/retention:** reproduction and CloudEvents exports can contain the full redacted history.
6. **Low in local profile — no encryption at rest:** SQLite relies on OS account/filesystem protection. Encryption/key management becomes necessary if the deployment or device-risk assumptions change.

## Narrow remote collaboration exception

The static viewer may be internet-accessible, but the ordinary Python API remains
loopback-only. The sole supported remote exception is the Phase 1 federation
route family exposed to an operator-controlled tailnet with Tailscale Serve. It
accepts only presence, claims, and bounded publication summaries; it does not
provide remote ingestion, exports, pairing, Codex dispatch, project download, or
artifact access. Tailscale identity headers are a transport gate, not the only
authorization control: every request also needs a scoped capability.

Tailscale Funnel, public reverse proxies, shared server databases, and direct
non-loopback binding remain unsupported. Any broader exposure requires a new
architecture decision and privacy review. CORS is not an authorization control.
