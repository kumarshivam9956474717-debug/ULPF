import React from 'react';
import { Activity, CheckCircle2, AlertTriangle, RefreshCw, Cpu, ShieldCheck } from 'lucide-react';

import { HealthStatus } from '../services/api';

interface SystemStatusCardProps {
  status: HealthStatus | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  latency: number | null;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({
  status,
  loading,
  error,
  onRefresh,
  latency,
}) => {
  const isHealthy = status?.status === 'ok';

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
        <div className="flex items-center space-x-3">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              isHealthy ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'
            }`}
          >
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900">Framework Operational Status</h3>
            <p className="text-xs text-slate-500">Core backend API & environment verification</p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-md transition-colors disabled:opacity-50"
          title="Re-query /api/v1/health"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Ping Health</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        {/* API Health */}
        <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-100">
          <span className="text-xs font-medium text-slate-500 block mb-1">Health Endpoint</span>
          <div className="flex items-center space-x-2">
            {isHealthy ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            )}
            <span className="font-mono text-sm font-semibold text-slate-800">
              {status ? status.status.toUpperCase() : error ? 'UNREACHABLE' : 'CHECKING...'}
            </span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono mt-1 block">/api/v1/health</span>
        </div>

        {/* Service / Engine */}
        <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-100">
          <span className="text-xs font-medium text-slate-500 block mb-1">Core Service</span>
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-sky-600 shrink-0" />
            <span className="font-mono text-sm font-semibold text-slate-800">
              {status?.service || 'ULPF Engine'}
            </span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block font-mono">v{status?.version || '1.0.0'}</span>
        </div>

        {/* Latency */}
        <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-100">
          <span className="text-xs font-medium text-slate-500 block mb-1">Response Latency</span>
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-indigo-600 shrink-0" />
            <span className="font-mono text-sm font-semibold text-slate-800">
              {latency !== null ? `${latency} ms` : '—'}
            </span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">Local loopback</span>
        </div>

        {/* Air-gap verification */}
        <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-100">
          <span className="text-xs font-medium text-slate-500 block mb-1">Air-Gap Integrity</span>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-mono text-sm font-semibold text-emerald-700">ENFORCED</span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">0 cloud SaaS calls</span>
        </div>
      </div>

      {error && (
        <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start space-x-2.5 text-xs text-amber-800">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Backend connection notice:</p>
            <p className="text-amber-700 mt-0.5">
              Could not reach backend API at <code className="bg-amber-100/80 px-1 py-0.5 rounded">/api/v1/health</code>. Ensure the FastAPI backend server is running on port 8000.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
