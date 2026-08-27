"""initial schema – reports table

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column("research_type", sa.String(32), nullable=False),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("report_markdown", sa.Text, nullable=True),
        sa.Column("raw_data", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("stage", sa.String(32), nullable=True, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])
    op.create_index("ix_reports_type_status", "reports", ["research_type", "status"])


def downgrade() -> None:
    op.drop_index("ix_reports_type_status", table_name="reports")
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_table("reports")
