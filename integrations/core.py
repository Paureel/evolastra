"""Canonical event construction and privacy helpers.

This module intentionally uses only the Python standard library so telemetry
capture remains usable when optional agent SDKs are absent.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from collections import OrderedDict
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

SCHEMA_URI = "/schemas/events/semantic-event-v1.json"
PRODUCER_VERSION = "asterism-integrations/0.1.0"
_EVENT_TYPE = re.compile(
    r"^galaxy\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.v[1-9][0-9]*$"
)
_PREFIX = re.compile(r"^[a-z][a-z0-9_]{1,15}$")
_HEX_TRACE = re.compile(r"^[0-9a-f]{32}$")
_HEX_SPAN = re.compile(r"^[0-9a-f]{16}$")
_ID_CACHE: OrderedDict[tuple[str, str, str], str] = OrderedDict()
_ID_CACHE_LIMIT = 200_000
_ID_LOCK = threading.Lock()
_SUBJECT_SEGMENTS = {
    "agent": "agent",
    "approval": "approval",
    "art": "artifact",
    "claim": "claim",
    "dataset": "dataset",
    "dataset_version": "dataset_version",
    "log": "log",
    "node": "node",
    "span": "span",
    "tool": "toolcall",
}
_SEMANTIC_ENTITY_KEYS = {
    ("analysis", "agent"): "agent",
    ("analysis", "anomaly"): "anomaly",
    ("analysis", "artifact"): "artifact",
    ("analysis", "claim"): "claim",
    ("analysis", "evidence"): "evidence",
    ("analysis", "finding"): "finding",
    ("analysis", "node"): "node",
    ("analysis", "run"): "run",
    ("analysis", "toolcall"): "tool_call",
    ("data", "dataset"): "dataset",
    ("data", "dataset_version"): "dataset_version",
    ("governance", "approval"): "approval",
}
_SEMANTIC_ENTITY_VALUES = frozenset(_SEMANTIC_ENTITY_KEYS.values())

_SECRET_KEY = re.compile(
    r"(?:^|[_-])(?:api[_-]?key|authorization|cookie|credential|passwd|password|private[_-]?key|secret|session[_-]?token|token)(?:$|[_-])",
    re.IGNORECASE,
)
_CONTENT_KEY = re.compile(
    r"(?:^|[_-])(?:body|content|input|message|output|prompt|response|text|transcript)(?:$|[_-])",
    re.IGNORECASE,
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _normalize_time(value: str | None) -> str:
    if not value:
        return utc_now()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("event time must include a timezone")
    return parsed.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_scalar(value: Any, *, max_string: int) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        text = value[:max_string]
        for pattern in _SECRET_VALUE_PATTERNS:
            text = pattern.sub("[REDACTED_SECRET]", text)
        return text
    return str(value)[:max_string]


def redact(
    value: Any,
    *,
    capture_content: bool = False,
    max_depth: int = 8,
    max_items: int = 100,
    max_string: int = 4096,
    _depth: int = 0,
) -> Any:
    """Return a bounded, JSON-safe copy with secrets removed.

    Content-shaped fields are default-deny because prompts, tool arguments,
    responses, and transcripts routinely contain source code or personal data.
    Setting ``capture_content`` does not disable secret redaction.
    """

    if _depth >= max_depth:
        return "[TRUNCATED_DEPTH]"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for index, (raw_key, item) in enumerate(value.items()):
            if index >= max_items:
                result["_truncated_items"] = len(value) - max_items
                break
            key = str(raw_key)[:256]
            if _SECRET_KEY.search(key):
                result[key] = "[REDACTED_SECRET]"
            elif _CONTENT_KEY.search(key) and not capture_content:
                if isinstance(item, str):
                    result[key] = {"redacted": True, "length": len(item)}
                else:
                    result[key] = "[REDACTED_CONTENT]"
            else:
                result[key] = redact(
                    item,
                    capture_content=capture_content,
                    max_depth=max_depth,
                    max_items=max_items,
                    max_string=max_string,
                    _depth=_depth + 1,
                )
        return result
    if isinstance(value, list | tuple | set):
        items = list(value)
        safe = [
            redact(
                item,
                capture_content=capture_content,
                max_depth=max_depth,
                max_items=max_items,
                max_string=max_string,
                _depth=_depth + 1,
            )
            for item in items[:max_items]
        ]
        if len(items) > max_items:
            safe.append({"_truncated_items": len(items) - max_items})
        return safe
    return _safe_scalar(value, max_string=max_string)


def deduplication_key(adapter: str, native_id: str | None, payload: Mapping[str, Any]) -> str:
    """Create a stable adapter-scoped key for retry and overlap detection."""

    if native_id:
        material = f"{adapter}\x00{native_id}"
    else:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        material = f"{adapter}\x00{canonical}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def stable_prefixed_id(prefix: str, namespace: str, value: str) -> str:
    """Resolve one native identity to a process-local compact UUIDv4.

    Adapters that span processes must persist this mapping themselves. The
    deterministic deduplication key, not this identifier, provides idempotency.
    """

    key = (prefix, namespace, value)
    with _ID_LOCK:
        identifier = _ID_CACHE.get(key)
        if identifier is None:
            identifier = f"{prefix}_{uuid.uuid4().hex}"
            _ID_CACHE[key] = identifier
            if len(_ID_CACHE) > _ID_CACHE_LIMIT:
                _ID_CACHE.popitem(last=False)
        else:
            _ID_CACHE.move_to_end(key)
        return identifier


def new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def is_prefixed_uuid4(value: str, expected_prefix: str | None = None) -> bool:
    try:
        prefix, raw = value.split("_", 1)
        parsed = uuid.UUID(raw)
    except (ValueError, AttributeError):
        return False
    return (
        bool(_PREFIX.fullmatch(prefix))
        and parsed.version == 4
        and (expected_prefix is None or prefix == expected_prefix)
    )


def _reference_id(value: str, prefix: str, *, fallback: str) -> str:
    if not value:
        return fallback
    if is_prefixed_uuid4(value):
        return value
    return stable_prefixed_id(prefix, "event-reference", value)


def _subject_path(subject: str, run_id: str) -> str:
    if "/" in subject:
        return subject
    if subject == run_id:
        return f"run/{run_id}"
    prefix = subject.split("_", 1)[0]
    segment = _SUBJECT_SEGMENTS.get(prefix, "entity")
    return f"run/{run_id}/{segment}/{subject}"


def trace_id(value: str) -> str:
    return hashlib.sha256(f"trace:{value}".encode()).hexdigest()[:32]


def span_id(value: str) -> str:
    return hashlib.sha256(f"span:{value}".encode()).hexdigest()[:16]


def entity_payload(
    entity_key: str,
    *,
    entity_id: str,
    run_id: str,
    schema_version: int = 1,
    **fields: Any,
) -> dict[str, Any]:
    """Create the canonical ``data.<entity>`` identity wrapper."""

    if entity_key not in _SEMANTIC_ENTITY_VALUES:
        raise ValueError(f"unsupported canonical entity key: {entity_key}")
    return {
        entity_key: {
            "id": entity_id,
            "run_id": run_id,
            "schema_version": schema_version,
            **fields,
        }
    }


def build_event(
    *,
    event_type: str,
    source: str,
    subject: str,
    run_id: str,
    data: Mapping[str, Any],
    adapter: str,
    native_id: str | None = None,
    deduplication_key_override: str | None = None,
    sequence: int | None = None,
    trace: str | None = None,
    span: str | None = None,
    correlation_id: str = "",
    causation_id: str = "",
    privacy_class: str = "internal",
    producer_version: str = PRODUCER_VERSION,
    event_time: str | None = None,
    capture_content: bool = False,
) -> dict[str, Any]:
    """Build the immutable shared CloudEvents-compatible ingestion envelope."""

    safe_data = redact(data, capture_content=capture_content)
    key = (
        hashlib.sha256(f"configured\0{deduplication_key_override}".encode()).hexdigest()
        if deduplication_key_override is not None
        else deduplication_key(adapter, native_id, safe_data)
    )
    enriched = dict(safe_data)
    if "integration" in enriched and not isinstance(enriched["integration"], dict):
        enriched["integration_native"] = enriched.pop("integration")
    enriched.setdefault("integration", {})
    enriched["integration"].update({"adapter": adapter, "deduplication_key": key})
    event_id = new_prefixed_id("evt")
    event: dict[str, Any] = {
        "specversion": "1.0",
        "id": event_id,
        "source": source,
        "type": event_type,
        "subject": _subject_path(subject, run_id),
        "time": _normalize_time(event_time),
        "datacontenttype": "application/json",
        "dataschema": SCHEMA_URI,
        "runid": run_id,
        "traceid": trace or trace_id(run_id),
        "spanid": span or span_id(native_id or key),
        "correlationid": _reference_id(correlation_id, "corr", fallback=run_id),
        "causationid": _reference_id(causation_id or (native_id or ""), "cause", fallback=event_id),
        "producerversion": producer_version,
        "privacyclass": privacy_class,
        "data": enriched,
    }
    if sequence is not None:
        event["sequence"] = sequence
    validate_envelope(event)
    return event


def validate_envelope(event: Mapping[str, Any], *, allow_unallocated_sequence: bool = True) -> None:
    required = {
        "specversion",
        "id",
        "source",
        "type",
        "subject",
        "time",
        "datacontenttype",
        "dataschema",
        "runid",
        "traceid",
        "spanid",
        "correlationid",
        "causationid",
        "producerversion",
        "privacyclass",
        "data",
    }
    missing = sorted(required.difference(event))
    if missing:
        raise ValueError(f"event envelope missing fields: {', '.join(missing)}")
    if event["specversion"] != "1.0":
        raise ValueError("only CloudEvents specversion 1.0 is supported")
    if not _EVENT_TYPE.fullmatch(str(event["type"])):
        raise ValueError("event type must match galaxy.<area>.<entity>.<action>.vN")
    if not isinstance(event["data"], Mapping):
        raise ValueError("event data must be an object")
    if not is_prefixed_uuid4(str(event["id"]), "evt"):
        raise ValueError("event id must be an evt_ prefixed UUIDv4")
    if not is_prefixed_uuid4(str(event["runid"]), "run"):
        raise ValueError("runid must be a run_ prefixed UUIDv4")
    if not is_prefixed_uuid4(str(event["correlationid"])):
        raise ValueError("correlationid must be a prefixed UUIDv4")
    if not is_prefixed_uuid4(str(event["causationid"])):
        raise ValueError("causationid must be a prefixed UUIDv4")
    if not _HEX_TRACE.fullmatch(str(event["traceid"])) or set(str(event["traceid"])) == {"0"}:
        raise ValueError("traceid must be a non-zero lowercase W3C trace id")
    if not _HEX_SPAN.fullmatch(str(event["spanid"])) or set(str(event["spanid"])) == {"0"}:
        raise ValueError("spanid must be a non-zero lowercase W3C span id")
    if event["dataschema"] != SCHEMA_URI:
        raise ValueError(f"dataschema must be {SCHEMA_URI}")
    if not str(event["subject"]).startswith(f"run/{event['runid']}"):
        raise ValueError("subject must be a stable path scoped to runid")
    type_parts = str(event["type"]).split(".")
    entity_key = _SEMANTIC_ENTITY_KEYS.get((type_parts[1], type_parts[2]))
    if entity_key:
        entity = event["data"].get(entity_key)
        if not isinstance(entity, Mapping):
            raise ValueError(f"semantic event requires data.{entity_key}")
        if not is_prefixed_uuid4(str(entity.get("id", ""))):
            raise ValueError(f"data.{entity_key}.id must be a prefixed UUIDv4")
        if entity_key == "run" and entity["id"] != event["runid"]:
            raise ValueError("data.run.id must match runid")
        if entity.get("run_id") != event["runid"]:
            raise ValueError(f"data.{entity_key}.run_id must match runid")
        if (
            isinstance(entity.get("schema_version"), bool)
            or not isinstance(entity.get("schema_version"), int)
            or entity["schema_version"] < 1
        ):
            raise ValueError(f"data.{entity_key}.schema_version must be a positive integer")
    _normalize_time(str(event["time"]))
    if "sequence" not in event and allow_unallocated_sequence:
        return
    sequence = event.get("sequence")
    if not isinstance(sequence, int) or sequence < 1:
        raise ValueError("allocated sequence must be a positive integer")
