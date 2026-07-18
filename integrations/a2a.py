"""Optional A2A dictionary mapping boundary (not a transport implementation)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from .core import build_event, entity_payload, stable_prefixed_id


class A2AReader(Protocol):
    """Minimal host-supplied reader; concrete protocol clients stay optional."""

    def get_agent_card(self) -> Mapping[str, Any]: ...
    def get_task(self, task_id: str) -> Mapping[str, Any]: ...


def map_agent_card(card: Mapping[str, Any], *, run_key: str = "discovery") -> dict[str, Any]:
    name = card.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("A2A Agent Card requires a non-empty name")
    run_id = stable_prefixed_id("run", "a2a-discovery", run_key)
    native_card = json.dumps(card, sort_keys=True, separators=(",", ":"), default=str)
    return build_event(
        event_type="galaxy.integration.a2a_agent.discovered.v1",
        source="urn:asterism:integration:a2a",
        subject=run_id,
        run_id=run_id,
        adapter="a2a-interface/0.1.0",
        native_id=native_card,
        data={
            "a2a_object": "AgentCard",
            "native": dict(card),
            "mapping_limitation": "Agent Card has no analysis run identity",
        },
    )


def map_task(task: Mapping[str, Any], *, capture_content: bool = False) -> dict[str, Any]:
    if not isinstance(task.get("id"), str) or not str(task["id"]).strip():
        raise ValueError("A2A Task requires a non-empty id")
    task_id = str(task["id"])
    context_id = str(task.get("contextId") or task_id)
    run_id = stable_prefixed_id("run", "a2a-context", context_id)
    node_id = stable_prefixed_id("node", "a2a-task", task_id)
    status = task.get("status") if isinstance(task.get("status"), Mapping) else {}
    state = str(status.get("state") or "unknown").lower()
    event_type = {
        "submitted": "galaxy.analysis.node.created.v1",
        "working": "galaxy.analysis.node.started.v1",
        "completed": "galaxy.analysis.node.completed.v1",
        "failed": "galaxy.analysis.node.failed.v1",
        "canceled": "galaxy.analysis.node.failed.v1",
    }.get(state, "galaxy.analysis.node.updated.v1")
    return build_event(
        event_type=event_type,
        source="urn:asterism:integration:a2a",
        subject=node_id,
        run_id=run_id,
        adapter="a2a-interface/0.1.0",
        native_id=f"{task_id}:{state}",
        correlation_id=context_id,
        capture_content=capture_content,
        data={
            **entity_payload(
                "node",
                entity_id=node_id,
                run_id=run_id,
                status=event_type.split(".")[3],
                title=f"A2A task {task_id}",
            ),
            "a2a_object": "Task",
            "native": dict(task),
        },
    )
