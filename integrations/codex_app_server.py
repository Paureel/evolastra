"""Pure mapping for documented Codex app-server notifications.

Transport ownership, initialization, approvals, and schema generation remain
with the caller. Generate schemas from the installed Codex version rather than
copying private or version-sensitive wire definitions into this adapter.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .core import build_event, entity_payload, stable_prefixed_id

_METHOD_TYPES = {
    "thread/started": "galaxy.analysis.run.created.v1",
    "turn/started": "galaxy.analysis.run.started.v1",
    "turn/completed": "galaxy.analysis.run.completed.v1",
    "item/started": "galaxy.analysis.node.started.v1",
    "item/completed": "galaxy.analysis.node.completed.v1",
}


def map_notification(
    message: Mapping[str, Any], *, capture_content: bool = False
) -> dict[str, Any]:
    if "id" in message:
        raise ValueError("app-server responses are not notifications")
    method = message.get("method")
    params = message.get("params", {})
    if not isinstance(method, str) or not isinstance(params, Mapping):
        raise ValueError("notification requires string method and object params")

    thread = params.get("thread") if isinstance(params.get("thread"), Mapping) else {}
    turn = params.get("turn") if isinstance(params.get("turn"), Mapping) else {}
    item = params.get("item") if isinstance(params.get("item"), Mapping) else {}
    thread_id = str(params.get("threadId") or thread.get("id") or "")
    turn_id = str(params.get("turnId") or turn.get("id") or "")
    item_id = str(params.get("itemId") or item.get("id") or "")
    native_id = json.dumps(message, sort_keys=True, separators=(",", ":"), default=str)
    run_native_id = turn_id or thread_id or native_id
    run_id = stable_prefixed_id("run", "codex-app-server", run_native_id)
    event_type = _METHOD_TYPES.get(method, "galaxy.integration.codex_notification.received.v1")
    subject = run_id
    data: dict[str, Any] = {"method": method, "params": dict(params)}
    if event_type.startswith("galaxy.analysis.run.") and (turn_id or thread_id):
        status = event_type.split(".")[3]
        data.update(entity_payload("run", entity_id=run_id, run_id=run_id, status=status))
    elif event_type.startswith("galaxy.analysis.node.") and item_id and (turn_id or thread_id):
        node_id = stable_prefixed_id("node", "codex-app-server-item", item_id)
        subject = node_id
        status = event_type.split(".")[3]
        data.update(entity_payload("node", entity_id=node_id, run_id=run_id, status=status))
    elif event_type.startswith("galaxy.analysis."):
        event_type = "galaxy.integration.codex_notification.received.v1"
        data["mapping_limitation"] = "notification lacked documented run/entity identity"
    return build_event(
        event_type=event_type,
        source="urn:asterism:integration:codex-app-server",
        subject=subject,
        run_id=run_id,
        adapter="codex-app-server-notifications/0.1.0",
        native_id=native_id,
        correlation_id=thread_id or run_native_id,
        causation_id=turn_id,
        capture_content=capture_content,
        data=data,
    )
