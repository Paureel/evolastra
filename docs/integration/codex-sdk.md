# Codex SDK and app-server

## SDK result adapter

`integrations.codex_sdk.map_run_result` consumes only caller-normalized, documented fields: a thread ID and the final response (`result.final_response` in the Python SDK or `result.finalResponse` in TypeScript). Final response content is redacted by default. The adapter does not inspect SDK internals or invent an event callback API.

The current public SDK guides document `Codex`, threads, `run()`, resume, and final responses, but do not establish a rich tracing-processor contract equivalent to the Agents SDK. Use hooks or app-server notifications for live activity. Source: current [Codex SDK documentation](https://learn.chatgpt.com/docs/codex-sdk).

## App-server notifications

`integrations.codex_app_server.map_notification` accepts a decoded app-server notification and maps documented lifecycle methods (`thread/started`, `turn/started`, `turn/completed`, `item/started`, and `item/completed`). Other notifications are persisted as unknown integration events, with content redacted.

The adapter is not a client. The caller must initialize the JSON-RPC-like connection, handle requests/responses and approvals, and generate schemas from its installed Codex version:

```powershell
codex app-server generate-json-schema --out ./schemas
```

The app-server supports JSONL-over-stdio by default. WebSocket transport is documented as experimental and unsupported; do not expose it on a shared network. Source: current [Codex app-server documentation](https://learn.chatgpt.com/docs/app-server).

Because generated schemas are version-specific, this repository does not vendor a guessed schema or reverse-engineer session transcripts.
