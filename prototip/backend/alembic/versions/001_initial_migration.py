"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создание таблицы app_roles
    op.create_table(
        'app_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_name')
    )
    
    # Создание таблицы app_users
    op.create_table(
        'app_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('login', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['role_id'], ['app_roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('login')
    )
    op.create_index(op.f('ix_app_users_id'), 'app_users', ['id'], unique=False)
    op.create_index(op.f('ix_app_users_login'), 'app_users', ['login'], unique=True)
    
    # Создание таблицы leave_events
    op.create_table(
        'leave_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('leave_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['app_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leave_events_id'), 'leave_events', ['id'], unique=False)
    
    # Создание таблицы app_configuration
    op.create_table(
        'app_configuration',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index(op.f('ix_app_configuration_id'), 'app_configuration', ['id'], unique=False)
    op.create_index(op.f('ix_app_configuration_key'), 'app_configuration', ['key'], unique=True)
    
    # Добавление начальных ролей
    op.execute("INSERT INTO app_roles (role_name) VALUES ('Admin'), ('User')")


def downgrade() -> None:
    op.drop_index(op.f('ix_app_configuration_key'), table_name='app_configuration')
    op.drop_index(op.f('ix_app_configuration_id'), table_name='app_configuration')
    op.drop_table('app_configuration')
    op.drop_index(op.f('ix_leave_events_id'), table_name='leave_events')
    op.drop_table('leave_events')
    op.drop_index(op.f('ix_app_users_login'), table_name='app_users')
    op.drop_index(op.f('ix_app_users_id'), table_name='app_users')
    op.drop_table('app_users')
    op.drop_table('app_roles')

