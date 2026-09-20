import React from 'react';
import { Lock, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface HeaderProps {
  isBackendHealthy: boolean | null;
  version?: string;
}

export const Header: React.FC<HeaderProps> = ({ isBackendHealthy, version = "1.0.0" }) => {
  const { user, logout } = useAuth();

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

        {/* Authenticated User Profile & Role Badge */}
        {user && (
          <div className="flex items-center space-x-2 pl-3 border-l border-slate-200">
            <div className="flex items-center space-x-2 py-1 px-2.5 rounded-lg bg-slate-50 border border-slate-200">
              <UserIcon className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-semibold text-slate-800">{user.username}</span>
              <span
                className={`text-[10px] uppercase font-mono font-bold px-1.5 py-0.5 rounded border ${
                  user.role === 'ADMIN'
                    ? 'bg-purple-100 text-purple-800 border-purple-200'
                    : user.role === 'ANALYST'
                    ? 'bg-sky-100 text-sky-800 border-sky-200'
                    : user.role === 'OPERATOR'
                    ? 'bg-amber-100 text-amber-800 border-amber-200'
                    : 'bg-slate-200 text-slate-700 border-slate-300'
                }`}
              >
                {user.role}
              </span>
            </div>

            <button
              onClick={logout}
              title="Sign Out of OmniLogix"
              className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg border border-transparent hover:border-rose-200 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
