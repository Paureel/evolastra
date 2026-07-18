"""Narrow OTLP/HTTP JSON mapping helpers.

This is not an OTLP receiver and does not decode protobuf. A Collector should
handle protocol negotiation and send bounded JSON objects to an ingestion
service. Unknown fields are retained after redaction.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from typing import Any

from .core import build_event, is_prefixed_uuid4, span_id, stable_prefixed_id, trace_id


class UnsupportedOtlpPayload(ValueError):
    pass


def _attribute_map(attributes: Any) -> dict[str, Any]:
    if not isinstance(attributes, list):
        return {}
    result: dict[str, Any] = {}
    for item in attributes:
        if not isinstance(item, Mapping) or not isinstance(item.get("key"), str):
            continue
        value = item.get("value")
        if isinstance(value, Mapping) and len(value) == 1:
            result[item["key"]] = next(iter(value.values()))
        else:
            result[item["key"]] = value
    return result


def _trace_context(native_trace_id: str, native_span_id: str) -> tuple[str, str]:
    trace = native_trace_id.lower()
    span = native_span_id.lower()
    if (
        len(trace) != 32
        or any(char not in "0123456789abcdef" for char in trace)
        or set(trace) == {"0"}
    ):
        trace = trace_id(native_trace_id)
    if (
        len(span) != 16
        or any(char not in "0123456789abcdef" for char in span)
        or set(span) == {"0"}
    ):
        span = span_id(native_span_id)
    return trace, span


def map_traces_json(payload: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    resources = payload.get("resourceSpans")
    if not isinstance(resources, list):
        raise UnsupportedOtlpPayload("expected OTLP JSON resourceSpans array")
    for resource_entry in resources:
        if not isinstance(resource_entry, Mapping):
            continue
        resource = resource_entry.get("resource")
        resource_attrs = (
            _attribute_map(resource.get("attributes")) if isinstance(resource, Mapping) else {}
        )
        scopes = resource_entry.get("scopeSpans", [])
        if not isinstance(scopes, list):
            continue
        for scope_entry in scopes:
            if not isinstance(scope_entry, Mapping):
                continue
            for native in (
                scope_entry.get("spans", []) if isinstance(scope_entry.get("spans"), list) else []
            ):
                if not isinstance(native, Mapping):
                    continue
                native_trace_id = str(native.get("traceId") or "unknown-trace")
                native_span_id = str(native.get("spanId") or "unknown-span")
                run_key = str(resource_attrs.get("galaxy.analysis.run_id") or native_trace_id)
                run_id = (
                    run_key
                    if is_prefixed_uuid4(run_key, "run")
                    else stable_prefixed_id("run", "otlp-trace", run_key)
                )
                mapped_trace_id, mapped_span_id = _trace_context(native_trace_id, native_span_id)
                yield build_event(
                    event_type="galaxy.telemetry.span.recorded.v1",
                    source="urn:asterism:integration:otlp-json",
                    subject=stable_prefixed_id("span", "otlp-span", native_span_id),
                    run_id=run_id,
                    adapter="otlp-http-json/0.1.0",
                    native_id=f"{native_trace_id}:{native_span_id}",
                    trace=mapped_trace_id,
                    span=mapped_span_id,
                    correlation_id=native_trace_id,
                    causation_id=str(native.get("parentSpanId") or ""),
                    data={
                        "otlp": dict(native),
                        "resource_attributes": resource_attrs,
                        "mapping": {"transport": "OTLP/HTTP JSON only"},
                    },
                )


def map_logs_json(payload: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    resources = payload.get("resourceLogs")
    if not isinstance(resources, list):
        raise UnsupportedOtlpPayload("expected OTLP JSON resourceLogs array")
    for resource_entry in resources:
        if not isinstance(resource_entry, Mapping):
            continue
        resource = resource_entry.get("resource")
        resource_attrs = (
            _attribute_map(resource.get("attributes")) if isinstance(resource, Mapping) else {}
        )
        scopes = resource_entry.get("scopeLogs", [])
        if not isinstance(scopes, list):
            continue
        for scope_entry in scopes:
            if not isinstance(scope_entry, Mapping):
                continue
            records = scope_entry.get("logRecords", [])
            for index, native in enumerate(records if isinstance(records, list) else []):
                if not isinstance(native, Mapping):
                    continue
                native_trace_id = str(native.get("traceId") or "untraced")
                native_span_id = str(native.get("spanId") or f"log-{index}")
                run_key = str(resource_attrs.get("galaxy.analysis.run_id") or native_trace_id)
                run_id = (
                    run_key
                    if is_prefixed_uuid4(run_key, "run")
                    else stable_prefixed_id("run", "otlp-log", run_key)
                )
                native_id = json.dumps(native, sort_keys=True, separators=(",", ":"), default=str)
                mapped_trace_id, mapped_span_id = _trace_context(native_trace_id, native_span_id)
                yield build_event(
                    event_type="galaxy.telemetry.log.recorded.v1",
                    source="urn:asterism:integration:otlp-json",
                    subject=stable_prefixed_id("log", "otlp-log", native_id),
                    run_id=run_id,
                    adapter="otlp-http-json/0.1.0",
                    native_id=native_id,
                    trace=mapped_trace_id,
                    span=mapped_span_id,
                    correlation_id=native_trace_id,
                    causation_id=native_span_id,
                    data={"otlp": dict(native), "resource_attributes": resource_attrs},
                )
