"""Context managers and decorators for emitting canonical analysis events."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, Protocol, TypeVar
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from integrations.core import build_event, entity_payload, utc_now
from integrations.jsonl import JsonlWriter

P = ParamSpec("P")
R = TypeVar("R")


class Sink(Protocol):
    def emit(self, event: dict[str, Any]) -> None: ...


class ListSink:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)


class JsonlSink:
    def __init__(self, path: str | Path, *, capture_content: bool = False) -> None:
        self.writer = JsonlWriter(path, capture_content=capture_content)

    def emit(self, event: dict[str, Any]) -> None:
        self.writer.write(event)


class HttpSink:
    """Small synchronous HTTP sink; use a buffered sink on latency-sensitive paths."""

    def __init__(self, endpoint: str, *, timeout: float = 2.0, fail_open: bool = True) -> None:
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("endpoint must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("endpoint credentials must not be embedded in the URL")
        self.endpoint = endpoint
        self.timeout = timeout
        self.fail_open = fail_open

    def emit(self, event: dict[str, Any]) -> None:
        import json

        request = Request(  # noqa: S310 - endpoint validated in __init__
            self.endpoint,
            data=json.dumps(event, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/cloudevents+json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout):  # noqa: S310 - endpoint validated in __init__
                pass
        except Exception:
            if not self.fail_open:
                raise


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class ArtifactRef:
    id: str
    sha256: str
    size: int
    filename: str


class GalaxyClient:
    def __init__(
        self,
        sink: Sink,
        *,
        source: str = "urn:asterism:sdk:python",
        producer_version: str = "galaxy-sdk-python/0.1.0",
        capture_content: bool = False,
        deduplication_key: Callable[[str, str, dict[str, Any]], str] | None = None,
    ) -> None:
        self.sink = sink
        self.source = source
        self.producer_version = producer_version
        self.capture_content = capture_content
        self.deduplication_key = deduplication_key

    def _emit(
        self,
        event_type: str,
        *,
        run_id: str,
        subject: str,
        data: dict[str, Any],
        native_id: str,
        causation_id: str = "",
    ) -> dict[str, Any]:
        event = build_event(
            event_type=event_type,
            source=self.source,
            subject=subject,
            run_id=run_id,
            adapter=self.producer_version,
            native_id=native_id,
            deduplication_key_override=(
                self.deduplication_key(event_type, native_id, data)
                if self.deduplication_key
                else None
            ),
            causation_id=causation_id,
            producer_version=self.producer_version,
            capture_content=self.capture_content,
            data=data,
        )
        self.sink.emit(event)
        return event

    def start_run(
        self,
        *,
        title: str,
        objective: str,
        run_id: str | None = None,
        tags: list[str] | None = None,
    ) -> RunScope:
        return RunScope(self, run_id or _id("run"), title, objective, tags or [])


class RunScope(AbstractContextManager["RunScope"]):
    def __init__(
        self, client: GalaxyClient, run_id: str, title: str, objective: str, tags: list[str]
    ) -> None:
        self.client = client
        self.id = run_id
        self.title = title
        self.objective = objective
        self.tags = tags
        self._entered = False

    def __enter__(self) -> RunScope:
        self._entered = True
        common = {
            "title": self.title,
            "objective": self.objective,
            "tags": self.tags,
            "run_seed": uuid.UUID(self.id.split("_", 1)[1]).int & 0x7FFFFFFF,
            "privacy_classification": "internal",
        }
        self.client._emit(
            "galaxy.analysis.run.created.v1",
            run_id=self.id,
            subject=self.id,
            data=entity_payload(
                "run",
                entity_id=self.id,
                run_id=self.id,
                status="created",
                created_at=utc_now(),
                **common,
            ),
            native_id=f"{self.id}:created",
        )
        self.client._emit(
            "galaxy.analysis.run.started.v1",
            run_id=self.id,
            subject=self.id,
            data=entity_payload(
                "run", entity_id=self.id, run_id=self.id, status="started", **common
            ),
            native_id=f"{self.id}:started",
        )
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        failed = exc is not None
        self.client._emit(
            "galaxy.analysis.run.failed.v1" if failed else "galaxy.analysis.run.completed.v1",
            run_id=self.id,
            subject=self.id,
            data=entity_payload(
                "run",
                entity_id=self.id,
                run_id=self.id,
                status="failed" if failed else "completed",
                error=str(exc) if failed else None,
            ),
            native_id=f"{self.id}:{'failed' if failed else 'completed'}",
        )
        return False

    def start_node(
        self,
        *,
        title: str,
        node_type: str,
        parent_node_id: str | None = None,
        node_id: str | None = None,
    ) -> NodeScope:
        return NodeScope(self, node_id or _id("node"), title, node_type, parent_node_id)

    def instrument_node(
        self,
        *,
        title: str,
        node_type: str,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        def decorator(function: Callable[P, R]) -> Callable[P, R]:
            @wraps(function)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                with self.start_node(title=title, node_type=node_type):
                    return function(*args, **kwargs)

            return wrapped

        return decorator


class NodeScope(AbstractContextManager["NodeScope"]):
    def __init__(
        self, run: RunScope, node_id: str, title: str, node_type: str, parent_node_id: str | None
    ) -> None:
        self.run = run
        self.client = run.client
        self.id = node_id
        self.title = title
        self.node_type = node_type
        self.parent_node_id = parent_node_id

    def __enter__(self) -> NodeScope:
        common = {
            "title": self.title,
            "node_type": self.node_type,
            "parent_node_id": self.parent_node_id,
            "promotion_reason": "explicit_sdk_node",
        }
        self.client._emit(
            "galaxy.analysis.node.created.v1",
            run_id=self.run.id,
            subject=self.id,
            data=entity_payload(
                "node",
                entity_id=self.id,
                run_id=self.run.id,
                status="created",
                created_at=utc_now(),
                **common,
            ),
            native_id=f"{self.id}:created",
        )
        self.client._emit(
            "galaxy.analysis.node.started.v1",
            run_id=self.run.id,
            subject=self.id,
            data=entity_payload(
                "node",
                entity_id=self.id,
                run_id=self.run.id,
                status="started",
                **common,
            ),
            native_id=f"{self.id}:started",
        )
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        failed = exc is not None
        self.client._emit(
            "galaxy.analysis.node.failed.v1" if failed else "galaxy.analysis.node.completed.v1",
            run_id=self.run.id,
            subject=self.id,
            data=entity_payload(
                "node",
                entity_id=self.id,
                run_id=self.run.id,
                status="failed" if failed else "completed",
                node_type=self.node_type,
                title=self.title,
                error=str(exc) if failed else None,
            ),
            native_id=f"{self.id}:{'failed' if failed else 'completed'}",
            causation_id=self.parent_node_id or self.run.id,
        )
        return False

    def start_tool_call(self, name: str, *, tool_call_id: str | None = None) -> ToolCallScope:
        return ToolCallScope(self, tool_call_id or _id("tool"), name)

    def create_claim(
        self,
        *,
        title: str,
        statement: str,
        evidence_artifact_ids: list[str] | None = None,
        validation_status: str = "unvalidated",
    ) -> str:
        claim_id = _id("claim")
        self.client._emit(
            "galaxy.analysis.claim.created.v1",
            run_id=self.run.id,
            subject=claim_id,
            native_id=f"{claim_id}:created",
            causation_id=self.id,
            data=entity_payload(
                "claim",
                entity_id=claim_id,
                run_id=self.run.id,
                node_id=self.id,
                title=title,
                statement=statement,
                evidence_artifact_ids=evidence_artifact_ids or [],
                validation_status=validation_status,
            ),
        )
        return claim_id


class ToolCallScope(AbstractContextManager["ToolCallScope"]):
    def __init__(self, node: NodeScope, tool_call_id: str, name: str) -> None:
        self.node = node
        self.client = node.client
        self.id = tool_call_id
        self.name = name

    def __enter__(self) -> ToolCallScope:
        common = {"node_id": self.node.id, "tool_name": self.name}
        self.client._emit(
            "galaxy.analysis.toolcall.requested.v1",
            run_id=self.node.run.id,
            subject=self.id,
            data=entity_payload(
                "tool_call",
                entity_id=self.id,
                run_id=self.node.run.id,
                status="requested",
                **common,
            ),
            native_id=f"{self.id}:requested",
            causation_id=self.node.id,
        )
        self.client._emit(
            "galaxy.analysis.toolcall.started.v1",
            run_id=self.node.run.id,
            subject=self.id,
            data=entity_payload(
                "tool_call",
                entity_id=self.id,
                run_id=self.node.run.id,
                status="started",
                **common,
            ),
            native_id=f"{self.id}:started",
            causation_id=self.node.id,
        )
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        failed = exc is not None
        self.client._emit(
            "galaxy.analysis.toolcall.failed.v1"
            if failed
            else "galaxy.analysis.toolcall.completed.v1",
            run_id=self.node.run.id,
            subject=self.id,
            data=entity_payload(
                "tool_call",
                entity_id=self.id,
                run_id=self.node.run.id,
                status="failed" if failed else "completed",
                node_id=self.node.id,
                tool_name=self.name,
                error=str(exc) if failed else None,
            ),
            native_id=f"{self.id}:{'failed' if failed else 'completed'}",
            causation_id=self.node.id,
        )
        return False

    def register_artifact(
        self,
        *,
        path: str | Path,
        artifact_type: str,
        title: str,
        media_type: str = "application/octet-stream",
    ) -> ArtifactRef:
        local_path = Path(path)
        digest = hashlib.sha256()
        size = 0
        with local_path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        checksum = digest.hexdigest()
        artifact_id = _id("art")
        reference = ArtifactRef(artifact_id, checksum, size, local_path.name)
        self.client._emit(
            "galaxy.analysis.artifact.created.v1",
            run_id=self.node.run.id,
            subject=artifact_id,
            native_id=f"sha256:{checksum}",
            causation_id=self.id,
            data=entity_payload(
                "artifact",
                entity_id=artifact_id,
                run_id=self.node.run.id,
                node_id=self.node.id,
                tool_call_id=self.id,
                title=title,
                artifact_type=artifact_type,
                mime_type=media_type,
                content_hash=f"sha256:{checksum}",
                byte_size=size,
                filename=local_path.name,
                created_at=utc_now(),
                privacy_classification="internal",
            ),
        )
        return reference
