# Operational telemetry model

_OpenTelemetry-compatible execution facts and their boundary with semantic events_

---

## 📋 Purpose

Operational telemetry answers what software components did, when they did it, and whether the work succeeded. It uses OpenTelemetry concepts for traces, spans, logs, and metrics while the semantic graph separately answers what the analysis means.[^1]

Telemetry may be more detailed than the semantic graph. A run can contain thousands of spans without creating thousands of semantic nodes. Promotion is explicit, and a promoted semantic record retains trace and span references so users can move from analytical meaning to execution detail.

## 🌐 Trace context

HTTP clients, adapters, background workers, and SDK integrations propagate W3C `traceparent` and `tracestate` headers.[^2] A trace ID is 32 lowercase hexadecimal characters and a span ID is 16 lowercase hexadecimal characters; all-zero identifiers are invalid.

The CloudEvent extensions `traceid` and `spanid` carry the active operation context without replacing transport propagation. A consumer starts or links a local span from the received trace context, preserving causality even when work crosses a queue or process boundary.

`baggage` is restricted to safe, low-cardinality propagation values. Prompts, user text, filenames, artifact content, credentials, tenant secrets, and other unbounded content never belong in baggage.

## ⚙️ Span model

| Operation | Recommended span kind | Required linkage | Semantic promotion default |
| --- | --- | --- | --- |
| HTTP ingestion | `SERVER` | Run ID when known | Never |
| Adapter delivery | `PRODUCER` or `CLIENT` | Event and correlation IDs | Never |
| Agent activity | `INTERNAL` | Agent and node IDs | Candidate when objective is distinct |
| Model request | `CLIENT` | Agent, node, provider | Aggregated under node |
| Tool execution | `INTERNAL` or `CLIENT` | Tool call, agent, node | Normally aggregated |
| Database query | `CLIENT` | Service and operation | Never |
| Artifact write | `INTERNAL` | Artifact and node IDs | Artifact is semantic; span is not |
| Projection apply | `INTERNAL` | Event ID and sequence | Never |
| Approval wait | `INTERNAL` | Approval and agent IDs | Approval is semantic |

Span status records protocol or operation success, not the truth of an analytical claim. A statistically unsupported conclusion can be produced by a technically successful span; its semantic validation status remains separate.

## 📚 Attribute conventions

Stable OpenTelemetry semantic conventions take precedence when they accurately describe the signal. Project-specific attributes use the `galaxy.*` namespace and do not redefine standard fields.

| Attribute | Signal use | Cardinality |
| --- | --- | --- |
| `galaxy.analysis.run.id` | Trace, span, log | Bounded by runs |
| `galaxy.analysis.node.id` | Span, log | Bounded by nodes |
| `galaxy.agent.id` | Span, log | Bounded by agents |
| `galaxy.tool_call.id` | Span, log | High; avoid metric labels |
| `galaxy.artifact.id` | Span, log | High; avoid metric labels |
| `galaxy.claim.id` | Span, log | High; avoid metric labels |
| `galaxy.event.id` | Span, log | Unique; never a metric label |
| `galaxy.event.sequence` | Span, log | Numeric; never a metric label |
| `galaxy.privacy.class` | All signals | Low |
| `galaxy.adapter.name` | All signals | Low |
| `galaxy.adapter.version` | Resource, span | Low |

Resource attributes describe the emitting service, including standard service name and version attributes. They do not duplicate per-run fields.

## 📊 Metrics and logs

Metrics aggregate operational behavior. Token, cost, runtime, projection lag, event throughput, quarantine count, reconnect count, and rendering duration use bounded dimensions. IDs, prompts, tool input, and other unique values are excluded from metric labels.

Logs are structured and correlate through trace and span IDs. Log bodies contain summaries, never captured sensitive payloads by default. Exception records include type and a redacted message; stack traces are restricted to trusted diagnostics.

High-rate metric samples may be preserved as durable semantic events when exact replay is required. The visualization projection coalesces them to a configured update cadence rather than reflecting each sample into React.

## 🔐 Capture and sampling

Redaction precedes telemetry export. Prompt and completion capture, tool arguments, tool output, dataset samples, and artifact previews are separately configurable and default to disabled for content-shaped fields. Secret detection is applied before any exporter or local log sink sees the data.

Sampling affects operational signals only. It must not discard durable semantic events, approvals, evidence, or artifact metadata. External collectors and commercial backends are optional; the core application remains functional when OTLP export is disabled.

## 🔗 References

[^1]: OpenTelemetry. "OpenTelemetry Specification." https://opentelemetry.io/docs/specs/otel/

[^2]: W3C. (2021). "Trace Context, Level 1." https://www.w3.org/TR/trace-context/
