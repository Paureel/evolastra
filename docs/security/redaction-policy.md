# Redaction policy

Status: normative target plus current implementation gap analysis
Reviewed: 2026-07-17

## Policy objective

Prevent secrets and default-denied raw operational content from crossing a persistence, log, spool, quarantine, SSE, or export boundary while retaining the bounded semantic summaries required for provenance. Redaction is irreversible replacement, not encryption or authorization.

## Mandatory ordering

1. Apply size/depth/item bounds while constructing a JSON-safe copy.
2. Normalize and classify every key.
3. Redact secret-shaped keys unconditionally.
4. Redact default-denied content keys unless explicit capture is enabled.
5. Scan every retained string for secret-shaped values, including semantic fields and exception text.
6. Validate the already-redacted payload against envelope/entity schemas.
7. Persist, quarantine, log, spool, stream, or export only the resulting safe copy.

Never include raw rejected values in validation errors or logs. Capture opt-in may permit content fields but must never permit secrets.

## Canonical bounds

Use one shared conformance specification across API Python, integration Python, and TypeScript SDK implementations:

| Limit | Target |
|---|---:|
| Maximum recursion depth | 8 |
| Maximum entries per mapping/sequence | 100, with an explicit truncated-count marker |
| Maximum key length | 256 Unicode code points |
| Maximum retained string length | 4,096 Unicode code points unless a named semantic schema sets a lower bound |
| Maximum request bytes | 5 MiB by default, counted from ASGI receive bytes rather than trusted header alone |
| Maximum event batch | 1,000 events plus request-byte and processing-budget limits |

Truncation metadata contains only counts/lengths, never prefixes or suffixes of denied content.

## Key normalization and classes

For classification only, normalize Unicode to NFKC, split camelCase/acronyms, lowercase, and treat `_`, `-`, `.`, whitespace, and brackets as separators. Preserve a bounded original key in the stored safe structure.

Always-secret tokens include at least:

- `authorization`, `cookie`, `set-cookie`, `password`, `passwd`, `credential`;
- `api key`, `client secret`, `private key`, `access token`, `refresh token`, `session token`, `id token`;
- database/password-bearing connection strings and signing/encryption key material.

Default-denied raw-content tokens include at least:

- `prompt`, `completion`, `transcript`, `message content`;
- `tool input`, `tool output`, `request body`, `response body`;
- raw source/file content, notebook cells, stdout/stderr, and model input/output.

Semantic fields such as objective, title, claim statement, finding summary, and artifact description may be retained because they are product data, but they remain string-scanned and schema-bounded. An `error` or `exception` field is semantic only after stack traces, environment details, paths, and secret values are minimized.

## Value detectors

The detector corpus should cover, without recording the matched secret:

- bearer/basic authorization values and JWT-shaped tokens;
- common provider prefixes such as OpenAI, GitHub, Slack, cloud access keys, and package-registry tokens;
- PEM private keys and high-confidence key blocks;
- URI userinfo in database/service URLs;
- assignment/header forms such as `clientSecret=`, `X-Api-Key:`, and `Authorization:`;
- known canary tokens used only in tests.

Pattern matching is defense in depth, not the primary control. Key-based denial and source minimization remain required. High-entropy matching should be narrowly tuned to avoid destroying legitimate hashes/IDs.

## Current implementation mapping

| Implementation | Existing strengths | Gaps |
|---|---|---|
| API `asterism_api.security.redact` | Recursive mapping/list traversal; normalized secret-key matching now covers `clientSecret`/`accessToken`; selected secret values; content capture off by default; 100k string ceiling | No depth/item/key bound; narrow exact content-key set and value detectors; tuple/list only; behavior differs from SDKs (`apps/api/asterism_api/security.py:7-56`) |
| Python integrations `integrations.core.redact` | Depth 8, 100 items, 4,096 strings, bounded keys, default-deny content, secret removal remains active during capture | Key normalization remains separator-oriented; detector set is narrow; semantic errors/exception strings can retain sensitive details (`integrations/core.py:25-113`) |
| TypeScript SDK `redact` | Depth/item/string bounds and content denial | No truncation-count marker for arrays/maps; fewer value detectors; divergent replacement strings and key semantics (`sdk/typescript/src/index.ts:28-47`) |

Ordinary API ingestion calls redaction before envelope validation (`event_store.py:102-109`). Locally created runs call `_ingest_validated` directly and store `title`/`objective` without the ordinary redaction pass (`event_store.py:33-100`); semantic fields still need secret-value scanning.

## Quarantine and errors

- Quarantine the redacted/bounded payload, never the original bytes.
- Store a stable reason code plus bounded human summary. Do not embed entire Pydantic error `input` values.
- The quarantine-list endpoint should return metadata only; payload retrieval, if added, requires an explicit local-operator action and audit.
- Retry must retain a content-free tombstone linking old quarantine ID, new event/quarantine ID, actor, and outcome.

## Capture opt-in

Raw capture requires an explicit configuration change, visible runtime indicator, reason/owner, and retention period. It must not be switchable by an untrusted event. A capture-enabled run should be labeled and exports should warn that raw content may be present.

## Testing requirements

- Maintain one language-neutral fixture corpus of nested structures, Unicode/confusable keys, camelCase/separator variants, every supported secret format, large maps/lists, deep recursion, and content capture on/off.
- Assert byte-for-byte equivalent redaction semantics across API Python, integration Python, and TypeScript SDK.
- Include only synthetic canary values; never place real credentials in fixtures.
- Assert redaction occurs before persistence, quarantine, audit, spool, SSE, JSONL, snapshot, and every export.
- Add a post-persistence scan test proving canaries are absent from SQLite and exported archives.
- Treat a new missed-secret fixture as a security regression.

The focused security suite now verifies camelCase API-key coverage with `tests/security/test_security_controls.py::test_redaction_covers_camel_case_secret_keys`. Cross-language equivalence and bounded API traversal remain unverified.

## Operational response

If a secret is discovered after persistence:

1. revoke/rotate it first;
2. stop affected streams/exports and disable raw capture;
3. identify event, snapshot, quarantine, audit, export, spool, backup, and artifact copies without re-logging the value;
4. purge using the documented deletion/SQLite/WAL process;
5. add a synthetic detector fixture and regression test;
6. record the incident with identifiers and scope, never the secret itself.
