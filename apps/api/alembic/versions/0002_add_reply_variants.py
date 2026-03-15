"""add reply_variants table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reply_variants",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("project_id",   sa.String(36),  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_type", sa.String(20),  nullable=False),
        sa.Column("message_text", sa.Text,        nullable=False),
        sa.Column("preview_text", sa.Text,        nullable=False),
        sa.Column("includes_link",sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("is_selected",  sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("created_at",   sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_reply_variants_project_id", "reply_variants", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_reply_variants_project_id", table_name="reply_variants")
    op.drop_table("reply_variants")
