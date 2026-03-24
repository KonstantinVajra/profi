"""add contact_info to projects

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-24

Adds nullable JSON column contact_info to the projects table.
Structure: flat dict { whatsapp, telegram, phone, instagram, vk } — all str | None.
No backfill — existing rows get NULL, meaning "no contacts configured".
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("contact_info", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "contact_info")
