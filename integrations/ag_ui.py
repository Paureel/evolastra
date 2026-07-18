"""AG-UI event adapter; AG-UI remains an edge protocol, not persistence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .core import build_event, entity_payload, stable_prefixed_id

_TYPES = {
    "RUN_STARTED": "galaxy.analysis.run.started.v1",
    "RUN_FINISHED": "galaxy.analysis.run.completed.v1",
    "RUN_ERROR": "galaxy.analysis.run.failed.v1",
    "STEP_STARTED": "galaxy.analysis.node.started.v1",
    "STEP_FINISHED": "galaxy.analysis.node.completed.v1",
    "TOOL_CALL_START": "galaxy.analysis.toolcall.started.v1",
    "TOOL_CALL_END": "galaxy.analysis.toolcall.completed.v1",
    "STATE_SNAPSHOT": "galaxy.integration.ag_ui_state.snapshotted.v1",
    "STATE_DELTA": "galaxy.integration.ag_ui_state.updated.v1",
    "MESSAGES_SNAPSHOT": "galaxy.integration.ag_ui_messages.snapshotted.v1",
}


def map_event(event: Mapping[str, Any], *, capture_content: bool = False) -> dict[str, Any]:
    event_name = str(event.get("type") or "UNKNOWN").upper()
    native_id = str(
        event.get("id") or json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
    )
    declared_run_id = str(event.get("runId") or "")
    run_native_id = declared_run_id or str(event.get("threadId") or native_id)
    run_id = stable_prefixed_id("run", "ag-ui-run", run_native_id)
    tool_call_id = str(event.get("toolCallId") or "")
    step_name = str(event.get("stepName") or "")
    if tool_call_id:
        subject = stable_prefixed_id("tool", "ag-ui-tool", tool_call_id)
    elif step_name:
        subject = stable_prefixed_id("node", "ag-ui-step", f"{run_native_id}:{step_name}")
    else:
        subject = run_id
    event_type = _TYPES.get(event_name, "galaxy.integration.ag_ui_event.received.v1")
    data: dict[str, Any] = {
        "ag_ui_type": event_name,
        "native": dict(event),
        "unsupported_fields_preserved_in": "data.native",
    }
    if event_type.startswith("galaxy.analysis.run.") and declared_run_id:
        data.update(
            entity_payload(
                "run",
                entity_id=run_id,
                run_id=run_id,
                status=event_type.split(".")[3],
            )
        )
    elif event_type.startswith("galaxy.analysis.node.") and declared_run_id and step_name:
        data.update(
            entity_payload(
                "node",
                entity_id=subject,
                run_id=run_id,
                status=event_type.split(".")[3],
                title=step_name,
            )
        )
    elif event_type.startswith("galaxy.analysis.toolcall.") and declared_run_id and tool_call_id:
        data.update(
            entity_payload(
                "tool_call",
                entity_id=subject,
                run_id=run_id,
                status=event_type.split(".")[3],
                tool_name=event.get("toolCallName"),
            )
        )
    elif event_type.startswith("galaxy.analysis."):
        event_type = "galaxy.integration.ag_ui_event.received.v1"
        data["mapping_limitation"] = "semantic event lacked documented run/entity identity"
    return build_event(
        event_type=event_type,
        source="urn:asterism:integration:ag-ui",
        subject=subject,
        run_id=run_id,
        adapter="ag-ui/0.1.0",
        native_id=native_id,
        correlation_id=str(event.get("threadId") or run_native_id),
        causation_id=str(event.get("parentRunId") or ""),
        capture_content=capture_content,
        data=data,
    )
