"""add org-wide holidays

Revision ID: 003_holidays
Revises: 002_telegram
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "003_holidays"
down_revision = "002_telegram"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="Праздник"),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("org_id", "day", name="uq_holidays_org_day"),
    )
    op.create_index("ix_holidays_org_id", "holidays", ["org_id"])
    op.create_index("ix_holidays_org_day", "holidays", ["org_id", "day"])


def downgrade() -> None:
    op.drop_index("ix_holidays_org_day", table_name="holidays")
    op.drop_index("ix_holidays_org_id", table_name="holidays")
    op.drop_table("holidays")

