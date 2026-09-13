import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { fetchHealthStatus, HealthStatus } from '../services/api';

export const Layout: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const data = await fetchHealthStatus();
      const end = performance.now();
      setLatency(Math.round(end - start));
      setHealthStatus(data);
    } catch (err: any) {
      setError(err.message || 'Health check error');
      setHealthStatus(null);
      setLatency(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // Periodic light ping every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const isBackendHealthy = healthStatus ? healthStatus.status === 'ok' : error ? false : null;

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header isBackendHealthy={isBackendHealthy} version={healthStatus?.version} />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <Outlet context={{ healthStatus, loading, error, latency, onRefreshHealth: checkHealth }} />
        </main>
      </div>
    </div>
  );
};
