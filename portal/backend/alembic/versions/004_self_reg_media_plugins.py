"""self-registration, job_title, media files, org feature flags

Revision ID: 004_self_reg
Revises: 003_holidays
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_self_reg"
down_revision = "003_holidays"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("self_registration_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("organizations", sa.Column("install_secret_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("screenshots_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "organizations",
        sa.Column("ai_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("users", sa.Column("job_title", sa.String(length=255), nullable=True))

    op.create_table(
        "media_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
    )
    op.create_index("ix_media_files_org_id", "media_files", ["org_id"])
    op.create_index("ix_media_files_device_id", "media_files", ["device_id"])
    op.create_index("ix_media_files_created_at", "media_files", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_media_files_created_at", table_name="media_files")
    op.drop_index("ix_media_files_device_id", table_name="media_files")
    op.drop_index("ix_media_files_org_id", table_name="media_files")
    op.drop_table("media_files")
    op.drop_column("users", "job_title")
    op.drop_column("organizations", "ai_enabled")
    op.drop_column("organizations", "screenshots_enabled")
    op.drop_column("organizations", "install_secret_hash")
    op.drop_column("organizations", "self_registration_enabled")
