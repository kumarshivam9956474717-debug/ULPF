import React from 'react';
import { Settings as SettingsIcon, Lock, HardDrive } from 'lucide-react';


export const SystemSettings: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3 mb-2">
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
            <SettingsIcon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">System & Air-Gap Configuration</h2>
            <p className="text-sm text-slate-500">
              Operational parameters, air-gap enforcement, and local storage retention policies.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Air Gap Enforcement Policy */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-sm">
            <Lock className="w-5 h-5 text-emerald-600" />
            <span>Air-Gap Enforcement Policy</span>
          </div>
          <p className="text-xs text-slate-600">
            ULPF operates strictly without external network egress. All parsers, schemas, and processing algorithms execute on host resources.
          </p>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-200">
              <span className="font-medium text-slate-700">External AI APIs</span>
              <span className="font-mono text-emerald-700 font-semibold">BLOCKED (0 calls)</span>
            </div>
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-200">
              <span className="font-medium text-slate-700">Cloud Telemetry / SaaS</span>
              <span className="font-mono text-emerald-700 font-semibold">DISABLED</span>
            </div>
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-200">
              <span className="font-medium text-slate-700">DNS Resolution Egress</span>
              <span className="font-mono text-slate-700 font-semibold">Local Loopback Only</span>
            </div>
          </div>
        </div>

        {/* Local Storage & Retention */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 text-sky-700 font-semibold text-sm">
            <HardDrive className="w-5 h-5 text-sky-600" />
            <span>Local Storage Directory Paths</span>
          </div>
          <p className="text-xs text-slate-600">
            File directories used for raw staging, processed outputs, and synthetic benchmarks.
          </p>

          <div className="space-y-2 text-xs font-mono">
            <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-sans font-semibold">Raw Staging</span>
              <span className="text-slate-800">./data/raw/</span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-sans font-semibold">Processed Parquet</span>
              <span className="text-slate-800">./data/processed/</span>
            </div>
            <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-sans font-semibold">Synthetic Datasets</span>
              <span className="text-slate-800">./data/synthetic/</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
