"""Initial append-only event and projection schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("privacy_class", sa.String(length=40), nullable=False),
        sa.Column("source_adapters", sa.JSON(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("run_id", sa.String(length=80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=180), nullable=False),
        sa.Column("source", sa.String(length=300), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=False),
        sa.Column("span_id", sa.String(length=16), nullable=False),
        sa.Column("correlation_id", sa.String(length=96), nullable=False),
        sa.Column("causation_id", sa.String(length=96), nullable=False),
        sa.Column("privacy_class", sa.String(length=40), nullable=False),
        sa.Column("envelope", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_events_run_sequence"),
    )
    op.create_index("ix_events_run_id", "events", ["run_id"])
    op.create_index("ix_events_run_sequence", "events", ["run_id", "sequence"])
    op.create_index("ix_events_type", "events", ["type"])
    op.create_table(
        "snapshots",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("run_id", sa.String(length=80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_snapshots_run_id", "snapshots", ["run_id"])
    op.create_index("ix_snapshots_run_sequence", "snapshots", ["run_id", "sequence"])
    op.create_table(
        "quarantine",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("run_id", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quarantine_run_id", "quarantine", ["run_id"])
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target", sa.String(length=300), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_quarantine_run_id", table_name="quarantine")
    op.drop_table("quarantine")
    op.drop_index("ix_snapshots_run_sequence", table_name="snapshots")
    op.drop_index("ix_snapshots_run_id", table_name="snapshots")
    op.drop_table("snapshots")
    op.drop_index("ix_events_type", table_name="events")
    op.drop_index("ix_events_run_sequence", table_name="events")
    op.drop_index("ix_events_run_id", table_name="events")
    op.drop_table("events")
    op.drop_table("analysis_runs")
