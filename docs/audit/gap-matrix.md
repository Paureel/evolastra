# Final gap matrix

Audited 2026-07-17 against the original empty workspace and the implemented local-first system. “Partial” means a working subset is present but a requested backend, scale target, or live external integration remains unverified.

| Requirement area | Final status | Evidence / remaining boundary |
| --- | --- | --- |
| Existing implementation audit | Complete, verified | The empty-workspace audit is preserved in `existing-implementation-audit.md`. |
| Three-layer architecture | Complete, verified | Telemetry, semantic projection, and disposable visualization are separated. |
| OpenTelemetry and trace context | Partial | Trace fields, conventions, collector config, and mapping fixtures exist; no external collector was exercised. |
| CloudEvents durable protocol | Complete, verified | Strict envelope, sequencing, idempotency, quarantine, import, and JSONL are tested. |
| AsyncAPI and OpenAPI | Complete | Maintained AsyncAPI plus runtime FastAPI OpenAPI. |
| AG-UI and A2A compatibility | Partial | Metadata-preserving fixture adapters exist; no live remote agent was connected. |
| OpenLineage, W3C PROV, MLflow | Partial | OpenLineage and PROV exports are tested; MLflow remains optional/deferred. |
| Codex hooks, SDK, and App Server | Partial | Documented fixture adapters and buffering paths exist; no live Codex session was captured. |
| OpenAI Agents tracing | Partial | Supported processor mappings and tests exist; no live external trace was captured. |
| Python, TypeScript, HTTP, JSONL, OTLP SDK paths | Partial | Python and TypeScript SDKs, HTTP, and JSONL are verified; OTLP is mapping/config only. |
| Semantic promotion | Complete, verified | Promotion reasons and low-level call grouping are represented and tested. |
| Canonical domain entities | Complete, verified | Registered v1 entity/action families enforce canonical identity payloads. |
| Append-only event store | Complete, verified | Atomic SQLite persistence/projection, unique IDs, per-run sequences, corrections, and snapshots. |
| Streaming and resume | Complete, verified | SSE cursor resume, catch-up, heartbeat, UI batching, and reconnect behavior are covered. |
| Persistence and migrations | Partial | SQLite, Alembic, snapshots, quarantine, and rebuild are verified; PostgreSQL/S3 are targets only. |
| Galaxy metaphor and deterministic layout | Complete, verified | Seeded systems, planets, agents, hyperlanes, anomalies, findings, and worker layout. |
| Renderer benchmark and ADR | Partial | Canvas ADR and deterministic reducer benchmark exist; cross-renderer browser benchmark is documented, not fully executed. |
| Rendering performance architecture | Partial | Scene isolation, culling/LOD, worker layout, and fallback exist; 6k/20k browser targets are not certified. |
| Main UX and synchronized views | Complete, verified | Galaxy, tree, findings, timeline, agents, artifacts, datasets, metrics, telemetry, and comparison views. |
| Artifact and bounded data workspace | Partial | Safe bounded previews and provenance exist; DuckDB-Wasm, Parquet/Arrow, notebooks, and PDF rendering are deferred. |
| Claims, evidence, contradictions, findings | Complete, verified | Traceable epistemic entities and explicit validation states are included in the demo and projection. |
| Replay and snapshots | Complete, verified | Deterministic seek and return-live behavior are unit- and browser-tested. |
| Search | Partial | Typed search and focus are implemented; dedicated upstream/downstream traversal actions are deferred. |
| Obsidian export | Complete, verified | Safe paths, manifest, stable links, collision resistance, and attachments are tested. |
| Original visual system | Complete | Original procedural palette, typography, geometry, motion, icons, and chart treatment; no third-party assets. |
| Backend APIs and health | Complete, verified | Versioned run/entity/export/command routes and granular health checks. |
| Privacy and security | Complete for local profile | Redaction, limits, safe files, headers, origin gates, approval boundary, threat model, and clean audits; internet/multi-user deployment is unsupported. |
| Accessibility | Substantially verified | Keyboard/text alternatives, reduced motion, contrast control, and axe serious/critical scan pass; no formal full WCAG audit. |
| Performance targets | Partial | Reducer reaches 24,387 events/s at 100k events; browser scale and long-session memory targets remain unverified. |
| Demonstration run | Complete, verified | Reproducible 214 semantic-event churn investigation plus four durable snapshot events, with eight branches, failures, contradictions, approvals, and unexplored paths. |
| Multi-agent delivery discipline | Complete | Bounded architecture, integration, visualization/security, and reliability workstreams reported independently. |
| Unit, property, contract, API, frontend, visualization tests | Complete, verified | Python and Vitest suites cover deterministic, protocol, projection, export, and safety properties. |
| End-to-end, chaos, accessibility, performance tests | Partial | Browser, axe, chaos, and reducer benchmark gates pass; PostgreSQL concurrency, crash injection, and long soak testing remain. |
| Documentation set | Complete | Architecture, protocol, integration, security, operations, user, asset, ADR, benchmark, and audit documents are present. |
| Non-Docker local development | Complete, verified | Setup, migration, dev, demo, reset, seed, security, benchmark, verify, and build commands exist. |
| Final clean verification | Complete, verified | Repository-local release gate passes after dependency and replay-race remediation; see `final-verification.md`. |
