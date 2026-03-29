"""Leave events: date -> datetime

Revision ID: 002
Revises: 001
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert DATE columns to TIMESTAMP WITH TIME ZONE.
    # For existing rows, interpret date as midnight local time.
    op.alter_column(
        "leave_events",
        "start_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="start_date::timestamp with time zone",
        nullable=False,
    )
    op.alter_column(
        "leave_events",
        "end_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="end_date::timestamp with time zone",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "leave_events",
        "start_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        postgresql_using="start_date::date",
        nullable=False,
    )
    op.alter_column(
        "leave_events",
        "end_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        postgresql_using="end_date::date",
        nullable=False,
    )

