import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ArrowDownToLine,
  Layers,
  Cpu,
  BarChart3,
  Server,
  Settings,
  SlidersHorizontal,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  FlaskConical,
} from 'lucide-react';


const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/demo', label: 'Live Evaluation Lab', icon: FlaskConical },
  { path: '/supervisory', label: 'Supervisory Assessment', icon: ShieldCheck },
  { path: '/security-analytics', label: 'Security Analytics', icon: ShieldAlert },
  { path: '/ingestion', label: 'Log Ingestion', icon: ArrowDownToLine },
  { path: '/onboarding', label: 'Log Onboarding', icon: Sparkles },
  { path: '/profiles', label: 'Parser Profiles', icon: SlidersHorizontal },
  { path: '/events', label: 'Events Explorer', icon: Layers },
  { path: '/parsers', label: 'Parser Registry', icon: Cpu },
  { path: '/analytics', label: 'Analytics Readiness', icon: BarChart3 },
  { path: '/sources', label: 'Log Sources', icon: Server },
  { path: '/settings', label: 'System Settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800">
      <div className="p-4 border-b border-slate-800/80">
        <div className="flex items-center space-x-2.5 text-xs font-semibold text-slate-300 uppercase tracking-wider">
          <img
            src="/omnilogix-logo.png"
            alt="OmniLogix"
            className="w-6 h-6 object-contain rounded bg-white p-0.5"
          />
          <span>OmniLogix Core</span>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-sky-600 text-white shadow-sm shadow-sky-900/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/70'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 bg-slate-950/40 text-xs text-slate-400">
        <div className="flex items-center justify-between mb-1.5 font-medium text-slate-300">
          <span>Mode</span>
          <span className="text-emerald-400 font-mono">Air-Gapped</span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span>Schema</span>
          <span className="font-mono">UES v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
