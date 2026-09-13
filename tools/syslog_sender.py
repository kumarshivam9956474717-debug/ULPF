#!/usr/bin/env python3
"""
ULPF Offline Syslog Sender Test Utility
Generates and transmits synthetic Syslog messages over UDP, TCP, or TLS
to validate live network ingestion without requiring external infrastructure.
"""

import argparse
import socket
import ssl
import sys
import time
from typing import List

# Synthetic log message templates for diverse perimeter network sources
SAMPLE_LOGS = {
    "cisco": (
        "%ASA-6-302013: Built outbound TCP connection 987654 for "
        "inside:192.168.1.100/49210 (192.168.1.100/49210) to "
        "outside:198.51.100.25/443 (198.51.100.25/443)"
    ),
    "fortinet": (
        "date=2026-09-10 time=09:30:00 devname=\"FGT-PERIMETER-01\" devid=\"FGT60D1234567890\" "
        "type=\"traffic\" subtype=\"forward\" level=\"notice\" action=\"accept\" "
        "srcip=10.0.1.50 dstip=203.0.113.15 srcport=54321 dstport=80 proto=6 "
        "service=\"HTTP\" app=\"Web.Browsing\" msg=\"Traffic accepted by firewall policy\""
    ),
    "palo_alto": (
        "1,2026/09/10 09:35:12,001801000001,TRAFFIC,drop,1,2026/09/10 09:35:12,"
        "192.168.10.45,198.51.100.99,0.0.0.0,0.0.0.0,RULE-PERIMETER-DROP,,,ping,vsys1,"
        "trust,untrust,ethernet1/2,ethernet1/1,log-forwarding,2026/09/10 09:35:12,0,1,56,84,0,0,0,0,0x0,icmp,deny"
    ),
    "rfc5424": (
        "<165>1 2026-09-10T09:40:00.123Z perimeter-edge-gw.local edge-guard 49152 ID47 "
        "[exampleSDID@32473 iut=\"3\" eventSource=\"EdgeFilter\" eventID=\"1011\"] "
        "Unauthorized port probe detected and dropped from 203.0.113.88 to port 22"
    ),
    "rfc3164": (
        "<34>Sep 10 09:42:15 edge-fw01 kernel: [FIREWALL_DROP] "
        "IN=eth0 OUT= MAC=00:11:22:33:44:55:66:77:88:99:aa:bb:08:00 "
        "SRC=198.51.100.77 DST=192.168.1.1 LEN=40 TOS=0x00 PREC=0x00 TTL=243 ID=54321 PROTO=TCP SPT=44521 DPT=23 WINDOW=1024 RES=0x00 SYN URGP=0"
    ),
    "malformed": (
        "INVALID_HEADER_GARBAGE_NO_TIMESTAMP_RANDOM_BYTES_%%%&&&***###"
    ),
    "oversized": (
        "<13>1 2026-09-10T09:45:00Z test-box app - - - " + ("A" * 70000)
    )
}


def send_udp(host: str, port: int, messages: List[str], interval: float) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sent = 0
    try:
        for msg in messages:
            data = msg.encode("utf-8")
            sock.sendto(data, (host, port))
            sent += 1
            if interval > 0:
                time.sleep(interval)
    finally:
        sock.close()
    return sent


def send_tcp(
    host: str,
    port: int,
    messages: List[str],
    interval: float,
    framing: str = "newline",
    use_tls: bool = False,
    tls_insecure: bool = False
) -> int:
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = raw_sock

    if use_tls:
        context = ssl.create_default_context()
        if tls_insecure:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        sock = context.wrap_socket(raw_sock, server_hostname=host if not tls_insecure else None)

    sock.connect((host, port))
    sent = 0
    try:
        for msg in messages:
            msg_bytes = msg.encode("utf-8")
            if framing == "octet":
                # RFC 6587 octet-counted: <length> <message>
                frame = f"{len(msg_bytes)} ".encode("ascii") + msg_bytes
            else:
                # Newline-delimited
                frame = msg_bytes + b"\n"

            sock.sendall(frame)
            sent += 1
            if interval > 0:
                time.sleep(interval)
    finally:
        sock.close()
    return sent


def main():
    parser = argparse.ArgumentParser(description="ULPF Live Syslog Sender Utility")
    parser.add_argument("--protocol", choices=["udp", "tcp", "tls"], default="udp", help="Transport protocol")
    parser.add_argument("--host", default="127.0.0.1", help="Target host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Target port (default: 1514 for udp/tcp, 16514 for tls)")
    parser.add_argument("--count", type=int, default=1, help="Number of messages to send (default: 1)")
    parser.add_argument("--interval", type=float, default=0.0, help="Delay between messages in seconds (default: 0.0)")
    parser.add_argument("--sample", choices=list(SAMPLE_LOGS.keys()), default="cisco", help="Synthetic sample type")
    parser.add_argument("--message", type=str, default=None, help="Custom message payload override")
    parser.add_argument("--framing", choices=["newline", "octet"], default="newline", help="TCP/TLS framing")
    parser.add_argument("--tls-insecure", action="store_true", help="Disable TLS certificate verification for testing")

    args = parser.parse_args()

    port = args.port
    if port is None:
        port = 16514 if args.protocol == "tls" else 1514

    base_message = args.message if args.message else SAMPLE_LOGS[args.sample]
    messages = [base_message] * args.count

    print(f"[*] Sending {args.count} {args.sample} message(s) to {args.protocol.upper()} {args.host}:{port}...")
    start = time.perf_counter()

    if args.protocol == "udp":
        sent = send_udp(args.host, port, messages, args.interval)
    elif args.protocol == "tcp":
        sent = send_tcp(args.host, port, messages, args.interval, framing=args.framing, use_tls=False)
    elif args.protocol == "tls":
        sent = send_tcp(args.host, port, messages, args.interval, framing=args.framing, use_tls=True, tls_insecure=args.tls_insecure)
    else:
        print(f"[!] Unknown protocol: {args.protocol}")
        sys.exit(1)

    elapsed = time.perf_counter() - start
    rate = sent / elapsed if elapsed > 0 else 0
    print(f"[+] Successfully transmitted {sent} message(s) in {elapsed:.4f}s ({rate:.1f} msgs/sec).")


if __name__ == "__main__":
    main()
