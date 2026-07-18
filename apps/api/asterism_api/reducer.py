from __future__ import annotations

from copy import deepcopy
from typing import Any

COLLECTIONS = {
    "node": "nodes",
    "agent": "agents",
    "tool_call": "tool_calls",
    "tool": "tool_calls",
    "dataset": "datasets",
    "dataset_version": "dataset_versions",
    "transformation": "transformations",
    "artifact": "artifacts",
    "claim": "claims",
    "evidence": "evidence",
    "finding": "findings",
    "decision": "decisions",
    "anomaly": "anomalies",
    "approval": "approvals",
    "annotation": "annotations",
    "metric": "metrics",
    "edge": "edges",
}

ENTITY_ALIASES = {
    # Older integrations and the Codex hook adapter use the compact CloudEvent
    # spelling while the canonical projection entity uses ``tool_call``.
    "toolcall": "tool_call",
}

SUPPORTED_ACTIONS = {
    "run": frozenset({"created", "started", "updated", "completed", "failed", "cancelled"}),
    "node": frozenset(
        {
            "proposed",
            "promoted",
            "created",
            "started",
            "progress",
            "completed",
            "failed",
            "cancelled",
        }
    ),
    "agent": frozenset(
        {"created", "assigned", "started", "status_changed", "handed_off", "completed", "failed"}
    ),
    "tool_call": frozenset({"requested", "started", "progress", "completed", "failed"}),
    "dataset": frozenset({"registered", "schema_updated"}),
    "dataset_version": frozenset({"created"}),
    "transformation": frozenset({"started", "completed", "failed"}),
    "artifact": frozenset({"created", "preview_created", "updated", "deleted"}),
    "claim": frozenset({"created", "updated", "validated", "disputed"}),
    "evidence": frozenset({"attached", "removed"}),
    "finding": frozenset({"created", "promoted", "updated"}),
    "decision": frozenset({"requested", "recorded"}),
    "approval": frozenset({"requested", "recorded"}),
    "anomaly": frozenset({"created", "resolved"}),
    "metric": frozenset({"recorded"}),
    "annotation": frozenset({"created"}),
    "snapshot": frozenset({"created"}),
    "edge": frozenset({"created"}),
}


def initial_state(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run": run,
        "nodes": {},
        "agents": {},
        "tool_calls": {},
        "datasets": {},
        "dataset_versions": {},
        "transformations": {},
        "artifacts": {},
        "claims": {},
        "evidence": {},
        "findings": {},
        "decisions": {},
        "anomalies": {},
        "approvals": {},
        "annotations": {},
        "metrics": [],
        "edges": {},
        "unknown_events": [],
        "last_sequence": 0,
        "event_count": 0,
    }


def _parse_type(event_type: str) -> tuple[str, str] | None:
    parts = event_type.split(".")
    if len(parts) != 5 or parts[0] != "galaxy" or parts[-1] != "v1":
        return None
    action = parts[-2]
    entity = ENTITY_ALIASES.get(parts[-3], parts[-3])
    if action not in SUPPORTED_ACTIONS.get(entity, frozenset()):
        return None
    return entity, action


def _entity_from_data(data: dict[str, Any], entity: str) -> dict[str, Any] | None:
    for key in (entity, entity.replace("_", ""), "entity"):
        candidate = data.get(key)
        if isinstance(candidate, dict):
            return deepcopy(candidate)
    if "id" in data:
        return deepcopy(data)
    return None


def reduce_event(state: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    # Copy-on-write keeps replay deterministic without copying the entire graph for every metric.
    next_state = state.copy()
    sequence = int(envelope.get("sequence") or 0)
    next_state["last_sequence"] = max(int(next_state.get("last_sequence", 0)), sequence)
    next_state["event_count"] = int(next_state.get("event_count", 0)) + 1
    parsed = _parse_type(str(envelope.get("type", "")))
    raw_data = envelope.get("data")
    data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    if parsed is None:
        next_state["unknown_events"] = [*next_state.get("unknown_events", []), envelope["id"]][
            -100:
        ]
        return next_state

    entity, action = parsed
    if entity == "run":
        patch: Any = data.get("run", data)
        if isinstance(patch, dict):
            run = {**next_state.get("run", {}), **patch, "_sequence": sequence}
            if action in {"started", "completed", "failed", "cancelled"}:
                run["status"] = "running" if action == "started" else action
            next_state["run"] = run
        return next_state

    collection_name = COLLECTIONS.get(entity)
    if collection_name is None:
        next_state["unknown_events"] = [*next_state.get("unknown_events", []), envelope["id"]][
            -100:
        ]
        return next_state

    item = _entity_from_data(data, entity)
    if entity == "metric":
        metric: dict[str, Any] = item if item is not None else deepcopy(data)
        metric.update({"_sequence": sequence, "event_id": envelope["id"]})
        # Durable fidelity remains in the event table; the UI projection intentionally coalesces.
        next_state["metrics"] = [*next_state.get("metrics", []), metric][-500:]
        return next_state

    if item is None:
        return next_state
    item_id = str(item.get("id") or data.get(f"{entity}_id") or "")
    if not item_id:
        return next_state
    collection = dict(next_state.get(collection_name, {}))
    current = dict(collection.get(item_id, {}))
    merged = {
        "schema_version": 1,
        **current,
        **item,
        "_sequence": sequence,
        "_event_id": envelope["id"],
    }
    status_actions = {
        "created": "created",
        "requested": "requested",
        "started": "running",
        "progress": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
        "validated": "validated",
        "disputed": "disputed",
        "promoted": "promoted",
        "resolved": "resolved",
        "recorded": str(item.get("status", "recorded")),
    }
    if action in status_actions:
        merged["status"] = status_actions[action]
    if action == "progress" and "progress" in data:
        merged["progress"] = data["progress"]
    collection[item_id] = merged
    next_state[collection_name] = collection

    if entity in {"node", "artifact", "claim", "finding", "dataset"} and action in {
        "created",
        "promoted",
        "registered",
    }:
        parent_id = merged.get("parent_node_id") or merged.get("node_id") or merged.get("parent_id")
        if parent_id and parent_id != item_id:
            edge_id = f"edge_{parent_id}_{item_id}"
            edges = dict(next_state.get("edges", {}))
            edges[edge_id] = {
                "id": edge_id,
                "source_id": parent_id,
                "target_id": item_id,
                "edge_type": "contains" if entity != "claim" else "produced",
                "_sequence": sequence,
            }
            next_state["edges"] = edges
    return next_state


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    for key, value in list(result.items()):
        if isinstance(value, dict) and key != "run":
            result[key] = list(value.values())
    return result
