"""Optional, import-safe OpenAI Agents SDK tracing processor."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .core import build_event, entity_payload, span_id, stable_prefixed_id, trace_id

try:  # Optional dependency. Importing this module must remain safe without it.
    from agents.tracing.processor_interface import TracingProcessor as _TracingProcessor
except ImportError:  # pragma: no cover - normal in the dependency-free test profile

    class _TracingProcessor:  # type: ignore[no-redef]
        pass


_SPAN_TYPES = {
    "task": ("galaxy.analysis.node.started.v1", "galaxy.analysis.node.completed.v1", "node"),
    "agent": ("galaxy.analysis.agent.started.v1", "galaxy.analysis.agent.completed.v1", "agent"),
    "generation": (
        "galaxy.telemetry.model.started.v1",
        "galaxy.telemetry.model.completed.v1",
        "span",
    ),
    "function": (
        "galaxy.analysis.toolcall.started.v1",
        "galaxy.analysis.toolcall.completed.v1",
        "tool",
    ),
    "handoff": (
        "galaxy.analysis.agent.status_changed.v1",
        "galaxy.analysis.agent.handed_off.v1",
        "agent",
    ),
    "guardrail": (
        "galaxy.telemetry.validation.started.v1",
        "galaxy.telemetry.validation.completed.v1",
        "span",
    ),
    "custom": (
        "galaxy.telemetry.custom.started.v1",
        "galaxy.telemetry.custom.completed.v1",
        "span",
    ),
}


class AsterismTracingProcessor(_TracingProcessor):
    """Translate public ``TracingProcessor`` callbacks to canonical events.

    ``sink`` should be a quick callable. For network delivery, pass a buffered
    sink instead of doing synchronous I/O in SDK callbacks.
    """

    def __init__(
        self,
        sink: Callable[[dict[str, Any]], Any],
        *,
        capture_content: bool = False,
        deduplication_key: Callable[[str, str, str], str] | None = None,
    ) -> None:
        self.sink = sink
        self.capture_content = capture_content
        self.deduplication_key = deduplication_key

    def _emit(self, event: dict[str, Any]) -> None:
        try:
            self.sink(event)
        except Exception:
            # Observability must not change the agent application's outcome.
            return

    def on_trace_start(self, trace: Any) -> None:
        try:
            native_trace_id = str(getattr(trace, "trace_id", "unknown-trace"))
            run_id = stable_prefixed_id("run", "openai-agents-trace", native_trace_id)
            event = build_event(
                event_type="galaxy.analysis.run.started.v1",
                source="urn:asterism:integration:openai-agents",
                subject=run_id,
                run_id=run_id,
                adapter="openai-agents-tracing/0.1.0",
                native_id=f"{native_trace_id}:start",
                deduplication_key_override=(
                    self.deduplication_key(native_trace_id, "trace", "start")
                    if self.deduplication_key
                    else None
                ),
                trace=trace_id(native_trace_id),
                correlation_id=str(getattr(trace, "group_id", "") or native_trace_id),
                capture_content=self.capture_content,
                data={
                    **entity_payload("run", entity_id=run_id, run_id=run_id, status="started"),
                    "sdk_trace_id": native_trace_id,
                    "name": getattr(trace, "name", None),
                    "group_id": getattr(trace, "group_id", None),
                    "phase": "start",
                },
            )
        except Exception:
            return
        self._emit(event)

    def on_trace_end(self, trace: Any) -> None:
        try:
            native_trace_id = str(getattr(trace, "trace_id", "unknown-trace"))
            run_id = stable_prefixed_id("run", "openai-agents-trace", native_trace_id)
            event = build_event(
                event_type="galaxy.analysis.run.completed.v1",
                source="urn:asterism:integration:openai-agents",
                subject=run_id,
                run_id=run_id,
                adapter="openai-agents-tracing/0.1.0",
                native_id=f"{native_trace_id}:end",
                deduplication_key_override=(
                    self.deduplication_key(native_trace_id, "trace", "end")
                    if self.deduplication_key
                    else None
                ),
                trace=trace_id(native_trace_id),
                correlation_id=str(getattr(trace, "group_id", "") or native_trace_id),
                capture_content=self.capture_content,
                data={
                    **entity_payload("run", entity_id=run_id, run_id=run_id, status="completed"),
                    "sdk_trace_id": native_trace_id,
                    "name": getattr(trace, "name", None),
                    "phase": "end",
                },
            )
        except Exception:
            return
        self._emit(event)

    def _span_event(self, sdk_span: Any, phase: str) -> dict[str, Any]:
        native_trace_id = str(getattr(sdk_span, "trace_id", "unknown-trace"))
        native_span_id = str(getattr(sdk_span, "span_id", "unknown-span"))
        run_id = stable_prefixed_id("run", "openai-agents-trace", native_trace_id)
        span_data = getattr(sdk_span, "span_data", None)
        sdk_type = str(getattr(span_data, "type", "custom"))
        mapping = _SPAN_TYPES.get(sdk_type, _SPAN_TYPES["custom"])
        has_error = getattr(sdk_span, "error", None) is not None
        event_type = mapping[0 if phase == "start" else 1]
        if phase == "end" and has_error:
            area = (
                "analysis.toolcall"
                if sdk_type == "function"
                else "analysis.agent"
                if sdk_type in {"agent", "handoff"}
                else "analysis.node"
                if sdk_type == "task"
                else "telemetry.span"
            )
            event_type = f"galaxy.{area}.failed.v1"
        subject = stable_prefixed_id(mapping[2], f"openai-agents-{sdk_type}", native_span_id)
        exported: Mapping[str, Any]
        try:
            candidate = span_data.export()
            exported = candidate if isinstance(candidate, Mapping) else {"type": sdk_type}
        except Exception:
            exported = {"type": sdk_type}
        data: dict[str, Any] = {
            "sdk_trace_id": native_trace_id,
            "sdk_span_id": native_span_id,
            "sdk_parent_id": getattr(sdk_span, "parent_id", None),
            "sdk_span_type": sdk_type,
            "phase": phase,
            "span_data": dict(exported),
            "error": getattr(sdk_span, "error", None),
        }
        entity_key = {
            "task": "node",
            "agent": "agent",
            "function": "tool_call",
            "handoff": "agent",
        }.get(sdk_type)
        if event_type.startswith("galaxy.analysis.") and entity_key:
            data.update(
                entity_payload(
                    entity_key,
                    entity_id=subject,
                    run_id=run_id,
                    status=event_type.split(".")[3],
                    sdk_span_type=sdk_type,
                    name=exported.get("name"),
                )
            )
        return build_event(
            event_type=event_type,
            source="urn:asterism:integration:openai-agents",
            subject=subject,
            run_id=run_id,
            adapter="openai-agents-tracing/0.1.0",
            native_id=f"{native_span_id}:{phase}",
            deduplication_key_override=(
                self.deduplication_key(native_trace_id, native_span_id, phase)
                if self.deduplication_key
                else None
            ),
            trace=trace_id(native_trace_id),
            span=span_id(native_span_id),
            correlation_id=native_trace_id,
            causation_id=str(getattr(sdk_span, "parent_id", "") or ""),
            event_time=getattr(sdk_span, "started_at" if phase == "start" else "ended_at", None),
            capture_content=self.capture_content,
            data=data,
        )

    def on_span_start(self, span: Any) -> None:
        try:
            event = self._span_event(span, "start")
        except Exception:
            return
        self._emit(event)

    def on_span_end(self, span: Any) -> None:
        try:
            event = self._span_event(span, "end")
        except Exception:
            return
        self._emit(event)

    def shutdown(self) -> None:
        close = getattr(self.sink, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                return

    def force_flush(self) -> None:
        flush = getattr(self.sink, "flush", None)
        if callable(flush):
            try:
                flush()
            except Exception:
                return
