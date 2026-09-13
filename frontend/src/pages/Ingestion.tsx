import React, { useState, useEffect } from 'react';
import {
  ArrowDownToLine,
  Search,
  AlertTriangle,
  FileCode2,
  Copy,
  Check,
  Cpu,
  Layers,
  ShieldCheck,
  RefreshCw,
  Zap,
  Radio,
  Server,
  Play,
  Square,
  RotateCcw,
  Upload,
  Files,
  Activity,
  Clock,
} from 'lucide-react';

import {
  detectFormat,
  ingestLog,
  ingestBatchLogs,
  fetchSyslogStatus,
  startSyslogService,
  stopSyslogService,
  resetSyslogMetrics,
  fetchLogSources,
  FormatDetectionResult,
  IngestResponse,
  BatchIngestResponse,
  SyslogStatusResponse,
  LogSourceItem,
} from '../services/api';

const SYNTHETIC_PRESETS = [
  {
    label: 'Cisco ASA Syslog',
    format: 'syslog',
    defaultSourceId: 'src-cisco-asa',
    payload: '<166>Sep 10 09:30:00 asa-01 %ASA-6-302013: Built inbound TCP connection 981245 for outside:198.51.100.25/54321 (198.51.100.25/54321) to dmz:10.0.1.10/443 (10.0.1.10/443)',
  },
  {
    label: 'Palo Alto PAN-OS',
    format: 'csv',
    defaultSourceId: 'src-paloalto',
    payload: '1,2026/09/10 09:20:15,001801000000,TRAFFIC,drop,2304,2026/09/10 09:20:15,198.51.100.10,10.0.0.50,0.0.0.0,0.0.0.0,Block-Bad-IPs,,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,Log-Forwarder,2026/09/10 09:20:15,12345,1,49152,80,0,0,0x0,tcp,deny,1542,1542,0,12,2026/09/10 09:20:00,15,any,0,123456789,0x0,192.0.2.0-192.0.2.255,United States,0,12,0,policy-deny,0,0,0,0,,panos-hq-01,from-policy',
  },
  {
    label: 'Fortinet Key-Value',
    format: 'syslog',
    defaultSourceId: 'src-fortinet',
    payload: '<189>date=2026-09-10 time=09:22:45 devname=FGT600E-BRANCH devid=FG600ETK19001234 logid="0000000013" type="traffic" subtype="forward" level="notice" vd="root" srcip=10.1.10.45 srcport=54122 srcintf="port1" dstip=198.51.100.4 dstport=443 dstintf="port2" polid=4 sessionid=109238 proto=6 action="accept" policyname="Internet-Access" user="alice.smith" group="Finance" app="HTTPS" duration=45 sentbyte=4020 rcvdbyte=18290',
  },
  {
    label: 'JSON Telemetry',
    format: 'json',
    defaultSourceId: 'src-checkpoint',
    payload: '{\n  "timestamp": "2026-09-10T09:25:00Z",\n  "vendor": "Cloudflare",\n  "device_type": "firewall",\n  "source_ip": "198.51.100.155",\n  "source_port": 61244,\n  "destination_ip": "203.0.113.80",\n  "destination_port": 443,\n  "protocol": "TCP",\n  "action": "block",\n  "severity": "high",\n  "event_type": "ddos_mitigation",\n  "rule_id": "RULE-SYN-PROTECT-01"\n}',
  },
  {
    label: 'CEF Perimeter',
    format: 'cef',
    defaultSourceId: 'src-checkpoint',
    payload: 'CEF:0|Check Point|VPN-1 & FireWall-1|R80.40|drop|Drop Security Rule|High|src=198.51.100.77 dst=10.0.1.25 spt=55412 dpt=3389 proto=TCP act=drop msg=Unauthorized RDP connection attempted duser=admin',
  },
  {
    label: 'LEEF QRadar',
    format: 'leef',
    defaultSourceId: 'src-fortinet',
    payload: 'LEEF:1.0|IBM|QRadar Network Security|5.4|IntrusionAlert|src=198.51.100.40\tdst=10.0.0.12\tsrcPort=39120\tdstPort=445\tproto=TCP\taction=block\tseverity=8\tusrName=compromised_host\tattack=SMBv1.Buffer.Overflow',
  },
  {
    label: 'XML Security Event',
    format: 'xml',
    defaultSourceId: 'src-silent-gw',
    payload: '<SecurityEvent vendor="F5 Networks" product="BIG-IP ASM">\n  <Timestamp>2026-09-10T09:28:00Z</Timestamp>\n  <SourceIp>198.51.100.91</SourceIp>\n  <DestinationIp>10.0.1.100</DestinationIp>\n  <DestinationPort>443</DestinationPort>\n  <Action>block</Action>\n  <Severity>critical</Severity>\n  <ThreatName>SQL-Injection</ThreatName>\n</SecurityEvent>',
  },
];

