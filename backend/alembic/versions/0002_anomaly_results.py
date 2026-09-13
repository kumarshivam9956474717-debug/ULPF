"""add anomaly_results table

Revision ID: 0002_anomaly_results
Revises: 0001_initial_persistence_layer
Create Date: 2026-09-10 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_anomaly_results'
down_revision: Union[str, None] = '0001_initial_persistence_layer'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'anomaly_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False),
        sa.Column('anomaly_score', sa.Float(), nullable=False),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False),
        sa.Column('feature_summary', sa.JSON(), nullable=True),
        sa.Column('explanation', sa.JSON(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['normalized_events.event_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anomaly_results_event_id'), 'anomaly_results', ['event_id'], unique=False)
    op.create_index(op.f('ix_anomaly_results_is_anomaly'), 'anomaly_results', ['is_anomaly'], unique=False)
    op.create_index(op.f('ix_anomaly_results_detected_at'), 'anomaly_results', ['detected_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_anomaly_results_detected_at'), table_name='anomaly_results')
    op.drop_index(op.f('ix_anomaly_results_is_anomaly'), table_name='anomaly_results')
    op.drop_index(op.f('ix_anomaly_results_event_id'), table_name='anomaly_results')
    op.drop_table('anomaly_results')
