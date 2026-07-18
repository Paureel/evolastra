"""Narrow mapping for the documented Codex SDK run-result surface."""

from __future__ import annotations

from typing import Any

from .core import build_event, entity_payload, stable_prefixed_id

ADAPTER_VERSION = "codex-sdk-result/0.1.0"


def map_run_result(
    *,
    thread_id: str,
    final_response: str,
    failed: bool = False,
    capture_content: bool = False,
) -> dict[str, Any]:
    """Map caller-supplied documented result fields without SDK introspection.

    Python ``openai-codex`` documents ``result.final_response`` and the
    TypeScript SDK documents ``result.finalResponse``. Callers normalize either
    property to ``final_response`` before invoking this function.
    """

    if not thread_id.strip():
        raise ValueError("thread_id must be non-empty")
    run_id = stable_prefixed_id("run", "codex-sdk-thread", thread_id)
    return build_event(
        event_type="galaxy.analysis.run.failed.v1"
        if failed
        else "galaxy.analysis.run.completed.v1",
        source="urn:asterism:integration:codex-sdk",
        subject=run_id,
        run_id=run_id,
        adapter=ADAPTER_VERSION,
        native_id=f"{thread_id}:result:{failed}",
        correlation_id=thread_id,
        capture_content=capture_content,
        data={
            **entity_payload(
                "run",
                entity_id=run_id,
                run_id=run_id,
                status="failed" if failed else "completed",
                final_response=final_response,
            ),
            "thread_id": thread_id,
            "mapping": {"scope": "documented run result only"},
        },
    )
