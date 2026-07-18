from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,15}_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")
TRACE_PATTERN = re.compile(r"^[0-9a-f]{32}$")
SPAN_PATTERN = re.compile(r"^[0-9a-f]{16}$")
EVENT_TYPE_PATTERN = re.compile(r"^galaxy\.[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+\.v[1-9][0-9]*$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunCreate(StrictModel):
    title: str = Field(min_length=3, max_length=300)
    objective: str = Field(min_length=3, max_length=5_000)
    seed: int | None = None
    privacy_class: Literal["public", "internal", "confidential", "restricted"] = "internal"
    tags: list[str] = Field(default_factory=list, max_length=30)


class RunPatch(StrictModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    objective: str | None = Field(default=None, min_length=3, max_length=5_000)
    archive_state: Literal["active", "archived"] | None = None


class CloudEvent(BaseModel):
    """CloudEvents structured JSON with Evolastra extension attributes."""

    model_config = ConfigDict(extra="allow")

    specversion: Literal["1.0"] = "1.0"
    id: str
    source: str = Field(min_length=3, max_length=300)
    type: str
    subject: str = Field(min_length=1, max_length=500)
    time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    datacontenttype: Literal["application/json"] = "application/json"
    dataschema: str = Field(default="/schemas/events/semantic-event-v1.json", max_length=500)
    runid: str
    sequence: int | None = Field(default=None, ge=1)
    traceid: str
    spanid: str
    correlationid: str = Field(max_length=96)
    causationid: str = Field(max_length=96)
    producerversion: str = Field(default="0.1.0", max_length=80)
    privacyclass: Literal["public", "internal", "confidential", "restricted"] = "internal"
    data: dict[str, Any]

    @field_validator("id", "runid")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not ID_PATTERN.fullmatch(value):
            raise ValueError("must be a stable prefixed identifier")
        return value

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if not EVENT_TYPE_PATTERN.fullmatch(value):
            raise ValueError("must use a versioned galaxy.*.vN event type")
        return value

    @field_validator("traceid")
    @classmethod
    def validate_trace_id(cls, value: str) -> str:
        if not TRACE_PATTERN.fullmatch(value):
            raise ValueError("traceid must be 32 lowercase hexadecimal characters")
        return value

    @field_validator("spanid")
    @classmethod
    def validate_span_id(cls, value: str) -> str:
        if not SPAN_PATTERN.fullmatch(value):
            raise ValueError("spanid must be 16 lowercase hexadecimal characters")
        return value


class EventBatch(StrictModel):
    events: list[dict[str, Any]] = Field(min_length=1, max_length=1_000)


class PairingExchange(StrictModel):
    code: str = Field(min_length=14, max_length=32, pattern=r"^[0-9A-Fa-f-]+$")


class CommandRequest(StrictModel):
    command: Literal[
        "pause_animation",
        "return_live",
        "follow_agent",
        "set_simulator_speed",
        "add_annotation",
    ]
    value: str | float | bool | None = None


class ApprovalRequest(StrictModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=2_000)


class SearchResult(StrictModel):
    id: str
    run_id: str
    entity_type: str
    title: str
    context: str
    status: str | None = None


class IngestResult(StrictModel):
    accepted: bool
    duplicate: bool = False
    event_id: str | None = None
    run_id: str | None = None
    sequence: int | None = None
    quarantine_id: str | None = None
    reason: str | None = None
