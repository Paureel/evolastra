# Semantic analysis model

_Canonical analytical meaning projected from immutable domain events_

---

## 📋 Model boundary

The semantic graph records durable analytical meaning. It is independent of renderer metaphors: records use `run`, `node`, `artifact`, and `finding`, never star, planet, fleet, territory, position, or camera terminology.

Persisted IDs are UUIDv4 strings with readable prefixes such as `run_`, `node_`, `agent_`, `evt_`, and `art_`. Every persisted semantic record has an integer `schema_version`. API timestamps are UTC RFC 3339 strings and internal timestamps are timezone-aware.

Incoming events, persisted entities, API DTOs, and visualization records are distinct types. Sharing identifiers across those boundaries does not make the structures interchangeable.

## 🔗 Entity groups

| Group | Canonical entities | Purpose |
| --- | --- | --- |
| Execution context | AnalysisRun, AnalysisNode, Agent, ToolCall | Organizes objectives, delegation, and work status |
| Data lineage | Dataset, DatasetVersion, Transformation | Separates logical datasets from immutable versions and processing activities |
| Outputs | Artifact, ReproductionBundle | Records content-addressed outputs and reproducibility metadata |
| Knowledge | Claim, Evidence, Finding | Preserves assertions, support, contradiction, and promoted conclusions |
| Governance | Decision, Anomaly, HumanAnnotation, HumanApproval | Records interventions, risk, exceptions, and review |
| Graph and measures | GraphEdge, MetricSample | Adds typed cross-entity relationships and exact measurements |

`GraphEdge` supplements, rather than replaces, direct foreign-key relationships. An evidence record is itself a first-class relationship with method, strength, explanation, author, time, and validation state.

## ⚙️ Initial projection

The initial vertical slice projects the durable families accepted by the shared contract:

- Run created, started, updated, completed, and failed
- Node created, promoted, started, progressed, completed, and failed
- Agent created, started, status changed, handed off, completed, and failed
- Tool call requested, started, completed, and failed
- Dataset registered and dataset version created
- Artifact created and preview created
- Claim created, validated, and disputed
- Evidence attached
- Finding created and promoted
- Anomaly created and resolved
- Approval requested and recorded
- Metric recorded and snapshot created

SSE heartbeats are transport liveness messages rather than semantic records. They carry the run ID, latest sent sequence, and server time, and never create analytical entities.

The broader entity taxonomy is an extension target, not a claim that every lifecycle is projected in the initial slice. Unknown event types remain durable and are ignored until a compatible projector is installed.

## 🎯 Promotion rules

Low-level spans and tool calls do not automatically become analysis nodes. An operation is a promotion candidate when it has a distinct delegated objective, creates a durable artifact or claim, opens a significant branch, consumes substantial resources, requires investigation, has user-visible importance, is explicitly promoted, or matches a configured adapter rule.

Every promoted node records its `promotion_reason` and creation source. Manual promotion or demotion changes the semantic view without deleting its source telemetry. Repeated low-level work is grouped under the meaningful node.

## 📊 Claims, evidence, and findings

A claim is an analytical assertion. Confidence is optional and must carry a source and type such as model-reported, analyst-assigned, statistically estimated, user-assigned, or rule-derived. The absence of justified confidence is represented explicitly rather than replaced by a fabricated number.

Evidence links a claim to an artifact, dataset version, claim, node, or other supported target. Relationships include support, contradiction, qualification, reproduction, failed reproduction, derivation, reference, and assumption. A finding is a promoted, user-facing knowledge object assembled from one or more claims; promotion never erases contradictory evidence.

## 💾 Datasets and artifacts

A `Dataset` is a logical identity. A `DatasetVersion` is an immutable materialization with format, schema, statistics, quality summary, content hash, parents, privacy class, and sampling policy. Transformations link input versions, output versions, code, parameters, environment, seed, trace, and span.

An `Artifact` is a logical analytical object whose opaque ID is independent of its content hash. Artifact metadata may point to content, preview, and thumbnail storage references, but browser clients never receive filesystem paths. Large bytes never appear in CloudEvents.

## 🔄 Event application rules

Projectors apply events in ascending `sequence` within a run. Event IDs enforce idempotency. A detected sequence gap stops forward application for the affected run until catch-up restores the missing range or an operator resolves quarantine; it does not silently infer state.

Stored events are immutable. A correction is a later event that references the original through `causationid` or domain metadata. Upcasters transform supported older payloads in memory for projection without rewriting event history.

For a fixed ordered stream and run seed, projection output is deterministic. Snapshot restore followed by replay must equal a full rebuild at the same terminal sequence.
