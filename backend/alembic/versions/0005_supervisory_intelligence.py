"""add supervisory intelligence tables

Revision ID: 0005_supervisory_intelligence
Revises: 0004_security_analytics
Create Date: 2026-09-11 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_supervisory_intelligence'
down_revision: Union[str, None] = '0004_security_analytics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. entity_assessments
    op.create_table(
        'entity_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('entity_name', sa.String(length=128), nullable=False),
        sa.Column('assessment_period', sa.String(length=64), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('detection_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('investigation_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('escalation_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('operational_discipline_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('monitoring_coverage_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('data_quality_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cyber_resilience_indicator', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('risk_category', sa.String(length=32), nullable=False, server_default='INSUFFICIENT_EVIDENCE'),
        sa.Column('trend', sa.String(length=32), nullable=False, server_default='INSUFFICIENT_EVIDENCE'),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_entity_assessments_entity_id', 'entity_assessments', ['entity_id'])
    op.create_index('ix_entity_assessments_risk_category', 'entity_assessments', ['risk_category'])
    op.create_index('ix_entity_assessments_entity_period', 'entity_assessments', ['entity_id', 'assessment_period'])

    # 2. capability_assessments
    op.create_table(
        'capability_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('capability_name', sa.String(length=64), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('indicators', sa.JSON(), nullable=False),
        sa.Column('positive_signals', sa.JSON(), nullable=False),
        sa.Column('negative_signals', sa.JSON(), nullable=False),
        sa.Column('supporting_evidence', sa.JSON(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['entity_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_capability_assessments_assessment_id', 'capability_assessments', ['assessment_id'])
    op.create_index('ix_capability_assessments_capability_name', 'capability_assessments', ['capability_name'])

    # 3. supervisory_indicators
    op.create_table(
        'supervisory_indicators',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('indicator_type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('time_period', sa.String(length=64), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('recommended_manual_review', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_supervisory_indicators_entity_id', 'supervisory_indicators', ['entity_id'])
    op.create_index('ix_supervisory_indicators_indicator_type', 'supervisory_indicators', ['indicator_type'])
    op.create_index('ix_supervisory_indicators_severity', 'supervisory_indicators', ['severity'])
    op.create_index('ix_supervisory_indicators_status', 'supervisory_indicators', ['status'])

    # 4. review_samples
    op.create_table(
        'review_samples',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('raw_event_id', sa.String(length=64), nullable=False),
        sa.Column('priority_label', sa.String(length=32), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('reasons', sa.JSON(), nullable=False),
        sa.Column('capability_tags', sa.JSON(), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('anomaly_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('closure_time_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_review_samples_entity_id', 'review_samples', ['entity_id'])
    op.create_index('ix_review_samples_event_id', 'review_samples', ['event_id'])
    op.create_index('ix_review_samples_raw_event_id', 'review_samples', ['raw_event_id'])
    op.create_index('ix_review_samples_priority_label', 'review_samples', ['priority_label'])

    # 5. supervisory_reviews
    op.create_table(
        'supervisory_reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('indicator_id', sa.String(length=36), nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=False),
        sa.Column('previous_status', sa.String(length=32), nullable=False),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['indicator_id'], ['supervisory_indicators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_supervisory_reviews_indicator_id', 'supervisory_reviews', ['indicator_id'])


def downgrade() -> None:
    op.drop_table('supervisory_reviews')
    op.drop_table('review_samples')
    op.drop_table('supervisory_indicators')
    op.drop_table('capability_assessments')
    op.drop_table('entity_assessments')
