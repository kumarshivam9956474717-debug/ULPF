from app.db.seed import seed_database
from app.models.log_source import LogSource
from app.models.parser import Parser, ParserVersion


def test_seed_data_execution(db_session):
    """
    Test seed script execution and verify:
    - 3 log sources
    - 3 parsers
    - 2 parser versions
    """
    seed_database(db=db_session)

    # 1. Verify 3 log sources
    sources = db_session.query(LogSource).all()
    assert len(sources) == 3
    source_ids = {s.source_id for s in sources}
    assert "cisco-asa-edge-01" in source_ids
    assert "panos-ngfw-hq-01" in source_ids
    assert "fortigate-utm-branch-01" in source_ids

    # 2. Verify 3 parsers
    parsers = db_session.query(Parser).all()
    assert len(parsers) == 3
    parser_ids = {p.parser_id for p in parsers}
    assert "cisco_asa_syslog" in parser_ids
    assert "paloalto_panos_traffic" in parser_ids
    assert "fortinet_fortios_utm" in parser_ids

    # 3. Verify 2 parser versions
    versions = db_session.query(ParserVersion).all()
    assert len(versions) == 2
    ver_tuples = {(v.parser_id, v.version) for v in versions}
    assert ("cisco_asa_syslog", "1.0.0") in ver_tuples
    assert ("cisco_asa_syslog", "1.1.0") in ver_tuples

    # Verify idempotency (running seed again does not duplicate)
    seed_database(db=db_session)
    assert db_session.query(LogSource).count() == 3
    assert db_session.query(Parser).count() == 3
    assert db_session.query(ParserVersion).count() == 2
