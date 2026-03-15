"""add dialogue_messages and dialogue_suggestions tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── dialogue_messages ─────────────────────────────────────────────────
    op.create_table(
        "dialogue_messages",
        sa.Column("id",             sa.String(36), primary_key=True),
        sa.Column("project_id",     sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_type",    sa.String(20), nullable=False),
        sa.Column("message_text",   sa.Text,       nullable=False),
        sa.Column("source_channel", sa.String(50), nullable=False, server_default="profi"),
        sa.Column("created_at",     sa.DateTime,   server_default=sa.func.now()),
    )
    op.create_index("ix_dialogue_messages_project_id", "dialogue_messages", ["project_id"])

    # ── dialogue_suggestions ──────────────────────────────────────────────
    op.create_table(
        "dialogue_suggestions",
        sa.Column("id",                  sa.String(36), primary_key=True),
        sa.Column("project_id",          sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_message_id",   sa.String(36), sa.ForeignKey("dialogue_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detected_intent",     sa.String(100), nullable=False),
        sa.Column("detected_stage",      sa.String(50),  nullable=False),
        sa.Column("suggestions_json",    sa.JSON,        nullable=False),
        sa.Column("next_best_question",  sa.Text,        nullable=False),
        sa.Column("created_at",          sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_dialogue_suggestions_project_id", "dialogue_suggestions", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_dialogue_suggestions_project_id", table_name="dialogue_suggestions")
    op.drop_table("dialogue_suggestions")
    op.drop_index("ix_dialogue_messages_project_id", table_name="dialogue_messages")
    op.drop_table("dialogue_messages")
