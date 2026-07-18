# OpenTelemetry and OTLP

Operational telemetry should use native OpenTelemetry concepts and W3C trace context. Codex itself can export structured OTel logs when `[otel]` is configured at the user level; project config cannot set the `otel` key. Codex prompt text remains redacted unless `otel.log_user_prompt = true` is explicitly enabled. See the current [Codex configuration documentation](https://learn.chatgpt.com/docs/config-file/config-advanced#observability-and-telemetry).

`integrations.otlp` is a narrow mapping helper for already-decoded OTLP/HTTP JSON objects:

- `map_traces_json` reads `resourceSpans/scopeSpans/spans`.
- `map_logs_json` reads `resourceLogs/scopeLogs/logRecords`.
- Resource and native fields are preserved after redaction.

It is not an OTLP server, does not decode protobuf, does not negotiate compression, and does not claim full OpenTelemetry semantic-convention coverage. Use an OpenTelemetry Collector for production protocol handling and route to a bounded ingestion service. Unsupported top-level shapes raise `UnsupportedOtlpPayload` instead of being guessed.

Protocol references: official OpenTelemetry [OTLP specification](https://opentelemetry.io/docs/specs/otlp/) and [OTLP exporter specification](https://opentelemetry.io/docs/specs/otel/protocol/exporter/).