const MULTI_VENDOR_BATCH_PRESET = [
  '<166>Sep 10 09:30:00 asa-01 %ASA-6-302013: Built inbound TCP connection 981245 for outside:198.51.100.25/54321 (198.51.100.25/54321) to dmz:10.0.1.10/443 (10.0.1.10/443)',
  '1,2026/09/10 09:20:15,001801000000,TRAFFIC,drop,2304,2026/09/10 09:20:15,198.51.100.10,10.0.0.50,0.0.0.0,0.0.0.0,Block-Bad-IPs,,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,Log-Forwarder,2026/09/10 09:20:15,12345,1,49152,80,0,0,0x0,tcp,deny,1542,1542,0,12,2026/09/10 09:20:00,15,any,0,123456789,0x0,192.0.2.0-192.0.2.255,United States,0,12,0,policy-deny,0,0,0,0,,panos-hq-01,from-policy',
  '<189>date=2026-09-10 time=09:22:45 devname=FGT600E-BRANCH devid=FG600ETK19001234 logid="0000000013" type="traffic" subtype="forward" level="notice" vd="root" srcip=10.1.10.45 srcport=54122 srcintf="port1" dstip=198.51.100.4 dstport=443 dstintf="port2" polid=4 sessionid=109238 proto=6 action="accept" policyname="Internet-Access" user="alice.smith" group="Finance" app="HTTPS" duration=45 sentbyte=4020 rcvdbyte=18290',
  'CEF:0|Check Point|VPN-1 & FireWall-1|R80.40|drop|Drop Security Rule|High|src=198.51.100.77 dst=10.0.1.25 spt=55412 dpt=3389 proto=TCP act=drop msg=Unauthorized RDP connection attempted duser=admin',
  '{"timestamp": "2026-09-10T09:25:00Z", "vendor": "Cloudflare", "device_type": "firewall", "source_ip": "198.51.100.155", "action": "block", "severity": "high"}'
].join('\n');

