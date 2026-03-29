"""telegram subscriptions

Revision ID: 002_telegram
Revises: 001_init
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa


revision = "002_telegram"
down_revision = "001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("chat_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("org_id", "chat_id", name="uq_telegram_subscriptions_org_chat"),
    )
    op.create_index("ix_telegram_subscriptions_org_id", "telegram_subscriptions", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_telegram_subscriptions_org_id", table_name="telegram_subscriptions")
    op.drop_table("telegram_subscriptions")

