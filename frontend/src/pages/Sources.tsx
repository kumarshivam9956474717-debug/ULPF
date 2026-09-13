import React from 'react';
import { Server, Plus, Shield, Network } from 'lucide-react';

export const Sources: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg">
            <Server className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Perimeter Log Sources</h2>
            <p className="text-sm text-slate-500">
              Perimeter security device registry (Firewalls, UTMs, Gateways, Proxies).
            </p>
          </div>
        </div>

        <button
          disabled
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-400 bg-slate-100 rounded-md cursor-not-allowed self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Log Source</span>
        </button>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Device Architecture Registry</h3>
        <p className="text-xs text-slate-600 mb-4">
          The <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">LogSource</code> SQLAlchemy model manages perimeter emitters with expected protocols, vendor profiles, and device roles:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex items-center space-x-2 font-semibold text-slate-800 mb-1">
              <Shield className="w-4 h-4 text-sky-600" />
              <span>Next-Gen Firewalls</span>
            </div>
            <p className="text-slate-500 text-[11px]">Palo Alto PAN-OS, Fortinet FortiGate, Check Point Quantum</p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex items-center space-x-2 font-semibold text-slate-800 mb-1">
              <Network className="w-4 h-4 text-emerald-600" />
              <span>Edge Routers / VPN</span>
            </div>
            <p className="text-slate-500 text-[11px]">Cisco ISR/ASR, OpenVPN Access Server, WireGuard Gateway</p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex items-center space-x-2 font-semibold text-slate-800 mb-1">
              <Server className="w-4 h-4 text-indigo-600" />
              <span>Reverse Proxies / WAF</span>
            </div>
            <p className="text-slate-500 text-[11px]">Cloudflare Edge, HAProxy, NGINX App Protect, F5 BIG-IP</p>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-dashed border-slate-300 text-center py-12">
        <p className="text-sm font-medium text-slate-600">
          Source onboarding and management forms will be enabled in Phase 2.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Supported metadata includes IP, Hostname, Expected Format, Vendor Profile, and Health status.
        </p>
      </div>
    </div>
  );
};
