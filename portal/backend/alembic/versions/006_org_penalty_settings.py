"""organizations.penalty_settings JSONB

Revision ID: 006_penalty_settings
Revises: 005_screenshot_ai
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006_penalty_settings"
down_revision = "005_screenshot_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("penalty_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "penalty_settings")
