# Standards mapping

_Interoperability boundaries for the Evolastra Observatory canonical model_

---

## 📋 Adoption policy

Standards are used where their semantics fit. The Observatory does not flatten its richer analytical graph into an external standard, and optional integrations never become prerequisites for local operation.

| Standard | Role | Core runtime dependency | Canonical persistence model |
| --- | --- | :---: | :---: |
| OpenTelemetry | Operational traces, logs, and metrics | No exporter required | Operational layer only |
| W3C Trace Context | Cross-boundary trace propagation | Yes at HTTP boundaries | Trace references only |
| CloudEvents | Durable semantic event envelope | Yes | Event log envelope |
| AsyncAPI | SSE and HTTP command contract | Documentation only | No |
| OpenLineage | Dataset lineage import/export subset | No | No |
| W3C PROV | Provenance export | No | No |
| AG-UI | Agent-to-frontend adapter | No | No |
| A2A | External agent adapter | No | No |
| MLflow | Experiment, model, and trace links | No | No |

## 📊 OpenTelemetry

OpenTelemetry describes operational execution signals, not the semantic analysis graph.[^1] Standard semantic conventions take precedence; project-only attributes use `galaxy.*`.

| Observatory concept | OpenTelemetry representation |
| --- | --- |
| Adapter, API, worker | Resource with service attributes |
| Analysis execution | Trace or trace group reference |
| Agent, model, tool, database operation | Span with appropriate kind and attributes |
| Retry or validation note | Span event when supported by the selected SDK version |
| Asynchronous causal relationship | Span link |
| Token, cost, latency, projection lag | Metrics with bounded dimensions |
| Structured diagnostic | Log record correlated to trace and span |

Semantic records retain trace and span IDs. They are not serialized as spans, and a technically successful span does not imply a validated claim.

## 🌐 W3C Trace Context

`traceparent` and `tracestate` propagate through HTTP ingestion, internal HTTP calls, SDK adapters, background work, and any future WebSocket connection setup.[^2] CloudEvent `traceid` and `spanid` extensions preserve the active context at event creation. They do not replace the W3C transport headers.

Only safe, bounded baggage is propagated. High-cardinality IDs may be used on spans and logs but not as metric dimensions. Sensitive content is redacted before propagation or export.

## 📦 CloudEvents and AsyncAPI

CloudEvents provides the structured envelope for every durable semantic event.[^3] The Observatory profile requires standard context fields plus `runid`, `sequence`, trace correlation, producer version, and privacy classification. The domain object lives in `data`; binary artifact bytes do not.

AsyncAPI documents the unidirectional SSE event feed, resumption rules, heartbeat behavior, and validated HTTP commands.[^4] OpenAPI remains authoritative for ordinary request-response REST resources. AsyncAPI is a contract artifact and introduces no message broker requirement.

## 🔗 OpenLineage

OpenLineage compatibility exports and imports the subset that describes data movement without discarding Observatory-only analytical meaning.[^5]

| Observatory concept | OpenLineage concept | Notes |
| --- | --- | --- |
| Transformation or data-producing node | Job | Stable namespace and name derived from adapter and operation |
| Transformation execution | Run | Linked to Observatory run and trace through custom facets |
| Dataset | Dataset identity | Maps namespace and logical name |
| DatasetVersion | Dataset plus version facet | Content hash and version ID use version or custom facets |
| Input/output version edge | InputDataset/OutputDataset | Direction follows transformation use and generation |
| Schema and documentation | Schema and documentation facets | Export only known, non-sensitive fields |
| Code artifact | Source code facet | Reference metadata, not embedded code by default |
| Quality summary | Data quality facets | Custom `galaxy_*` facet when no standard facet fits |

Claims, evidence, findings, approvals, layout, and camera state are not forced into OpenLineage. Custom facets are namespaced, optional, and ignored safely by generic consumers.

## 🔗 W3C PROV

