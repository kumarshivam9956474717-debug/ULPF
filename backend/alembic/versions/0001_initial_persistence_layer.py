"""initial persistence layer

Revision ID: 0001_initial_persistence_layer
Revises: 
Create Date: 2026-09-10 09:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_persistence_layer'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. log_sources table
    op.create_table(
        'log_sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('vendor', sa.String(length=64), nullable=True),
        sa.Column('product', sa.String(length=64), nullable=True),
        sa.Column('device_type', sa.String(length=32), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('source_format', sa.String(length=32), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )
    op.create_index('ix_log_sources_source_id', 'log_sources', ['source_id'])
    op.create_index('ix_log_sources_vendor', 'log_sources', ['vendor'])
    op.create_index('ix_log_sources_device_type', 'log_sources', ['device_type'])
    op.create_index('ix_log_sources_hostname', 'log_sources', ['hostname'])

    # 2. parsers table
    op.create_table(
        'parsers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('parser_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('vendor', sa.String(length=64), nullable=False),
        sa.Column('product', sa.String(length=64), nullable=True),
        sa.Column('device_type', sa.String(length=32), nullable=True),
        sa.Column('supported_formats', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('parser_id')
    )
    op.create_index('ix_parsers_parser_id', 'parsers', ['parser_id'])
    op.create_index('ix_parsers_vendor', 'parsers', ['vendor'])

    # 3. parser_versions table
    op.create_table(
        'parser_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('parser_id', sa.String(length=64), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['parser_id'], ['parsers.parser_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_parser_versions_parser_id', 'parser_versions', ['parser_id'])

    # 4. processing_runs table
    op.create_table(
        'processing_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('records_received', sa.Integer(), nullable=False),
        sa.Column('records_parsed', sa.Integer(), nullable=False),
        sa.Column('records_normalized', sa.Integer(), nullable=False),
        sa.Column('records_failed', sa.Integer(), nullable=False),
        sa.Column('processing_time_ms', sa.Integer(), nullable=False),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['log_sources.source_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )
    op.create_index('ix_processing_runs_run_id', 'processing_runs', ['run_id'])
    op.create_index('ix_processing_runs_source_id', 'processing_runs', ['source_id'])

    # 5. raw_events table
    op.create_table(
        'raw_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('raw_event_id', sa.String(length=64), nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('raw_payload', sa.Text(), nullable=False),
        sa.Column('payload_encoding', sa.String(length=16), nullable=False),
        sa.Column('payload_hash_sha256', sa.String(length=64), nullable=False),
        sa.Column('source_format', sa.String(length=32), nullable=True),
        sa.Column('ingestion_batch_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ingestion_batch_id'], ['processing_runs.run_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['log_sources.source_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('raw_event_id')
    )
    op.create_index('ix_raw_events_raw_event_id', 'raw_events', ['raw_event_id'])
    op.create_index('ix_raw_events_source_id', 'raw_events', ['source_id'])
    op.create_index('ix_raw_events_received_at', 'raw_events', ['received_at'])
    op.create_index('ix_raw_events_payload_hash_sha256', 'raw_events', ['payload_hash_sha256'])
    op.create_index('ix_raw_events_ingestion_batch_id', 'raw_events', ['ingestion_batch_id'])

    # 6. normalized_events table
    op.create_table(
        'normalized_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('source_event_id', sa.String(length=128), nullable=True),
        sa.Column('raw_event_id', sa.String(length=64), nullable=False),
        sa.Column('schema_version', sa.String(length=16), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timezone', sa.String(length=32), nullable=True),
        sa.Column('vendor', sa.String(length=64), nullable=True),
        sa.Column('product', sa.String(length=64), nullable=True),
        sa.Column('device_type', sa.String(length=32), nullable=True),
        sa.Column('device_id', sa.String(length=128), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('source_format', sa.String(length=32), nullable=True),
        sa.Column('source_ip', sa.String(length=45), nullable=True),
        sa.Column('source_port', sa.Integer(), nullable=True),
        sa.Column('destination_ip', sa.String(length=45), nullable=True),
        sa.Column('destination_port', sa.Integer(), nullable=True),
        sa.Column('protocol', sa.String(length=32), nullable=True),
        sa.Column('username', sa.String(length=128), nullable=True),
        sa.Column('user_id', sa.String(length=128), nullable=True),
        sa.Column('authentication_method', sa.String(length=64), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=32), nullable=True),
        sa.Column('outcome', sa.String(length=32), nullable=True),
        sa.Column('severity', sa.String(length=32), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('subcategory', sa.String(length=64), nullable=True),
        sa.Column('interface', sa.String(length=64), nullable=True),
        sa.Column('direction', sa.String(length=32), nullable=True),
        sa.Column('zone', sa.String(length=64), nullable=True),
        sa.Column('threat_name', sa.String(length=255), nullable=True),
        sa.Column('threat_id', sa.String(length=128), nullable=True),
        sa.Column('signature_id', sa.String(length=128), nullable=True),
        sa.Column('rule_id', sa.String(length=128), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('custom_fields', sa.JSON(), nullable=True),
        sa.Column('parser_id', sa.String(length=64), nullable=True),
        sa.Column('parser_version', sa.String(length=32), nullable=True),
        sa.Column('normalization_version', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['raw_event_id'], ['raw_events.raw_event_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('ix_normalized_events_event_id', 'normalized_events', ['event_id'])
    op.create_index('ix_normalized_events_raw_event_id', 'normalized_events', ['raw_event_id'])
    op.create_index('ix_normalized_events_timestamp', 'normalized_events', ['timestamp'])
    op.create_index('ix_normalized_events_vendor', 'normalized_events', ['vendor'])
    op.create_index('ix_normalized_events_device_type', 'normalized_events', ['device_type'])
    op.create_index('ix_normalized_events_event_type', 'normalized_events', ['event_type'])
    op.create_index('ix_normalized_events_severity', 'normalized_events', ['severity'])
    op.create_index('ix_normalized_events_source_ip', 'normalized_events', ['source_ip'])
    op.create_index('ix_normalized_events_destination_ip', 'normalized_events', ['destination_ip'])
    op.create_index('ix_normalized_events_src_dst_ip', 'normalized_events', ['source_ip', 'destination_ip'])
    op.create_index('ix_normalized_events_ts_vendor', 'normalized_events', ['timestamp', 'vendor'])

    # 7. validation_results table
    op.create_table(
        'validation_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('normalized_event_id', sa.String(length=64), nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=True),
        sa.Column('validation_status', sa.String(length=32), nullable=False),
        sa.Column('validation_errors', sa.JSON(), nullable=False),
        sa.Column('validation_warnings', sa.JSON(), nullable=False),
        sa.Column('validation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['normalized_event_id'], ['normalized_events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['processing_runs.run_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_results_normalized_event_id', 'validation_results', ['normalized_event_id'])
    op.create_index('ix_validation_results_run_id', 'validation_results', ['run_id'])


def downgrade() -> None:
    op.drop_table('validation_results')
    op.drop_table('normalized_events')
    op.drop_table('raw_events')
    op.drop_table('processing_runs')
    op.drop_table('parser_versions')
    op.drop_table('parsers')
    op.drop_table('log_sources')
