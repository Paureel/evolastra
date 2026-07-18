# Integration support matrix

All adapters emit the immutable envelope in `docs/architecture/shared-contract.md`. Sequence is intentionally omitted at ingestion so the server can allocate it. IDs are prefixed UUIDv4 values; idempotency comes from `data.integration.deduplication_key`, never a deterministic UUID. Redaction runs before any spool, JSONL, or network sink.

Pure mappers keep a bounded process-local native-ID registry. A host that needs the same canonical entity IDs after restart must persist that association or retain the first ingested IDs while deduplicating on the supplied key. The short-lived Codex hook path handles this explicitly with a private `.ids` directory inside its outbox.

| Surface | Status | Boundary |
|---|---|---|
| Codex lifecycle hooks | Documented surface; fixture/CLI tested | Public command-hook stdin; spool-first capture and separate HTTP flusher; not exercised by a live Codex session here |
| Codex app-server | Documented mapper; fixture-tested | Documented notifications only; no live server transport test; caller owns initialization and transport |
| Codex SDK | Documented narrow mapper; fixture-tested | Documented final response only; no live SDK run or invented tracing callbacks |
| OpenAI Agents SDK | Documented optional processor; fixture-tested | Public `TracingProcessor` callbacks/exported span data; optional package was not installed for this test run |
| Python SDK | Implemented and stdlib-tested | Context managers, decorator, HTTP/JSONL/list sinks |
| TypeScript SDK | Standalone source; strict compiler-checked | Typed envelope, canonical entity validation, redaction, and sink; no package manifest or published package |
| AG-UI | Documented event mapper; fixture-tested | Supported lifecycle/tool/state events; unsupported fields retained under `data.native` |
| A2A | Interface only | Maps caller-supplied Agent Card and Task dictionaries; no protocol client |
| OpenLineage | Documented subset mapper; fixture-tested | RunEvent and dataset identity import/export; caller pins export schema URL |
| OTLP | Narrow JSON mapping | OTLP/HTTP JSON trace/log objects only; no protobuf receiver |
| MLflow | Deferred | No dependency or verified implementation is shipped |

Official references are linked from the adapter-specific pages. Imported content is untrusted data, never executable input.
