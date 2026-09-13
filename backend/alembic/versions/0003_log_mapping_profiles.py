"""add log_mapping_profiles and mapping_audit_logs tables

Revision ID: 0003_log_mapping_profiles
Revises: 0002_anomaly_results
Create Date: 2026-09-10 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_log_mapping_profiles'
down_revision: Union[str, None] = '0002_anomaly_results'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. log_mapping_profiles
    op.create_table(
        'log_mapping_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('vendor', sa.String(length=64), nullable=False),
        sa.Column('product', sa.String(length=64), nullable=False),
        sa.Column('device_type', sa.String(length=32), nullable=False),
        sa.Column('source_format', sa.String(length=32), nullable=False),
        sa.Column('parser_type', sa.String(length=64), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('field_mappings', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_log_mapping_profiles_name'), 'log_mapping_profiles', ['name'], unique=True)
    op.create_index(op.f('ix_log_mapping_profiles_vendor'), 'log_mapping_profiles', ['vendor'], unique=False)
    op.create_index(op.f('ix_log_mapping_profiles_status'), 'log_mapping_profiles', ['status'], unique=False)
    op.create_index('ix_mapping_profile_vendor_status', 'log_mapping_profiles', ['vendor', 'status'], unique=False)

    # 2. mapping_audit_logs
    op.create_table(
        'mapping_audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('profile_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('actor', sa.String(length=128), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['log_mapping_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mapping_audit_logs_profile_id'), 'mapping_audit_logs', ['profile_id'], unique=False)
    op.create_index(op.f('ix_mapping_audit_logs_timestamp'), 'mapping_audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mapping_audit_logs_timestamp'), table_name='mapping_audit_logs')
    op.drop_index(op.f('ix_mapping_audit_logs_profile_id'), table_name='mapping_audit_logs')
    op.drop_table('mapping_audit_logs')

    op.drop_index('ix_mapping_profile_vendor_status', table_name='log_mapping_profiles')
    op.drop_index(op.f('ix_log_mapping_profiles_status'), table_name='log_mapping_profiles')
    op.drop_index(op.f('ix_log_mapping_profiles_vendor'), table_name='log_mapping_profiles')
    op.drop_index(op.f('ix_log_mapping_profiles_name'), table_name='log_mapping_profiles')
    op.drop_table('log_mapping_profiles')
