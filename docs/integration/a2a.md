# A2A compatibility boundary

`integrations.a2a` provides a small `A2AReader` protocol plus pure Agent Card and Task dictionary mappers. It does not implement discovery, authentication, JSON-RPC, streaming, push notifications, task cancellation, or capability negotiation.

The task mapper recognizes the documented task identity/context and common task states, preserves the redacted native object, and creates a canonical `data.node` candidate. An Agent Card has no analysis-run identity, so it remains a namespaced discovery integration event rather than inventing a semantic `data.agent`. Internal subagents do not depend on A2A.

Use an independently maintained A2A client to obtain validated objects, then call `map_agent_card` or `map_task`. Imported messages, artifacts, URLs, and metadata remain untrusted data.

Source: official [A2A protocol specification](https://a2a-protocol.org/latest/specification/).
