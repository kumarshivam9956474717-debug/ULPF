from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.processing_run import ProcessingRun
from app.services.pipeline import PipelineService


def test_pipeline_successful_processing(db_session):
    raw_payload = '{"timestamp": "2026-09-10T09:30:00Z", "src_ip": "10.0.1.5", "dst_ip": "192.168.1.1", "action": "allow", "vendor": "Fortinet"}'
    result = PipelineService.process_event(raw_payload=raw_payload, db=db_session)

    assert result.success is True
    assert result.raw_event_id is not None
    assert result.normalized_event_id is not None
    assert result.detected_format == "json"
    assert result.validation_status in ("valid", "warning")

    # Verify persisted in database
    raw = db_session.query(RawEvent).filter_by(raw_event_id=result.raw_event_id).first()
    assert raw is not None
    assert raw.raw_payload == raw_payload

    norm = db_session.query(NormalizedEvent).filter_by(event_id=result.normalized_event_id).first()
    assert norm is not None
    assert norm.source_ip == "10.0.1.5"
    assert norm.raw_event_id == raw.raw_event_id


def test_pipeline_failed_parsing_preserves_raw_event(db_session):
    """
    Architecture Principle 1 & Prompt Requirement:
    If parsing fails:
    - raw event MUST still remain stored
    - failure must be recorded
    - no raw data may be discarded
    """
    corrupted_payload = "CORRUPT_UNKNOWN_PAYLOAD_WITHOUT_PARSER_12345"
    result = PipelineService.process_event(raw_payload=corrupted_payload, db=db_session)

    assert result.success is False
    assert result.raw_event_id is not None
    assert result.normalized_event_id is None
    assert len(result.errors) > 0

    # Verify the raw event was strictly persisted in database!
    raw = db_session.query(RawEvent).filter_by(raw_event_id=result.raw_event_id).first()
    assert raw is not None
    assert raw.raw_payload == corrupted_payload
    assert raw.payload_hash_sha256 is not None


def test_pipeline_batch_processing_and_run_metrics(db_session):
    batch = [
        '<166>Sep 10 09:30:00 asa-01 %ASA-6-302013: Built inbound TCP connection',
        '{"src_ip": "10.0.0.1", "dst_ip": "10.0.0.2", "action": "deny"}',
        'CEF:0|Vendor|Product|1.0|100|Name|5|src=1.1.1.1 dst=2.2.2.2',
        'UNKNOWN_CORRUPT_RECORD_001'
    ]

    batch_result = PipelineService.process_batch(events=batch, db=db_session, source_id="batch-source-01")

    assert batch_result.total_received == 4
    assert batch_result.total_parsed == 4
    assert batch_result.total_normalized == 3
    assert batch_result.total_failed == 1
    assert "syslog" in batch_result.format_statistics or "json" in batch_result.format_statistics

    # Verify ProcessingRun record created in database
    run = db_session.query(ProcessingRun).filter_by(run_id=batch_result.processing_run_id).first()
    assert run is not None
    assert run.records_received == 4
    assert run.records_normalized == 3
    assert run.records_failed == 1
    assert run.status == "completed_with_errors"