The provenance exporter maps the semantic graph to PROV concepts without making PROV the internal object model.[^6]

| Observatory concept | PROV concept or relation |
| --- | --- |
| Artifact, dataset version, claim, finding | `prov:Entity` |
| Transformation or analysis operation | `prov:Activity` |
| Human, agent, adapter, software system | `prov:Agent` |
| Output produced by operation | `prov:wasGeneratedBy` |
| Operation consumed input | `prov:used` |
| Version or artifact derived from another | `prov:wasDerivedFrom` |
| Object owned or asserted by actor | `prov:wasAttributedTo` |
| Operation performed by actor | `prov:wasAssociatedWith` |

The preferred interchange form is JSON-LD. Exported identifiers are stable URIs derived from opaque Observatory IDs, and privacy policy may omit or summarize restricted content.

## 🔌 AG-UI

AG-UI is an optional adapter at the agent-to-frontend boundary, not the event store schema.[^7]

| AG-UI event family | Operational mapping | Semantic mapping |
| --- | --- | --- |
| Run lifecycle | Workflow or agent spans | Run lifecycle event |
| Step lifecycle | Task span | Node candidate or status event |
| Tool-call lifecycle | Tool span | ToolCall lifecycle event |
| Text message lifecycle | Message span or log | User-visible message metadata when allowed |
| State snapshot or delta | Adapter processing span | Namespaced shared-state update when supported |
| Custom event | Namespaced span or log | Persist only when a registered semantic mapping exists |

Unsupported fields survive in namespaced adapter metadata after redaction. The adapter never treats remote text as instructions and never bypasses semantic promotion rules.

## 🔌 A2A

A2A support is optional and modular.[^8] An external Agent Card can describe an integration capability; an A2A task can map to an external agent activity and a semantic node candidate; task status maps to explicit agent and node status events; returned artifacts map to artifact registrations after validation.

Internal subagents do not require A2A. A2A task IDs remain external references rather than replacing `agent_`, `node_`, or `run_` identifiers. Authentication and trust remain adapter concerns.

## 🔌 MLflow

MLflow integration is optional.[^9] When available, it may link:

- Analysis runs or experiments to MLflow runs
- Parameters and exact metrics to experiment metadata
- Dataset versions to dataset references
- Model artifacts to registered model or model-version references
- Evaluation results to claims, evidence, or artifacts without equating them
- OpenTelemetry-compatible agent traces to corresponding external trace views

External run and model references are metadata. The local event log, semantic graph, artifacts, replay, and core UI continue to work when MLflow is absent.

## 📌 Compatibility rules

- Adapters preserve source identifiers under a namespaced metadata key
- Import never trusts source text, paths, HTML, SVG, notebooks, or code
- Export applies privacy classification and redaction policy
- Missing optional fields remain absent rather than fabricated
- Unsupported event types remain durable and projection-safe
- Adapter versions are recorded independently from the core event schema
- Deduplication keys include source system and stable source identity

## 🔗 References

[^1]: OpenTelemetry. "OpenTelemetry Specification." https://opentelemetry.io/docs/specs/otel/

[^2]: W3C. (2021). "Trace Context, Level 1." https://www.w3.org/TR/trace-context/

[^3]: Cloud Native Computing Foundation. "CloudEvents Specification." https://github.com/cloudevents/spec

[^4]: AsyncAPI Initiative. "AsyncAPI Specification 3.1.0." https://www.asyncapi.com/docs/reference/specification/v3.1.0

[^5]: OpenLineage. "OpenLineage Specification." https://openlineage.io/docs/spec/

[^6]: W3C. (2013). "PROV-O: The PROV Ontology." https://www.w3.org/TR/prov-o/

[^7]: AG-UI. "AG-UI Documentation." https://docs.ag-ui.com/

[^8]: A2A Project. "A2A Protocol Specification." https://a2a-protocol.org/latest/specification/

[^9]: MLflow. "MLflow Documentation." https://mlflow.org/docs/latest/
