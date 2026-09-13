import React from 'react';
import { useOutletContext } from 'react-router-dom';
import { SystemStatusCard } from '../components/SystemStatusCard';
import { HealthStatus } from '../services/api';
import {
  Shield,
  Layers,
  CheckCircle,
  Boxes
} from 'lucide-react';


interface OutletContextType {
  healthStatus: HealthStatus | null;
  loading: boolean;
  error: string | null;
  latency: number | null;
  onRefreshHealth: () => void;
}

export const Dashboard: React.FC = () => {
  const { healthStatus, loading, error, latency, onRefreshHealth } =
    useOutletContext<OutletContextType>();

  const PIPELINE_STEPS = [
    { name: 'Raw Event', desc: 'Immutable ingest' },
    { name: 'Ingestion', desc: 'Syslog / API / File' },
    { name: 'Detection', desc: 'Format / Vendor' },
    { name: 'Parser', desc: 'Modular logic' },
    { name: 'Extraction', desc: 'Field mapping' },
    { name: 'Normalization', desc: 'Universal Schema' },
    { name: 'Validation', desc: 'Quality audit' },
    { name: 'Traceability', desc: '100% lineage' },
    { name: 'Analytics-Ready', desc: 'Lossless output' },
  ];

  const ARCH_PRINCIPLES = [
    { title: 'Lossless Raw Preservation', desc: 'Raw events are NEVER modified or discarded.' },
    { title: 'Bi-directional Traceability', desc: 'Every normalized event references its original raw record.' },
    { title: 'Decoupled Layers', desc: 'Parsing and normalization are completely separated.' },
    { title: 'Modular Architecture', desc: 'Vendor-specific logic is modular, isolated, and replaceable.' },
    { title: 'Zero Core Modifications', desc: 'Onboard new log formats without modifying the core framework.' },
    { title: 'Strictly Air-Gapped', desc: '100% offline execution; zero cloud AI APIs or SaaS calls.' },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Title & Scope Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 text-xs font-semibold bg-sky-100 text-sky-800 rounded font-mono">
              PHASE 1 FOUNDATION
            </span>
            <span className="text-xs text-slate-500 font-medium">SIH 2026 Problem Statement SIH26156</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            Universal Log Pre-processing Framework (ULPF)
          </h2>
          <p className="text-sm text-slate-600 mt-1">
            Vendor-agnostic, scalable, extensible, and air-gapped perimeter network-device log normalizer.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-start md:self-auto">
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-right">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Target Surface</span>
            <span className="text-xs font-medium text-slate-700">Perimeter Gateways & IDPS</span>
          </div>
        </div>
      </div>

      {/* Live System Health Status Card */}
      <SystemStatusCard
        status={healthStatus}
        loading={loading}
        error={error}
        latency={latency}
        onRefresh={onRefreshHealth}
      />

      {/* Core Pipeline Architecture Flow */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2.5">
            <Boxes className="w-5 h-5 text-sky-600" />
            <h3 className="text-base font-semibold text-slate-900">Core Pipeline Architecture</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Sequential Processing Chain</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-2 items-center">
          {PIPELINE_STEPS.map((step, idx) => (
            <React.Fragment key={step.name}>
              <div className="bg-slate-50 hover:bg-slate-100/80 transition-colors border border-slate-200/90 rounded-lg p-3 text-center">
                <span className="text-[10px] font-mono font-bold text-sky-600 block mb-1">
                  0{idx + 1}
                </span>
                <span className="text-xs font-semibold text-slate-800 block truncate">{step.name}</span>
                <span className="text-[10px] text-slate-500 block truncate mt-0.5">{step.desc}</span>
              </div>
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Architectural Pillars & Schema Foundation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Core Principles */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center space-x-2.5 mb-4">
            <Shield className="w-5 h-5 text-emerald-600" />
            <h3 className="text-base font-semibold text-slate-900">Architecture Principles</h3>
          </div>
          <div className="space-y-3">
            {ARCH_PRINCIPLES.map((principle, index) => (
              <div key={index} className="flex items-start space-x-3 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-semibold text-slate-800">{principle.title}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">{principle.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Universal Event Schema Foundation */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2.5">
                <Layers className="w-5 h-5 text-sky-600" />
                <h3 className="text-base font-semibold text-slate-900">Universal Event Schema</h3>
              </div>
              <span className="text-xs font-mono bg-sky-50 text-sky-700 px-2 py-0.5 rounded border border-sky-100">
                11 Logical Groups
              </span>
            </div>

            <p className="text-xs text-slate-600 mb-4">
              The Universal Event Schema abstracts heterogeneous perimeter formats (Syslog, CEF, LEEF, JSON) into a unified, vendor-neutral structure with lossless custom attributes.
            </p>

            <div className="grid grid-cols-2 gap-2 text-xs">
              {[
                { name: '1. Identity', detail: 'event_id, source_id, schema_version' },
                { name: '2. Time', detail: 'timestamp, ingestion_timestamp, tz' },
                { name: '3. Source', detail: 'vendor, product, device_type, host' },
                { name: '4. Network', detail: 'src_ip, src_port, dst_ip, dst_port' },
                { name: '5. User Identity', detail: 'username, user_id, auth_method' },
                { name: '6. Event', detail: 'event_type, action, outcome, severity' },
                { name: '7. Network Context', detail: 'interface, direction, zone' },
                { name: '8. Threat / Sec', detail: 'threat_name, threat_id, rule_id' },
                { name: '9. Additional', detail: 'message, tags, custom_fields' },
                { name: '10. Traceability', detail: 'raw_event_id, parser_id, versions' },
                { name: '11. Raw Preservation', detail: 'raw_event (lossless verbatim string)' },
              ].map((group) => (
                <div key={group.name} className="p-2 bg-slate-50 rounded border border-slate-100">
                  <div className="font-semibold text-slate-800">{group.name}</div>
                  <div className="text-[11px] text-slate-500 font-mono truncate">{group.detail}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-400 flex items-center justify-between">
            <span>Validated via Pydantic v2 & SQLAlchemy 2.0</span>
            <span className="font-mono text-emerald-600">7 Unit Tests Passing</span>
          </div>
        </div>
      </div>
    </div>
  );
};
