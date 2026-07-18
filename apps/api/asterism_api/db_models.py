from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class RunRecord(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="created")
    seed: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    privacy_class: Mapped[str] = mapped_column(String(40), default="internal")
    source_adapters: Mapped[list[str]] = mapped_column(JSON, default=list)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRecord(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_events_run_sequence"),
        Index("ix_events_run_sequence", "run_id", "sequence"),
        Index("ix_events_type", "type"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(180))
    source: Mapped[str] = mapped_column(String(300))
    subject: Mapped[str] = mapped_column(String(500))
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str] = mapped_column(String(32), nullable=False)
    span_id: Mapped[str] = mapped_column(String(16), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(96), nullable=False)
    causation_id: Mapped[str] = mapped_column(String(96), nullable=False)
    privacy_class: Mapped[str] = mapped_column(String(40), default="internal")
    envelope: Mapped[dict[str, Any]] = mapped_column(JSON)


class SnapshotRecord(Base):
    __tablename__ = "snapshots"
    __table_args__ = (Index("ix_snapshots_run_sequence", "run_id", "sequence"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QuarantineRecord(Base):
    __tablename__ = "quarantine"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class AuditRecord(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    target: Mapped[str] = mapped_column(String(300))
    actor: Mapped[str] = mapped_column(String(120), default="local-operator")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class MultiplayerSessionRecord(Base):
    __tablename__ = "multiplayer_sessions"
    __table_args__ = (UniqueConstraint("run_id", name="uq_multiplayer_session_run"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    project_fingerprint: Mapped[str] = mapped_column(String(64))
    host_url: Mapped[str] = mapped_column(String(500))
    local_player_id: Mapped[str] = mapped_column(String(80))
    invite_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remote_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MultiplayerPlayerRecord(Base):
    __tablename__ = "multiplayer_players"
    __table_args__ = (
        UniqueConstraint("session_id", "display_name", name="uq_multiplayer_player_name"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(7))
    role: Mapped[str] = mapped_column(String(20))
    token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MultiplayerClaimRecord(Base):
    __tablename__ = "multiplayer_claims"
    __table_args__ = (
        UniqueConstraint("session_id", "node_id", name="uq_multiplayer_claim_node"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    node_id: Mapped[str] = mapped_column(String(80), index=True)
    player_id: Mapped[str] = mapped_column(String(80), index=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MultiplayerPublicationRecord(Base):
    __tablename__ = "multiplayer_publications"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    player_id: Mapped[str] = mapped_column(String(80), index=True)
    finding_id: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
