"""add photo_set category_key

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "photo_sets",
        sa.Column("category_key", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("photo_sets", "category_key")