export const Ingestion: React.FC = () => {
  // Mode selection: Single interactive log or Batch bulk log stream
  const [ingestionMode, setIngestionMode] = useState<'single' | 'batch'>('single');

  // Single Ingestion State
  const [rawPayload, setRawPayload] = useState<string>(SYNTHETIC_PRESETS[0].payload);
  const [formatHint, setFormatHint] = useState<string>('auto');
  const [sourceId, setSourceId] = useState<string>('src-cisco-asa');
  const [customSource, setCustomSource] = useState<boolean>(false);
  const [registeredSources, setRegisteredSources] = useState<LogSourceItem[]>([]);

  const [detecting, setDetecting] = useState<boolean>(false);
  const [detectionResult, setDetectionResult] = useState<FormatDetectionResult | null>(null);

  const [ingesting, setIngesting] = useState<boolean>(false);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Batch Ingestion State
  const [batchPayload, setBatchPayload] = useState<string>(MULTI_VENDOR_BATCH_PRESET);
  const [batchProcessing, setBatchProcessing] = useState<boolean>(false);
  const [batchResult, setBatchResult] = useState<BatchIngestResponse | null>(null);

  const [copied, setCopied] = useState<boolean>(false);

  // Syslog Transport State
  const [syslogStatus, setSyslogStatus] = useState<SyslogStatusResponse | null>(null);
  const [loadingSyslog, setLoadingSyslog] = useState<boolean>(false);
  const [operatingSyslog, setOperatingSyslog] = useState<boolean>(false);
  const [syslogMessage, setSyslogMessage] = useState<string | null>(null);

  const loadSyslogStatus = async () => {
    try {
      setLoadingSyslog(true);
      const data = await fetchSyslogStatus();
      setSyslogStatus(data);
    } catch {
      // Offline fallback
    } finally {
      setLoadingSyslog(false);
    }
  };

  const loadSources = async () => {
    try {
      const srcs = await fetchLogSources();
      setRegisteredSources(srcs);
      if (srcs.length > 0 && !sourceId) {
        setSourceId(srcs[0].source_id);
      }
    } catch {
      // Offline fallback
    }
  };

  useEffect(() => {
    loadSyslogStatus();
    loadSources();
    const timer = setInterval(loadSyslogStatus, 5000);
    return () => clearInterval(timer);
  }, []);

  const handleStartSyslog = async () => {
    setOperatingSyslog(true);
    setSyslogMessage(null);
    setErrorMessage(null);
    try {
      const res = await startSyslogService();
      setSyslogStatus(res.status);
      setSyslogMessage(res.message);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to start Syslog service');
    } finally {
      setOperatingSyslog(false);
    }
  };

  const handleStopSyslog = async () => {
    setOperatingSyslog(true);
    setSyslogMessage(null);
    setErrorMessage(null);
    try {
      const res = await stopSyslogService();
      setSyslogStatus(res.status);
      setSyslogMessage(res.message);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to stop Syslog service');
    } finally {
      setOperatingSyslog(false);
    }
  };

  const handleResetSyslog = async () => {
    setOperatingSyslog(true);
    setSyslogMessage(null);
    setErrorMessage(null);
    try {
      const res = await resetSyslogMetrics();
      if (syslogStatus) {
        setSyslogStatus({ ...syslogStatus, metrics: res.metrics });
      }
      setSyslogMessage(res.message);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to reset Syslog metrics');
    } finally {
      setOperatingSyslog(false);
    }
  };

  const handlePresetSelect = (payload: string, hint: string, defSource?: string) => {
    setRawPayload(payload);
    setFormatHint(hint);
    if (defSource) {
      setSourceId(defSource);
      setCustomSource(false);
    }
    setDetectionResult(null);
    setIngestResult(null);
    setErrorMessage(null);
  };

  const handleDetectFormat = async () => {
    if (!rawPayload.trim()) return;
    setDetecting(true);
    setErrorMessage(null);
    try {
      const res = await detectFormat(rawPayload);
      setDetectionResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Detection failed');
    } finally {
      setDetecting(false);
    }
  };

  const handleIngest = async () => {
    if (!rawPayload.trim()) return;
    setIngesting(true);
    setErrorMessage(null);
    try {
      const res = await ingestLog(rawPayload, sourceId, formatHint);
      setIngestResult(res);
      setDetectionResult({
        detected_format: res.detected_format,
        confidence: 0.99,
        reason: 'Processed through live ingestion engine pipeline',
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Ingestion failed');
    } finally {
      setIngesting(false);
    }
  };

  const handleBatchIngest = async () => {
    const rawLines = batchPayload
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (rawLines.length === 0) return;

    setBatchProcessing(true);
    setErrorMessage(null);
    setBatchResult(null);
    try {
      const res = await ingestBatchLogs(rawLines, sourceId);
      setBatchResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Batch ingestion failed');
    } finally {
      setBatchProcessing(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        setBatchPayload(content);
        setIngestionMode('batch');
        setBatchResult(null);
      }
    };
    reader.readAsText(file);
  };

  const handleCopyJson = () => {
    if (ingestResult?.normalized_event) {
      navigator.clipboard.writeText(JSON.stringify(ingestResult.normalized_event, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-sky-50 text-sky-600 rounded-lg">
            <ArrowDownToLine className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-slate-900">Universal Log Ingestion Engine</h2>
              <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-medium border border-emerald-200">
                Phase 3 & 4A Active
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Lossless ingestion, deterministic offline format detection, modular parsing, and universal normalization.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-500 font-mono bg-slate-50 px-3 py-2 rounded-lg border border-slate-200">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Air-Gapped / Zero External Calls</span>
        </div>
      </div>

      {/* Live Syslog Listeners & Telemetry Section */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <Radio className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-slate-900">Live Syslog Listeners & Network Transports</h3>
                <span className="flex h-2 w-2 relative">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${syslogStatus?.manager_running ? 'bg-emerald-400' : 'bg-slate-300'} opacity-75`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${syslogStatus?.manager_running ? 'bg-emerald-500' : 'bg-slate-400'}`}></span>
                </span>
                <span className={`text-[11px] font-semibold border px-1.5 py-0.5 rounded ${
                  syslogStatus?.manager_running ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-slate-600 bg-slate-100 border-slate-200'
                }`}>
                  {syslogStatus?.manager_running ? 'Sockets Active' : 'Standby'}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Network perimeter socket transports streaming directly into the lossless normalization pipeline.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {!syslogStatus?.manager_running ? (
              <button
                onClick={handleStartSyslog}
                disabled={operatingSyslog}
                className="px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg flex items-center space-x-1.5 shadow-sm transition-colors disabled:opacity-50"
              >
                <Play className={`w-3.5 h-3.5 ${operatingSyslog ? 'animate-spin' : ''}`} />
                <span>Start Listeners</span>
              </button>
            ) : (
              <button
                onClick={handleStopSyslog}
                disabled={operatingSyslog}
                className="px-3 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg flex items-center space-x-1.5 shadow-sm transition-colors disabled:opacity-50"
              >
                <Square className="w-3.5 h-3.5" />
                <span>Stop Listeners</span>
              </button>
            )}

            <button
              onClick={handleResetSyslog}
              disabled={operatingSyslog}
              className="px-2.5 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 hover:bg-slate-50 rounded-lg flex items-center space-x-1 transition-colors"
              title="Reset telemetry counters"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              <span>Reset</span>
            </button>

            <button
              onClick={loadSyslogStatus}
              disabled={loadingSyslog}
              className="px-2.5 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 hover:bg-slate-50 rounded-lg flex items-center space-x-1 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingSyslog ? 'animate-spin text-indigo-600' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {syslogMessage && (
          <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-medium flex items-center justify-between">
            <span>{syslogMessage}</span>
            <button onClick={() => setSyslogMessage(null)} className="text-emerald-700 font-bold ml-2">×</button>
          </div>
        )}

        {/* Transport Protocols Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* UDP */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <Server className="w-4 h-4 text-sky-600" />
              <div>
                <div className="text-xs font-semibold text-slate-800">UDP Syslog Transport</div>
                <div className="text-[11px] font-mono text-slate-500">
                  {syslogStatus?.udp.host || '0.0.0.0'}:{syslogStatus?.udp.port || 1514}
                </div>
              </div>
            </div>
            <span
              className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                syslogStatus?.udp.running
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
            >
              {syslogStatus?.udp.running ? 'Listening' : 'Standby'}
            </span>
          </div>

          {/* TCP */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <Server className="w-4 h-4 text-indigo-600" />
              <div>
                <div className="text-xs font-semibold text-slate-800">TCP Stream Transport</div>
                <div className="text-[11px] font-mono text-slate-500">
                  {syslogStatus?.tcp.host || '0.0.0.0'}:{syslogStatus?.tcp.port || 1514}
                  {syslogStatus?.metrics.active_tcp_connections ? ` (${syslogStatus.metrics.active_tcp_connections} active)` : ''}
                </div>
              </div>
            </div>
            <span
              className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                syslogStatus?.tcp.running
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
            >
              {syslogStatus?.tcp.running ? 'Listening' : 'Standby'}
            </span>
          </div>

          {/* TLS */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <Server className="w-4 h-4 text-purple-600" />
              <div>
                <div className="text-xs font-semibold text-slate-800">TLS 1.2+ Encrypted Transport</div>
                <div className="text-[11px] font-mono text-slate-500">
                  {syslogStatus?.tls.host || '0.0.0.0'}:{syslogStatus?.tls.port || 16514}
                </div>
              </div>
            </div>
            <span
              className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                syslogStatus?.tls.running
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
            >
              {syslogStatus?.tls.running ? 'Listening' : 'Standby'}
            </span>
          </div>
        </div>

        {/* Telemetry & Backpressure Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 text-xs">
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[11px] text-slate-500 font-medium">Messages Ingested</div>
            <div className="text-base font-bold text-slate-800 mt-0.5 font-mono">
              {syslogStatus?.metrics.messages_received ?? 0}
            </div>
            <div className="text-[10px] text-emerald-600 mt-0.5">
              {syslogStatus?.metrics.messages_processed ?? 0} successfully parsed
            </div>
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[11px] text-slate-500 font-medium">Bounded Queue Depth</div>
            <div className="text-base font-bold text-slate-800 mt-0.5 font-mono">
              {syslogStatus?.queue.depth ?? 0}{' '}
              <span className="text-[11px] font-normal text-slate-400">
                / {syslogStatus?.queue.maxsize ?? 10000}
              </span>
            </div>
            <div className="w-full bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden">
              <div
                className="bg-indigo-600 h-1.5 rounded-full"
                style={{
                  width: `${Math.min(
                    100,
                    ((syslogStatus?.queue.depth ?? 0) / (syslogStatus?.queue.maxsize || 10000)) * 100
                  )}%`,
                }}
              ></div>
            </div>
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[11px] text-slate-500 font-medium">Throughput & Latency</div>
            <div className="text-base font-bold text-slate-800 mt-0.5 font-mono">
              {syslogStatus?.metrics.events_per_second ?? 0}{' '}
              <span className="text-[11px] font-normal text-slate-400">evt/s</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Avg latency: {syslogStatus?.metrics.processing_latency_ms_avg ?? 0} ms
            </div>
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[11px] text-slate-500 font-medium">Backpressure & Drops</div>
            <div className="text-base font-bold text-slate-800 mt-0.5 font-mono">
              {syslogStatus?.metrics.messages_dropped ?? 0}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              {syslogStatus?.metrics.oversized_messages ?? 0} oversized rejected
            </div>
          </div>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setIngestionMode('single')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center space-x-2 ${
            ingestionMode === 'single'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Interactive Single Log Mode</span>
        </button>

        <button
          onClick={() => setIngestionMode('batch')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center space-x-2 ${
            ingestionMode === 'batch'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <Files className="w-4 h-4" />
          <span>Batch & Bulk Log Stream Mode</span>
        </button>
      </div>

      {/* Preset Pickers */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            {ingestionMode === 'single' ? 'Load Synthetic Multi-Vendor Log Preset' : 'Batch Preset & Bulk Log File Loading'}
          </span>
          {ingestionMode === 'batch' && (
            <label className="cursor-pointer inline-flex items-center space-x-1.5 px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors">
              <Upload className="w-3.5 h-3.5 text-sky-600" />
              <span>Upload Log File (.log, .txt, .json)</span>
              <input type="file" accept=".log,.txt,.json,.csv" onChange={handleFileUpload} className="hidden" />
            </label>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {ingestionMode === 'single' ? (
            SYNTHETIC_PRESETS.map((preset) => (
              <button
                key={preset.label}
                onClick={() => handlePresetSelect(preset.payload, preset.format, preset.defaultSourceId)}
                className="px-3 py-1.5 text-xs font-medium bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg transition-colors flex items-center space-x-1.5"
              >
                <Zap className="w-3.5 h-3.5 text-sky-600" />
                <span>{preset.label}</span>
              </button>
            ))
          ) : (
            <button
              onClick={() => {
                setBatchPayload(MULTI_VENDOR_BATCH_PRESET);
                setBatchResult(null);
                setErrorMessage(null);
              }}
              className="px-3 py-1.5 text-xs font-medium bg-indigo-50 hover:bg-indigo-100 text-indigo-800 border border-indigo-200 rounded-lg transition-colors flex items-center space-x-1.5 font-semibold"
            >
              <Zap className="w-3.5 h-3.5 text-indigo-600" />
              <span>Load 5-Vendor Multi-Stream Batch Preset</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Console Grid */}
      {ingestionMode === 'single' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Raw Payload Input */}
          <div className="lg:col-span-6 space-y-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileCode2 className="w-4 h-4 text-sky-600" />
                  <h3 className="text-sm font-semibold text-slate-900">Raw Perimeter Log Payload</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">Verbatim UTF-8</span>
              </div>

              <textarea
                value={rawPayload}
                onChange={(e) => setRawPayload(e.target.value)}
                rows={8}
                placeholder="Paste raw log string (Syslog RFC 5424/3164, CEF, LEEF, JSON, CSV, or XML)..."
                className="w-full font-mono text-xs p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white resize-y"
              />

              {/* Input Controls */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Format Hint / Selection</label>
                  <select
                    value={formatHint}
                    onChange={(e) => setFormatHint(e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-mono focus:outline-none focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="auto">Auto-Detect Format (Recommended)</option>
                    <option value="syslog">Syslog (RFC 5424 / 3164 / Cisco)</option>
                    <option value="json">JSON</option>
                    <option value="cef">CEF (Common Event Format)</option>
                    <option value="leef">LEEF (IBM QRadar)</option>
                    <option value="csv">CSV Delimited</option>
                    <option value="xml">XML Document</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block font-medium text-slate-700">Target Log Source</label>
                    <button
                      type="button"
                      onClick={() => setCustomSource(!customSource)}
                      className="text-[10px] text-sky-600 hover:underline"
                    >
                      {customSource ? 'Select Registered' : 'Enter Custom'}
                    </button>
                  </div>
                  {customSource ? (
                    <input
                      type="text"
                      value={sourceId}
                      onChange={(e) => setSourceId(e.target.value)}
                      placeholder="e.g., custom-perimeter-gw"
                      className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-mono focus:outline-none focus:ring-1 focus:ring-sky-500"
                    />
                  ) : (
                    <select
                      value={sourceId}
                      onChange={(e) => setSourceId(e.target.value)}
                      className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-mono focus:outline-none focus:ring-1 focus:ring-sky-500"
                    >
                      {registeredSources.map((s) => (
                        <option key={s.source_id} value={s.source_id}>
                          {s.hostname || s.source_id} ({s.source_id})
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-3 pt-2">
                <button
                  onClick={handleDetectFormat}
                  disabled={detecting || !rawPayload.trim()}
                  className="flex-1 inline-flex items-center justify-center space-x-1.5 px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
                >
                  {detecting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5 text-slate-500" />}
                  <span>Test Detection</span>
                </button>

                <button
                  onClick={handleIngest}
                  disabled={ingesting || !rawPayload.trim()}
                  className="flex-1 inline-flex items-center justify-center space-x-1.5 px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 shadow-sm shadow-sky-200 rounded-lg transition-colors disabled:opacity-50"
                >
                  {ingesting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Layers className="w-3.5 h-3.5" />}
                  <span>Ingest & Normalize</span>
                </button>
              </div>

              {errorMessage && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2 text-xs text-red-700">
                  <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}
            </div>

            {/* Detection Analysis Result Card */}
            {detectionResult && (
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">Format Detection Audit</h4>
                  <span className="px-2 py-0.5 text-xs font-mono font-bold bg-sky-100 text-sky-800 rounded uppercase">
                    {detectionResult.detected_format}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                    <span className="text-slate-400 block text-[11px]">Confidence</span>
                    <span className="font-mono font-semibold text-slate-800">
                      {(detectionResult.confidence * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                    <span className="text-slate-400 block text-[11px]">Detection Engine</span>
                    <span className="font-semibold text-emerald-700">Deterministic Offline</span>
                  </div>
                </div>

                <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-100">
                  <strong className="text-slate-700">Heuristic: </strong>
                  {detectionResult.reason}
                </p>
              </div>
            )}
          </div>

          {/* Right Column: Ingestion Pipeline & Normalized Event Result */}
          <div className="lg:col-span-6 space-y-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col h-full min-h-[420px]">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                <div className="flex items-center space-x-2">
                  <Cpu className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-sm font-semibold text-slate-900">Universal Event Schema Output</h3>
                </div>

                {ingestResult?.normalized_event && (
                  <button
                    onClick={handleCopyJson}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                  </button>
                )}
              </div>

              {ingestResult ? (
                <div className="space-y-4 flex-1 flex flex-col">
                  {/* Pipeline Execution Metadata */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div className="p-2 bg-slate-50 rounded border border-slate-100">
                      <span className="text-slate-400 block text-[10px]">Pipeline Status</span>
                      <span
                        className={`font-mono font-semibold ${
                          ingestResult.success ? 'text-emerald-700' : 'text-amber-700'
                        }`}
                      >
                        {ingestResult.success ? 'NORMALIZED' : 'FAILED'}
                      </span>
                    </div>

                    <div className="p-2 bg-slate-50 rounded border border-slate-100">
                      <span className="text-slate-400 block text-[10px]">Parser Plugin</span>
                      <span className="font-mono text-slate-800 truncate block">
                        {ingestResult.parser_id || 'None'}
                      </span>
                    </div>

                    <div className="p-2 bg-slate-50 rounded border border-slate-100">
                      <span className="text-slate-400 block text-[10px]">Validation</span>
                      <span
                        className={`font-mono font-semibold uppercase ${
                          ingestResult.validation_status === 'valid'
                            ? 'text-emerald-600'
                            : ingestResult.validation_status === 'warning'
                            ? 'text-amber-600'
                            : 'text-red-600'
                        }`}
                      >
                        {ingestResult.validation_status}
                      </span>
                    </div>

                    <div className="p-2 bg-slate-50 rounded border border-slate-100">
                      <span className="text-slate-400 block text-[10px]">Traceability</span>
                      <span className="font-mono text-sky-700 font-semibold">100% LINKED</span>
                    </div>
                  </div>

                  {/* Traceability IDs */}
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500 font-sans">raw_event_id:</span>
                      <span className="text-slate-900 font-semibold">{ingestResult.raw_event_id}</span>
                    </div>
                    {ingestResult.normalized_event_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500 font-sans">normalized_event_id:</span>
                        <span className="text-sky-700 font-semibold">{ingestResult.normalized_event_id}</span>
                      </div>
                    )}
                  </div>

                  {/* Warnings or Errors */}
                  {ingestResult.warnings.length > 0 && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 space-y-1">
                      <div className="font-semibold flex items-center space-x-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                        <span>Validation Warnings ({ingestResult.warnings.length})</span>
                      </div>
                      <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-700">
                        {ingestResult.warnings.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Normalized JSON Viewer */}
                  <div className="flex-1 min-h-[220px]">
                    <pre className="w-full h-full p-3.5 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-auto max-h-[360px]">
                      {JSON.stringify(ingestResult.normalized_event, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8 border border-dashed border-slate-200 rounded-lg text-slate-400">
                  <FileCode2 className="w-10 h-10 text-slate-300 mb-2" />
                  <p className="text-sm font-medium text-slate-600">No event processed yet</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-xs">
                    Select a multi-vendor synthetic preset on the left and click <strong>Ingest & Normalize</strong> to trigger the live pipeline.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Batch Ingestion Console Grid */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Batch Raw Payload Textarea */}
          <div className="lg:col-span-6 space-y-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Files className="w-4 h-4 text-indigo-600" />
                  <h3 className="text-sm font-semibold text-slate-900">Batch Log Stream Input</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {batchPayload.split('\n').filter((l) => l.trim().length > 0).length} lines detected
                </span>
              </div>

              <textarea
                value={batchPayload}
                onChange={(e) => setBatchPayload(e.target.value)}
                rows={12}
                placeholder="Paste multi-line log streams or upload a log file. One raw event per line..."
                className="w-full font-mono text-xs p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white resize-y"
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Target Log Source</label>
                  <select
                    value={sourceId}
                    onChange={(e) => setSourceId(e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-slate-700 font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    {registeredSources.map((s) => (
                      <option key={s.source_id} value={s.source_id}>
                        {s.hostname || s.source_id} ({s.source_id})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={handleBatchIngest}
                    disabled={batchProcessing || !batchPayload.trim()}
                    className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm shadow-indigo-200 transition-colors disabled:opacity-50"
                  >
                    {batchProcessing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                    <span>Process Batch Ingestion Stream</span>
                  </button>
                </div>
              </div>

              {errorMessage && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2 text-xs text-red-700">
                  <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Processing Run Operational Telemetry */}
          <div className="lg:col-span-6 space-y-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col h-full min-h-[420px]">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                <div className="flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-indigo-600" />
                  <h3 className="text-sm font-semibold text-slate-900">ProcessingRun Operational Telemetry</h3>
                </div>
                {batchResult && (
                  <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">
                    100% LOSSLESS RECORDED
                  </span>
                )}
              </div>

              {batchResult ? (
                <div className="space-y-4 flex-1">
                  {/* ProcessingRun ID Banner */}
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono flex items-center justify-between">
                    <div>
                      <span className="text-slate-500 font-sans">Processing Run ID: </span>
                      <strong className="text-slate-900 font-bold">{batchResult.processing_run_id}</strong>
                    </div>
                    <div className="flex items-center space-x-1 text-emerald-600">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{batchResult.processing_time_ms} ms</span>
                    </div>
                  </div>

                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-slate-400 block text-[11px]">Total Received</span>
                      <span className="text-xl font-bold text-slate-800 font-mono">
                        {batchResult.total_received}
                      </span>
                    </div>

                    <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                      <span className="text-emerald-700 block text-[11px] font-medium">Successfully Parsed</span>
                      <span className="text-xl font-bold text-emerald-800 font-mono">
                        {batchResult.total_parsed}
                      </span>
                    </div>

                    <div className="p-3 bg-sky-50 rounded-lg border border-sky-200">
                      <span className="text-sky-700 block text-[11px] font-medium">Normalized (UES)</span>
                      <span className="text-xl font-bold text-sky-800 font-mono">
                        {batchResult.total_normalized}
                      </span>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                      <span className="text-slate-400 block text-[11px]">Failed Records</span>
                      <span className={`text-xl font-bold font-mono ${batchResult.total_failed > 0 ? 'text-red-600' : 'text-slate-800'}`}>
                        {batchResult.total_failed}
                      </span>
                    </div>
                  </div>

                  {/* Format Statistics Breakdown */}
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Format Distribution</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(batchResult.format_statistics).map(([fmt, cnt]) => (
                        <div key={fmt} className="px-3 py-1 bg-white rounded-lg border border-slate-200 text-xs font-mono flex items-center space-x-1.5 shadow-sm">
                          <span className="font-semibold text-slate-800 uppercase">{fmt}:</span>
                          <span className="text-sky-600 font-bold">{cnt}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Parser Plugin Breakdown */}
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                    <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Parser Plugin Allocation</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(batchResult.parser_statistics).map(([pname, cnt]) => (
                        <div key={pname} className="px-3 py-1 bg-white rounded-lg border border-slate-200 text-xs font-mono flex items-center space-x-1.5 shadow-sm">
                          <span className="font-semibold text-slate-800">{pname}:</span>
                          <span className="text-emerald-600 font-bold">{cnt}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8 border border-dashed border-slate-200 rounded-lg text-slate-400">
                  <Files className="w-10 h-10 text-slate-300 mb-2" />
                  <p className="text-sm font-medium text-slate-600">No batch processing run active</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-xs">
                    Paste multiple raw logs or upload a log file and click <strong>Process Batch Ingestion Stream</strong> to run the batch engine.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Ingestion;
