"""add client_intent_line, situation_notes, shoot_feel to parsed_orders

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parsed_orders",
        sa.Column("client_intent_line", sa.Text(), nullable=True),
    )
    op.add_column(
        "parsed_orders",
        sa.Column("situation_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "parsed_orders",
        sa.Column("shoot_feel", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parsed_orders", "shoot_feel")
    op.drop_column("parsed_orders", "situation_notes")
    op.drop_column("parsed_orders", "client_intent_line")