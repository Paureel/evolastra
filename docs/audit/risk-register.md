# Risk register

| ID | Risk | Likelihood | Impact | Mitigation / evidence required |
| --- | --- | --- | --- | --- |
| R-001 | The specification is far larger than a normal single release and encourages false-completion claims. | High | High | Vertical slice first; gap matrix and final verified-limitations section; never relabel a missing integration as complete. |
| R-002 | High-rate telemetry overwhelms React or the browser. | High | High | Durable ingestion separated from animation, coalesced metrics, external scene state, stress fixture. |
| R-003 | Event duplication or reordering corrupts projections. | High | High | Unique event IDs, server sequence allocation, deterministic reducer, quarantine, property tests. |
| R-004 | Imported artifacts or telemetry leak secrets or execute active content. | High | High | Redaction before persistence, size/MIME allowlists, opaque IDs, sandboxed previews, no code execution. |
| R-005 | SQLite behavior diverges from the PostgreSQL production target. | Medium | High | SQLAlchemy-portable schema, transaction tests, documented local-only constraints, PostgreSQL CI profile when available. |
| R-006 | Current Codex/OpenAI event surfaces are overclaimed or reverse engineered. | Medium | High | Use official documentation, version adapters separately, preserve unknown fields, mark unavailable surfaces honestly. |
| R-007 | Renderer spectacle harms evidence navigation and accessibility. | Medium | High | 2D-first benchmark, synchronized text tree, keyboard/search alternatives, reduced motion, semantic zoom. |
| R-008 | Third-party visual assets create licensing or originality risk. | Medium | High | Prefer original procedural assets, manifest every shipped external asset, checksum verification, originality review. |
| R-009 | Live transport disconnects lose or duplicate UI state. | Medium | High | Sequence cursor, `Last-Event-ID`, idempotent client projection, reconnect and catch-up tests. |
| R-010 | Unbounded data preview or search creates resource exhaustion. | Medium | High | Hard file, row, query-time, pagination, and response limits; cancellation where supported. |
| R-011 | Local single-user assumptions are mistaken for production authorization. | High | High | State scope clearly, keep production authentication behind an explicit dependency boundary, do not claim multi-tenancy. |
| R-012 | Node 20.10 is below the requirement of newer build tooling. | Medium | Medium | Pin a compatible Vite release and verify all commands on the installed runtime. |
