# OmniLogix Synthetic Evaluation Dataset Catalog
**Universal Log Pre-Processing Framework (ULPF)**  
**Problem Statement:** `SIH26156` (NTRO) — *Theme: Blockchain & Cybersecurity*  
**Air-Gapped & Offline Status:** Strictly Synthetic Data (Zero PII, Zero Classified Telemetry)

---

## 1. Overview
This directory contains deterministic, synthetic perimeter telemetry datasets designed for 100% offline evaluation and validation of OmniLogix. Every file is safe for distribution and conforms to real-world vendor formats.

---

## 2. Dataset Files & Formats

| File Name | Format | Vendor / System | Scenarios Represented |
|---|---|---|---|
| `final_evaluation_dataset.json` | Master JSON Bundle | Multi-Vendor (13 records) | Auth success/failure, Deny, Malware, Scan, C2, Config change, Normal, Unknown |
| `checkpoint_sample.log` | Key-Value / Pipe | Check Point FW-1 | Drop (SSH), Reject (C2/Tor beacon), Accept (HTTPS) |
| `suricata_sample.json` | JSON (EVE) | Suricata IDS/IPS | Port scan alert, Cobalt strike beaconing, Normal flow |
| `cisco_asa_sample.log` | RFC 3164 / Syslog | Cisco ASA NGFW | Connection built, Deny 106023, Teardown |
| `fortinet_sample.log` | Key-Value Pairs | Fortinet FortiGate | Allowed traffic, UTM virus (EICAR), Admin login failed |
| `palo_alto_sample.log` | CSV | Palo Alto PAN-OS | Traffic flow, Threat vulnerability (SQLi) |
| `rfc3164_sample.log` | RFC 3164 BSD Syslog | Linux / Switch / Router | Su failure, SSH auth failed, SSH accepted, Config change |
| `rfc5424_sample.log` | RFC 5424 Structured Syslog | Enterprise Gateway | Port scan detected, MFA login success, C2 blocked |
| `keyvalue_sample.log` | Key-Value | FortiGate / Generic | Forward traffic, UTM virus block, SSH auth failure |
| `perimeter_event_sample.cef` | CEF (ArcSight) | Multi-Vendor | Threat alerts, brute force attempts |
| `perimeter_event_sample.leef` | LEEF (IBM QRadar) | Edge Defense | Authentication failure, drop events |
| `security_event_sample.json` | Structured JSON | Cloud/Host Telemetry | Access audit, privilege elevation |
| `security_event_sample.xml` | XML with CDATA | Web Application Firewall | SQLi attempt, blocked XSS, normal request |
| `network_event_sample.csv` | Delimited CSV | NetFlow / Proxy | Inbound/outbound connection statistics |
| `unknown_sample.txt` | Custom Delimited | Legacy / Unknown Device | Proprietary tokenized perimeter logs for no-code onboarding |
| `malformed_sample.log` | Malformed Streams | Corrupted Transports | Framing error resilience & corrupt field tolerance |

---

## 3. Ground-Truth Threat & Operational Coverage
1. **Successful Authentication:** RFC 5424 & RFC 3164 MFA logins.
2. **Failed Authentication:** SSH brute-force and admin password failure.
3. **Firewall Deny:** Cisco ASA `%ASA-3-106023` and Check Point drop rules.
4. **Malware Alert:** Suricata ET TROJAN Cobalt Strike beaconing & FortiGate UTM virus block.
5. **Port Scan:** Reconnaissance sweeps across ports 20-1024.
6. **Suspicious Outbound Connection:** C2 / Tor exit node connection rejection.
7. **Configuration Change:** Cisco IOS interface IP reconfiguration.
8. **Normal Traffic:** Proxy HTTPS flows and TCP teardown records.
9. **Unknown Vendor Event:** Tokenized unknown stream onboarding without code modification.
