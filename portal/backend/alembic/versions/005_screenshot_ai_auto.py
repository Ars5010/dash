"""user ai_analyze_screenshots + screenshot_analyses

Revision ID: 005_screenshot_ai
Revises: 004_self_reg
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005_screenshot_ai"
down_revision = "004_self_reg"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("ai_analyze_screenshots", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_table(
        "screenshot_analyses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("media_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("productive_score", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("unproductive", sa.Boolean(), nullable=True),
        sa.Column("concerns", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_ru", sa.Text(), nullable=True),
        sa.Column("vision_model", sa.String(length=120), nullable=True),
        sa.Column("raw_model_text", sa.Text(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("media_file_id", name="uq_screenshot_analyses_media_file"),
    )
    op.create_index("ix_screenshot_analyses_org_analyzed", "screenshot_analyses", ["org_id", "analyzed_at"])
    op.create_index("ix_screenshot_analyses_user_analyzed", "screenshot_analyses", ["user_id", "analyzed_at"])


def downgrade() -> None:
    op.drop_index("ix_screenshot_analyses_user_analyzed", table_name="screenshot_analyses")
    op.drop_index("ix_screenshot_analyses_org_analyzed", table_name="screenshot_analyses")
    op.drop_table("screenshot_analyses")
    op.drop_column("users", "ai_analyze_screenshots")
