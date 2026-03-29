"""init portal schema

Revision ID: 001_init
Revises:
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("login", sa.String(length=100), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Europe/Moscow"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_login", "users", ["login"])

    op.create_table(
        "portal_config",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.String(length=2000), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("device_id", sa.String(length=200), nullable=False, unique=True),
        sa.Column("hostname", sa.String(length=200), nullable=True),
        sa.Column("os", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_devices_org_id", "devices", ["org_id"])
    op.create_index("ix_devices_user_id", "devices", ["user_id"])
    op.create_index("ix_devices_device_id", "devices", ["device_id"])

    op.create_table(
        "enrollment_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=200), nullable=False, unique=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_enrollment_codes_code", "enrollment_codes", ["code"])
    op.create_index("ix_enrollment_codes_org_id", "enrollment_codes", ["org_id"])
    op.create_index("ix_enrollment_codes_user_id", "enrollment_codes", ["user_id"])

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_device_tokens_device_id", "device_tokens", ["device_id"])
    op.create_index("ix_device_tokens_token", "device_tokens", ["token"])

    op.create_table(
        "activity_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("raw_bucket", sa.String(length=200), nullable=True),
        sa.Column("raw_event_id", sa.Text(), nullable=True),
        sa.UniqueConstraint("device_id", "seq", name="uq_activity_events_device_seq"),
    )
    op.create_index("ix_activity_events_device_ts", "activity_events", ["device_id", "ts"])
    op.create_index("ix_activity_events_org_ts", "activity_events", ["org_id", "ts"])
    op.create_index("ix_activity_events_user_id", "activity_events", ["user_id"])

    op.create_table(
        "absence_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absence_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_absence_events_user_start", "absence_events", ["user_id", "start_at"])

    op.create_table(
        "productivity_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("pattern", sa.String(length=500), nullable=False),
        sa.Column("is_productive", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_productivity_rules_user", "productivity_rules", ["user_id"])
    op.create_index("ix_productivity_rules_org_id", "productivity_rules", ["org_id"])

    op.create_table(
        "daily_aggregates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("active_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inactive_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("productive_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unproductive_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inactive_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("productive_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unproductive_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kpi_percent_x100", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("indicator", sa.String(length=16), nullable=False, server_default="blue"),
        sa.Column("late", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("early_leave", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("late_penalty_x100", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("early_penalty_x100", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("day_fine", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("org_id", "user_id", "day", name="uq_daily_aggregates_org_user_day"),
    )
    op.create_index("ix_daily_aggregates_org_id", "daily_aggregates", ["org_id"])
    op.create_index("ix_daily_aggregates_user_id", "daily_aggregates", ["user_id"])
    op.create_index("ix_daily_aggregates_day", "daily_aggregates", ["day"])


def downgrade() -> None:
    op.drop_table("daily_aggregates")
    op.drop_table("productivity_rules")
    op.drop_table("absence_events")
    op.drop_index("ix_activity_events_user_id", table_name="activity_events")
    op.drop_index("ix_activity_events_org_ts", table_name="activity_events")
    op.drop_index("ix_activity_events_device_ts", table_name="activity_events")
    op.drop_table("activity_events")
    op.drop_table("device_tokens")
    op.drop_table("enrollment_codes")
    op.drop_table("devices")
    op.drop_table("portal_config")
    op.drop_index("ix_users_login", table_name="users")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_table("users")
    op.drop_table("organizations")

