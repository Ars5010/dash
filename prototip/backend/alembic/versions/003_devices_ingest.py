"""Devices/enrollment/ingest tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.String(length=100), nullable=True),
        sa.Column("device_id", sa.String(length=200), nullable=False),
        sa.Column("hostname", sa.String(length=200), nullable=True),
        sa.Column("os", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
    )
    op.create_index(op.f("ix_devices_device_id"), "devices", ["device_id"], unique=True)
    op.create_index(op.f("ix_devices_id"), "devices", ["id"], unique=False)
    op.create_index(op.f("ix_devices_org_id"), "devices", ["org_id"], unique=False)

    op.create_table(
        "enrollment_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=200), nullable=False),
        sa.Column("org_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_device_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["used_by_device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_enrollment_codes_code"), "enrollment_codes", ["code"], unique=True)
    op.create_index(op.f("ix_enrollment_codes_id"), "enrollment_codes", ["id"], unique=False)
    op.create_index(op.f("ix_enrollment_codes_org_id"), "enrollment_codes", ["org_id"], unique=False)

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_device_tokens_device_id"), "device_tokens", ["device_id"], unique=False)
    op.create_index(op.f("ix_device_tokens_id"), "device_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_device_tokens_token"), "device_tokens", ["token"], unique=True)

    op.create_table(
        "activity_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("raw_bucket", sa.String(length=200), nullable=True),
        sa.Column("raw_event_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "seq", name="uq_activity_events_device_seq"),
    )
    op.create_index(op.f("ix_activity_events_device_id"), "activity_events", ["device_id"], unique=False)
    op.create_index(op.f("ix_activity_events_id"), "activity_events", ["id"], unique=False)
    op.create_index(op.f("ix_activity_events_received_at"), "activity_events", ["received_at"], unique=False)
    op.create_index(op.f("ix_activity_events_ts"), "activity_events", ["ts"], unique=False)
    op.create_index(op.f("ix_activity_events_type"), "activity_events", ["type"], unique=False)
    op.create_index("ix_activity_events_device_ts", "activity_events", ["device_id", "ts"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_events_device_ts", table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_type"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_ts"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_received_at"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_id"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_device_id"), table_name="activity_events")
    op.drop_table("activity_events")

    op.drop_index(op.f("ix_device_tokens_token"), table_name="device_tokens")
    op.drop_index(op.f("ix_device_tokens_id"), table_name="device_tokens")
    op.drop_index(op.f("ix_device_tokens_device_id"), table_name="device_tokens")
    op.drop_table("device_tokens")

    op.drop_index(op.f("ix_enrollment_codes_org_id"), table_name="enrollment_codes")
    op.drop_index(op.f("ix_enrollment_codes_id"), table_name="enrollment_codes")
    op.drop_index(op.f("ix_enrollment_codes_code"), table_name="enrollment_codes")
    op.drop_table("enrollment_codes")

    op.drop_index(op.f("ix_devices_org_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_device_id"), table_name="devices")
    op.drop_table("devices")

