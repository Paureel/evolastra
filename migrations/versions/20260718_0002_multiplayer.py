"""Add host-authoritative multiplayer collaboration state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0002"
down_revision: str | None = "20260717_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "multiplayer_sessions",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("run_id", sa.String(length=80), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("project_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("host_url", sa.String(length=500), nullable=False),
        sa.Column("local_player_id", sa.String(length=80), nullable=False),
        sa.Column("invite_digest", sa.String(length=64), nullable=True),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remote_state", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_multiplayer_session_run"),
    )
    op.create_index("ix_multiplayer_sessions_run_id", "multiplayer_sessions", ["run_id"])
    op.create_table(
        "multiplayer_players",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "display_name", name="uq_multiplayer_player_name"),
        sa.UniqueConstraint("token_digest"),
    )
    op.create_index("ix_multiplayer_players_session_id", "multiplayer_players", ["session_id"])
    op.create_table(
        "multiplayer_claims",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("node_id", sa.String(length=80), nullable=False),
        sa.Column("player_id", sa.String(length=80), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "node_id", name="uq_multiplayer_claim_node"),
    )
    op.create_index("ix_multiplayer_claims_session_id", "multiplayer_claims", ["session_id"])
    op.create_index("ix_multiplayer_claims_node_id", "multiplayer_claims", ["node_id"])
    op.create_index("ix_multiplayer_claims_player_id", "multiplayer_claims", ["player_id"])
    op.create_table(
        "multiplayer_publications",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("player_id", sa.String(length=80), nullable=False),
        sa.Column("finding_id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_multiplayer_publications_session_id", "multiplayer_publications", ["session_id"]
    )
    op.create_index(
        "ix_multiplayer_publications_player_id", "multiplayer_publications", ["player_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_multiplayer_publications_player_id", table_name="multiplayer_publications")
    op.drop_index("ix_multiplayer_publications_session_id", table_name="multiplayer_publications")
    op.drop_table("multiplayer_publications")
    op.drop_index("ix_multiplayer_claims_player_id", table_name="multiplayer_claims")
    op.drop_index("ix_multiplayer_claims_node_id", table_name="multiplayer_claims")
    op.drop_index("ix_multiplayer_claims_session_id", table_name="multiplayer_claims")
    op.drop_table("multiplayer_claims")
    op.drop_index("ix_multiplayer_players_session_id", table_name="multiplayer_players")
    op.drop_table("multiplayer_players")
    op.drop_index("ix_multiplayer_sessions_run_id", table_name="multiplayer_sessions")
    op.drop_table("multiplayer_sessions")
