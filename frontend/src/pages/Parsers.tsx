import React from 'react';
import { Cpu, Plus } from 'lucide-react';


export const Parsers: React.FC = () => {
  const PARSER_TARGETS = [
    {
      id: 'cisco_asa',
      name: 'Cisco ASA / Firepower',
      vendor: 'Cisco',
      format: 'Syslog / %ASA codes',
      type: 'Perimeter Firewall',
    },
    {
      id: 'paloalto_panos',
      name: 'Palo Alto PAN-OS',
      vendor: 'Palo Alto Networks',
      format: 'Syslog CSV / CEF',
      type: 'NGFW & Threat Prevention',
    },
    {
      id: 'fortinet_fortigate',
      name: 'Fortinet FortiGate',
      vendor: 'Fortinet',
      format: 'Key-Value Syslog',
      type: 'NGFW & UTM',
    },
    {
      id: 'checkpoint_gaia',
      name: 'Check Point Quantum',
      vendor: 'Check Point',
      format: 'Log Export / Syslog',
      type: 'Perimeter Gateway',
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Modular Parser Registry</h2>
            <p className="text-sm text-slate-500">
              Decoupled parsing modules for vendor-specific format extraction without core changes.
            </p>
          </div>
        </div>

        <button
          disabled
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-400 bg-slate-100 rounded-md cursor-not-allowed self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Parser</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PARSER_TARGETS.map((target) => (
          <div key={target.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  {target.vendor}
                </span>
                <h3 className="text-sm font-bold text-slate-900 mt-0.5">{target.name}</h3>
                <p className="text-xs text-slate-500 mt-1">{target.type}</p>
              </div>
              <span className="px-2 py-0.5 text-[11px] font-medium bg-slate-100 text-slate-600 rounded">
                Target: Phase 2
              </span>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-mono text-slate-500">
              <span>Format: {target.format}</span>
              <span className="text-sky-600">ID: {target.id}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm text-xs text-slate-600 space-y-2">
        <h4 className="font-semibold text-slate-800">Decoupled Parser Architecture:</h4>
        <p>
          Each parser is encapsulated behind a strict interface implementing <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">parse_raw(payload: str) -&gt; ExtractedEvent</code>.
          Adding a new vendor format never alters the database schema, normalization pipeline, or frontend presentation.
        </p>
      </div>
    </div>
  );
};
