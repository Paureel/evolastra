# AG-UI

`integrations.ag_ui.map_event` translates supported AG-UI run, step, tool-call, and state lifecycle events into canonical envelopes. AG-UI is an edge protocol, not the persisted domain model.

Verified mappings include `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`, `STEP_STARTED`, `STEP_FINISHED`, `TOOL_CALL_START`, `TOOL_CALL_END`, `STATE_SNAPSHOT`, `STATE_DELTA`, and `MESSAGES_SNAPSHOT`. The adapter uses documented `threadId`, `runId`, `parentRunId`, `stepName`, and `toolCallId` fields when present. Semantic mappings carry canonical `data.run`, `data.node`, or `data.tool_call`. Events lacking the necessary documented identity are retained as `galaxy.integration.ag_ui_event.received.v1` instead of receiving fabricated semantic entities. Unsupported fields remain under `data.native` after redaction.

Message content, state snapshots, state deltas, tool arguments, and results are content-shaped and default-deny. This protects persistence but means a UI needing live text should use its normal ephemeral AG-UI channel rather than this durable event payload.

Source: official [AG-UI event documentation](https://docs.ag-ui.com/concepts/events).
