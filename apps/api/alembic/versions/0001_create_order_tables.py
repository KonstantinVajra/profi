"""create order parsing tables

Revision ID: 0001
Revises:
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── projects ─────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id",         sa.String(36),  primary_key=True),
        sa.Column("title",      sa.String(255), nullable=True),
        sa.Column("status",     sa.String(50),  nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime,    server_default=sa.func.now()),
    )

    # ── order_inputs ──────────────────────────────────────────────────────
    op.create_table(
        "order_inputs",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("project_id",      sa.String(36),  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_text",        sa.Text,        nullable=True),
        sa.Column("screenshot_path", sa.String(512), nullable=True),
        sa.Column("source_type",     sa.String(50),  nullable=False, server_default="text"),
        sa.Column("created_at",      sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_order_inputs_project_id", "order_inputs", ["project_id"])

    # ── parsed_orders ─────────────────────────────────────────────────────
    op.create_table(
        "parsed_orders",
        sa.Column("id",                   sa.String(36),  primary_key=True),
        sa.Column("project_id",           sa.String(36),  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_input_id",       sa.String(36),  sa.ForeignKey("order_inputs.id", ondelete="CASCADE"), nullable=False),
        # who
        sa.Column("client_name",          sa.String(255), nullable=True),
        sa.Column("client_label",         sa.String(255), nullable=True),
        # what
        sa.Column("event_type",           sa.String(100), nullable=True),
        sa.Column("event_subtype",        sa.String(100), nullable=True),
        # where
        sa.Column("city",                 sa.String(255), nullable=True),
        sa.Column("location",             sa.String(512), nullable=True),
        # when
        sa.Column("event_date",           sa.Date,        nullable=True),
        sa.Column("date_text",            sa.String(100), nullable=True),
        # how
        sa.Column("duration_text",        sa.String(100), nullable=True),
        sa.Column("guest_count_text",     sa.String(100), nullable=True),
        # money
        sa.Column("budget_max",           sa.Integer,     nullable=True),
        sa.Column("currency",             sa.String(10),  nullable=False, server_default="RUB"),
        # json fields
        sa.Column("requirements",         sa.JSON,        nullable=False, server_default="[]"),
        sa.Column("priority_signals",     sa.JSON,        nullable=False, server_default="[]"),
        # signals
        sa.Column("tone_signal",          sa.String(100), nullable=True),
        sa.Column("extracted_confidence", sa.Float,       nullable=True),
        # meta
        sa.Column("user_confirmed",       sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("created_at",           sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_parsed_orders_project_id",     "parsed_orders", ["project_id"])
    op.create_index("ix_parsed_orders_order_input_id", "parsed_orders", ["order_input_id"])


def downgrade() -> None:
    op.drop_table("parsed_orders")
    op.drop_table("order_inputs")
    op.drop_table("projects")
