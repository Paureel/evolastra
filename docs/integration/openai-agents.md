# OpenAI Agents SDK tracing

`integrations.openai_agents.AsterismTracingProcessor` is import-safe when `openai-agents` is not installed. With the optional SDK installed, register an instance as an additional trace processor and pass it a quick local sink. Registration as an additional processor preserves the SDK's default exporter; replacing all processors changes that behavior.

```python
from agents import add_trace_processor
from integrations.jsonl import JsonlWriter
from integrations.openai_agents import AsterismTracingProcessor

writer = JsonlWriter("./agents-events.jsonl")
add_trace_processor(AsterismTracingProcessor(writer.write))
```

Mapping:

| Agents SDK span type | Asterism mapping |
|---|---|
| task | semantic node candidate |
| agent | agent activity |
| generation | operational model span |
| function | tool call |
| handoff | agent handoff |
| guardrail | operational validation span |
| custom/unknown | namespaced operational span |

The processor consumes the public synchronous callbacks `on_trace_start`, `on_trace_end`, `on_span_start`, `on_span_end`, `shutdown`, and `force_flush`. It uses public IDs, timestamps, `span_data.type`, and `span_data.export()`. Input/output fields from exported span data are default-deny content. Sink failures are swallowed so telemetry cannot change the agent result.

For overlap with another integration, pass `deduplication_key=lambda trace_id, span_id, phase: ...` to the processor. The callback receives only public native IDs and lifecycle phase; its result is hashed before persistence. Use the same material in the other adapter only when both sources expose a genuinely shared identity.

Sources: official [Agents SDK tracing guide](https://openai.github.io/openai-agents-python/tracing/), [processor interface](https://openai.github.io/openai-agents-python/ref/tracing/processor_interface/), and [span data reference](https://openai.github.io/openai-agents-python/ref/tracing/span_data/).

Limitation: this processor does not reconstruct a semantic task from private reasoning, and it does not deduplicate against hooks unless both paths retain their shared native identity. Configure one primary source per activity where cross-adapter identity is unavailable.
