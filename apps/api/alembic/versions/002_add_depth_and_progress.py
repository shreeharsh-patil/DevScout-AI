"""add depth and progress to reports table

Revision ID: 002_depth_progress
Revises: 001_initial
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_depth_progress"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("depth", sa.String(20), nullable=False, server_default="standard")
    )
    op.add_column(
        "reports",
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("reports", "progress")
    op.drop_column("reports", "depth")
