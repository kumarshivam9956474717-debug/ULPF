import asyncio
import datetime
import os
import ssl
import tempfile
import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.services.syslog.tls_listener import TLSListener
from app.services.syslog.metrics import syslog_metrics


@pytest.fixture(scope="module")
def tls_certificates():
    """
    Generates a temporary self-signed RSA certificate and private key for testing TLS Syslog.
    """
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ULPF-Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ip) for ip in [__import__("ipaddress").ip_address("127.0.0.1")]]),
            critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )

    with tempfile.NamedTemporaryFile(suffix=".crt", delete=False) as cert_f, \
         tempfile.NamedTemporaryFile(suffix=".key", delete=False) as key_f:
        cert_f.write(cert.public_bytes(serialization.Encoding.PEM))
        cert_f.flush()
        key_f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )
        key_f.flush()

        cert_path = cert_f.name
        key_path = key_f.name

    yield cert_path, key_path

    # Cleanup
    if os.path.exists(cert_path):
        os.remove(cert_path)
    if os.path.exists(key_path):
        os.remove(key_path)


@pytest.mark.anyio
async def test_tls_syslog_listener_and_client(tls_certificates):
    cert_path, key_path = tls_certificates
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19530

    listener = TLSListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        certfile=cert_path,
        keyfile=key_path,
        max_bytes=65536
    )

    await listener.start()
    assert listener.is_running is True

    # Client SSL context
    client_ssl = ssl.create_default_context()
    client_ssl.check_hostname = False
    client_ssl.verify_mode = ssl.CERT_NONE  # for self-signed test cert

    reader, writer = await asyncio.open_connection("127.0.0.1", test_port, ssl=client_ssl)
    try:
        tls_msg = "<134>1 2026-09-10T10:05:00Z firewall01 vpn 1024 ID99 TLS encrypted Syslog\n"
        writer.write(tls_msg.encode("utf-8"))
        await writer.drain()

        received = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert received.transport == "tls"
        assert received.remote_address == "127.0.0.1"
        assert b"TLS encrypted Syslog" in received.payload
        assert syslog_metrics.messages_received == 1
    finally:
        writer.close()
        await writer.wait_closed()
        await listener.stop()

    assert listener.is_running is False
