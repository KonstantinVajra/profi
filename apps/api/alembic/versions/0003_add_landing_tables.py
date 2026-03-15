"""add landing_pages and landing_content tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── landing_pages ─────────────────────────────────────────────────────
    op.create_table(
        "landing_pages",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("project_id",   sa.String(36),  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug",         sa.String(255), nullable=False, unique=True),
        sa.Column("template_key", sa.String(100), nullable=False),
        sa.Column("status",       sa.String(50),  nullable=False, server_default="draft"),
        sa.Column("is_public",    sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime,    nullable=True),
        sa.Column("archived_at",  sa.DateTime,    nullable=True),
        sa.Column("created_at",   sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_landing_pages_project_id", "landing_pages", ["project_id"])
    op.create_index("ix_landing_pages_slug",       "landing_pages", ["slug"])

    # ── landing_content ───────────────────────────────────────────────────
    op.create_table(
        "landing_content",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("landing_page_id", sa.String(36),  sa.ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("content_json",    sa.JSON,        nullable=False),
        sa.Column("version",         sa.Integer,     nullable=False, server_default="1"),
        sa.Column("created_at",      sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime,    server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("landing_content")
    op.drop_index("ix_landing_pages_slug",       table_name="landing_pages")
    op.drop_index("ix_landing_pages_project_id", table_name="landing_pages")
    op.drop_table("landing_pages")
