import React from 'react';
import { Lock } from 'lucide-react';


interface HeaderProps {
  isBackendHealthy: boolean | null;
  version?: string;
}

export const Header: React.FC<HeaderProps> = ({ isBackendHealthy, version = "1.0.0" }) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 shadow-sm">
      <div className="flex items-center space-x-3">
        <img
          src="/omnilogix-logo.png"
          alt="OmniLogix Logo"
          className="h-10 w-auto object-contain rounded-lg border border-slate-100 shadow-sm"
        />
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-bold text-slate-900 tracking-tight">OmniLogix</h1>
            <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono font-medium border border-slate-200">
              v{version}
            </span>
            <span className="text-xs bg-sky-50 text-sky-700 px-2 py-0.5 rounded font-medium border border-sky-100 hidden sm:inline-block">
              SIH26156 Prototype
            </span>
          </div>
          <p className="text-xs text-slate-500 hidden md:block">Universal Log Intelligence & Pre-processing Framework (ULPF)</p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Air-gapped / Offline indicator */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200/80 rounded-full text-xs font-medium">
          <Lock className="w-3.5 h-3.5 text-emerald-600" />
          <span>Air-Gapped / Offline</span>
        </div>

        {/* Backend health status badge */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            isBackendHealthy === true
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : isBackendHealthy === false
              ? 'bg-amber-50 text-amber-800 border-amber-200'
              : 'bg-slate-100 text-slate-600 border-slate-200'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendHealthy === true
                ? 'bg-emerald-500 animate-pulse'
                : isBackendHealthy === false
                ? 'bg-amber-500'
                : 'bg-slate-400'
            }`}
          />
          <span>
            {isBackendHealthy === true
              ? 'API Active'
              : isBackendHealthy === false
              ? 'API Offline'
              : 'Checking API...'}
          </span>
        </div>
      </div>
    </header>
  );
};
