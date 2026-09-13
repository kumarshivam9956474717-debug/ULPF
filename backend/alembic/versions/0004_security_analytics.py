"""add analytics_findings and source_baselines tables

Revision ID: 0004_security_analytics
Revises: 0003_log_mapping_profiles
Create Date: 2026-09-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_security_analytics'
down_revision: Union[str, None] = '0003_log_mapping_profiles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. analytics_findings
    op.create_table(
        'analytics_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('finding_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=False),
        sa.Column('priority_category', sa.String(length=32), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=True),
        sa.Column('event_count', sa.Integer(), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('reviewed_by', sa.String(length=128), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_findings_finding_type'), 'analytics_findings', ['finding_type'], unique=False)
    op.create_index(op.f('ix_analytics_findings_severity'), 'analytics_findings', ['severity'], unique=False)
    op.create_index(op.f('ix_analytics_findings_priority_score'), 'analytics_findings', ['priority_score'], unique=False)
    op.create_index(op.f('ix_analytics_findings_priority_category'), 'analytics_findings', ['priority_category'], unique=False)
    op.create_index(op.f('ix_analytics_findings_source_id'), 'analytics_findings', ['source_id'], unique=False)
    op.create_index(op.f('ix_analytics_findings_first_seen'), 'analytics_findings', ['first_seen'], unique=False)
    op.create_index(op.f('ix_analytics_findings_last_seen'), 'analytics_findings', ['last_seen'], unique=False)
    op.create_index(op.f('ix_analytics_findings_status'), 'analytics_findings', ['status'], unique=False)
    op.create_index('ix_analytics_findings_type_status', 'analytics_findings', ['finding_type', 'status'], unique=False)
    op.create_index('ix_analytics_findings_priority_status', 'analytics_findings', ['priority_score', 'status'], unique=False)

    # 2. source_baselines
    op.create_table(
        'source_baselines',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('avg_hourly_volume', sa.Float(), nullable=False),
        sa.Column('median_hourly_volume', sa.Float(), nullable=False),
        sa.Column('stddev_hourly_volume', sa.Float(), nullable=False),
        sa.Column('severity_distribution', sa.JSON(), nullable=False),
        sa.Column('protocol_distribution', sa.JSON(), nullable=False),
        sa.Column('action_distribution', sa.JSON(), nullable=False),
        sa.Column('sample_hours_count', sa.Integer(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_source_baselines_source_id'), 'source_baselines', ['source_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_source_baselines_source_id'), table_name='source_baselines')
    op.drop_table('source_baselines')

    op.drop_index('ix_analytics_findings_priority_status', table_name='analytics_findings')
    op.drop_index('ix_analytics_findings_type_status', table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_status'), table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_last_seen'), table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_first_seen'), table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_source_id'), table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_priority_category'), table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_priority_score'), table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_severity'), table_name='analytics_findings')
    op.drop_index(op.f('ix_analytics_findings_finding_type'), table_name='analytics_findings')
    op.drop_table('analytics_findings')
