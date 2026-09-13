import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Database,
  ShieldAlert,
  Download,
  RefreshCw,
  Cpu,
  FolderTree,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Play
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import {
  fetchAnalyticsOverview,
  fetchAnalyticsTimeline,
  fetchAnalyticsVendors,
  fetchAnalyticsSeverity,
  fetchAnalyticsTopIps,
  fetchAnalyticsTopPorts,
  triggerParquetExport,
  fetchExportStatus,
  triggerAnomalyTrain,
  triggerAnomalyScan,
  fetchAnomalyResults,
  fetchAnomalyStatistics,
  OverviewMetrics,
  TimelinePoint,
  DistributionItem,
  TopItem,
  ExportMetrics,
  ExportStatus,
  AnomalyScoreItem,
  AnomalyStatistics,
  TrainingResult,
  ScanResult
} from '../services/api';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#e11d48',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#0284c7',
  informational: '#64748b',
  unknown: '#94a3b8',
};

const VENDOR_COLORS = ['#0284c7', '#4f46e5', '#059669', '#d97706', '#7c3aed', '#db2777'];

export const Analytics: React.FC = () => {
  // Core Analytics State
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [vendors, setVendors] = useState<DistributionItem[]>([]);
  const [severities, setSeverities] = useState<DistributionItem[]>([]);
  const [topIps, setTopIps] = useState<TopItem[]>([]);
  const [topPorts, setTopPorts] = useState<TopItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Anomaly Detection State
  const [anomalyStats, setAnomalyStats] = useState<AnomalyStatistics | null>(null);
  const [recentAnomalies, setRecentAnomalies] = useState<AnomalyScoreItem[]>([]);
  const [trainingInProgress, setTrainingInProgress] = useState<boolean>(false);
  const [scanningInProgress, setScanningInProgress] = useState<boolean>(false);
  const [anomalyActionMessage, setAnomalyActionMessage] = useState<string | null>(null);

  // Parquet Export State
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null);
  const [exportModalOpen, setExportModalOpen] = useState<boolean>(false);
  const [exportingInProgress, setExportingInProgress] = useState<boolean>(false);
  const [lastExportResult, setLastExportResult] = useState<ExportMetrics | null>(null);
  const [batchSize, setBatchSize] = useState<number>(10000);

  const loadAllAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        overviewData,
        timelineData,
        vendorData,
        severityData,
        topIpsData,
        topPortsData,
        anomStats,
        anomResults,
        expStatus
      ] = await Promise.all([
        fetchAnalyticsOverview(),
        fetchAnalyticsTimeline('hour'),
        fetchAnalyticsVendors(),
        fetchAnalyticsSeverity(),
        fetchAnalyticsTopIps(5),
        fetchAnalyticsTopPorts(5),
        fetchAnomalyStatistics().catch(() => null),
        fetchAnomalyResults(true, 10).catch(() => []),
        fetchExportStatus().catch(() => null)
      ]);

      setOverview(overviewData);
      setTimeline(timelineData);
      setVendors(vendorData);
      setSeverities(severityData);
      setTopIps(topIpsData);
      setTopPorts(topPortsData);
      if (anomStats) setAnomalyStats(anomStats);
      if (anomResults) setRecentAnomalies(anomResults);
      if (expStatus) setExportStatus(expStatus);
    } catch (err: any) {
      setError(err.message || 'Failed to load analytics data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllAnalytics();
  }, []);

  const handleTrainBaseline = async () => {
    setTrainingInProgress(true);
    setAnomalyActionMessage(null);
    try {
      const res: TrainingResult = await triggerAnomalyTrain(5000);
      setAnomalyActionMessage(`Baseline trained successfully on ${res.records_trained.toLocaleString()} records in ${res.duration_seconds}s.`);
      const stats = await fetchAnomalyStatistics();
      setAnomalyStats(stats);
    } catch (err: any) {
      setAnomalyActionMessage(`Training error: ${err.message}`);
    } finally {
      setTrainingInProgress(false);
    }
  };

  const handleScanAnomalies = async () => {
    setScanningInProgress(true);
    setAnomalyActionMessage(null);
    try {
      const res: ScanResult = await triggerAnomalyScan(5000, true);
      setAnomalyActionMessage(`Scan complete: ${res.anomalies_detected} anomalies detected across ${res.records_scanned} records.`);
      const [stats, results, over] = await Promise.all([
        fetchAnomalyStatistics(),
        fetchAnomalyResults(true, 10),
        fetchAnalyticsOverview()
      ]);
      setAnomalyStats(stats);
      setRecentAnomalies(results);
      setOverview(over);
    } catch (err: any) {
      setAnomalyActionMessage(`Scan error: ${err.message}`);
    } finally {
      setScanningInProgress(false);
    }
  };

  const handleExecuteExport = async () => {
    setExportingInProgress(true);
    try {
      const res = await triggerParquetExport(batchSize);
      setLastExportResult(res);
      const status = await fetchExportStatus();
      setExportStatus(status);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setExportingInProgress(false);
    }
  };

  const formatPort = (port: string) => {
    const p = parseInt(port, 10);
    const common: Record<number, string> = {
      443: 'HTTPS',
      80: 'HTTP',
      22: 'SSH',
      53: 'DNS',
      123: 'NTP',
      514: 'Syslog',
      8080: 'HTTP-Alt',
      8443: 'HTTPS-Alt'
    };
    return common[p] ? `${port} (${common[p]})` : port;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-sky-50 text-sky-600 rounded-lg border border-sky-100">
            <BarChart3 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Perimeter Analytics & Columnar Engine</h2>
            <p className="text-sm text-slate-500">
              SQL aggregations, timestamp-partitioned Apache Parquet export, and air-gapped Isolation Forest baseline.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setExportModalOpen(true)}
            className="inline-flex items-center px-3.5 py-2 border border-sky-200 rounded-lg text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 shadow-xs transition-colors"
          >
            <Download className="w-4 h-4 mr-1.5" />
            Export Parquet
          </button>

          <button
            onClick={loadAllAnalytics}
            disabled={loading}
            className="inline-flex items-center px-3.5 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl text-rose-700 flex items-center space-x-2 text-sm font-medium">
          <AlertTriangle className="w-4 h-4 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-1">
            <span>Total Normalized</span>
            <Database className="w-4 h-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {overview?.total_events.toLocaleString() || '0'}
          </div>
          <span className="text-[11px] text-slate-400">UES database records</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-1">
            <span>Throughput Rate</span>
            <Activity className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {overview?.events_per_minute.toFixed(1) || '0.0'}{' '}
            <span className="text-xs font-normal text-slate-500">evt/min</span>
          </div>
          <span className="text-[11px] text-slate-400">
            ~{overview?.events_per_hour.toFixed(0) || '0'} events / hr
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-1">
            <span>Flagged Anomalies</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-600">
            {overview?.anomaly_count.toLocaleString() || '0'}
          </div>
          <span className="text-[11px] text-slate-400">
            {anomalyStats?.anomaly_rate.toFixed(1) || '0.0'}% outlier contamination
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-1">
            <span>Validation Integrity</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-600">
            {overview ? overview.total_events - overview.validation_failures : 0}
          </div>
          <span className="text-[11px] text-slate-400">
            {overview?.validation_failures || 0} validation drops
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-1">
            <span>Air-Gapped Model</span>
            <Cpu className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-base font-bold text-slate-800 mt-1 truncate">
            {anomalyStats?.is_model_trained ? 'IsolationForest Active' : 'Untrained Baseline'}
          </div>
          <span className="text-[11px] text-slate-400">Local scikit-learn v1.0</span>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline Chart (2 cols) */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Event Ingestion Frequency Timeline</h3>
              <p className="text-xs text-slate-500">Hourly aggregated volume of perimeter log streams</p>
            </div>
            <div className="flex items-center space-x-1 text-xs text-slate-500">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-sky-500 mr-1" />
              <span>Events</span>
            </div>
          </div>

          <div className="h-64">
            {timeline.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                No timeline records available yet. Ingest events to populate trend graph.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0284c7" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={(val) => val.split(' ')[1] || val}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#0284c7"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCount)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Severity Distribution (1 col) */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-900 text-sm mb-1">Severity Breakdown</h3>
          <p className="text-xs text-slate-500 mb-4">Normalized security risk taxonomy</p>

          <div className="h-64">
            {severities.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                No severity records found.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={severities} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis dataKey="key" type="category" tick={{ fontSize: 11, fill: '#334155' }} width={80} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {severities.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={SEVERITY_COLORS[entry.key.toLowerCase()] || '#0284c7'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Second Row: Top Entities & Vendor Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Source IPs */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-slate-900 text-sm">Top Source IP Addresses</h3>
            <span className="text-[11px] font-semibold text-slate-400">By Frequency</span>
          </div>
          <div className="space-y-3">
            {topIps.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">No source IPs recorded.</p>
            ) : (
              topIps.map((ip, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-mono text-slate-800 font-medium">{ip.item}</span>
                    <span className="text-slate-500 font-semibold">{ip.count} ({ip.percentage.toFixed(1)}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5">
                    <div
                      className="bg-sky-500 h-1.5 rounded-full"
                      style={{ width: `${Math.min(100, ip.percentage)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Destination Ports */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-slate-900 text-sm">Top Destination Ports</h3>
            <span className="text-[11px] font-semibold text-slate-400">By Frequency</span>
          </div>
          <div className="space-y-3">
            {topPorts.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">No ports recorded.</p>
            ) : (
              topPorts.map((p, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-mono text-slate-800 font-medium">{formatPort(p.item)}</span>
                    <span className="text-slate-500 font-semibold">{p.count} ({p.percentage.toFixed(1)}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5">
                    <div
                      className="bg-indigo-500 h-1.5 rounded-full"
                      style={{ width: `${Math.min(100, p.percentage)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Vendor Distribution */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-900 text-sm mb-1">Heterogeneous Vendor Share</h3>
          <p className="text-xs text-slate-500 mb-3">Multi-vendor perimeter sources</p>

          <div className="h-48 flex items-center justify-center">
            {vendors.length === 0 ? (
              <p className="text-xs text-slate-400">No vendor distribution data.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={vendors}
                    dataKey="count"
                    nameKey="key"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={3}
                  >
                    {vendors.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={VENDOR_COLORS[index % VENDOR_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    formatter={(val) => <span className="text-[11px] text-slate-600 font-medium">{val}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Offline Anomaly Detection Section */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-100 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-rose-50 text-rose-600 rounded-lg border border-rose-100">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-900">Offline Anomaly Detection Baseline</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                  IsolationForest
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Deterministic 9-dimensional numerical feature tensors analyzed locally without internet or cloud APIs.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleTrainBaseline}
              disabled={trainingInProgress}
              className="inline-flex items-center px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
            >
              <Cpu className={`w-3.5 h-3.5 mr-1.5 text-indigo-600 ${trainingInProgress ? 'animate-spin' : ''}`} />
              {trainingInProgress ? 'Fitting...' : 'Train Baseline'}
            </button>

            <button
              onClick={handleScanAnomalies}
              disabled={scanningInProgress}
              className="inline-flex items-center px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 shadow-xs transition-colors"
            >
              <Play className={`w-3.5 h-3.5 mr-1.5 ${scanningInProgress ? 'animate-spin' : ''}`} />
              {scanningInProgress ? 'Scanning...' : 'Scan Events'}
            </button>
          </div>
        </div>

        {anomalyActionMessage && (
          <div className="p-3 bg-sky-50 text-sky-800 border border-sky-200 rounded-lg text-xs font-medium flex items-center justify-between">
            <span>{anomalyActionMessage}</span>
            <button onClick={() => setAnomalyActionMessage(null)} className="text-sky-600 font-bold ml-2">✕</button>
          </div>
        )}

        {/* Flagged Anomalies Table */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Recently Flagged Anomalies ({recentAnomalies.length})
            </span>
            <span className="text-[11px] text-slate-400">Score &ge; 0.50 threshold</span>
          </div>

          {recentAnomalies.length === 0 ? (
            <div className="py-8 text-center bg-slate-50 rounded-lg border border-dashed border-slate-200 text-slate-500 text-xs">
              No anomalies flagged in current dataset. Click "Scan Events" to evaluate normalized events against the baseline.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="py-2.5 px-3">Event ID</th>
                    <th className="py-2.5 px-3">Anomaly Score</th>
                    <th className="py-2.5 px-3">Detected At</th>
                    <th className="py-2.5 px-3">Deterministic Explanation Reasons</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {recentAnomalies.map((anom) => (
                    <tr key={anom.id} className="hover:bg-slate-50/70">
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-900 whitespace-nowrap">
                        {anom.event_id}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono font-bold text-rose-600 text-xs">
                            {(anom.anomaly_score * 100).toFixed(1)}%
                          </span>
                          <div className="w-16 bg-slate-100 rounded-full h-1.5">
                            <div
                              className="bg-rose-500 h-1.5 rounded-full"
                              style={{ width: `${Math.min(100, anom.anomaly_score * 100)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500 whitespace-nowrap">
                        {anom.detected_at ? new Date(anom.detected_at).toISOString().replace('T', ' ').substring(0, 19) : 'N/A'}
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex flex-wrap gap-1">
                          {anom.explanation?.reasons?.map((reason, rIdx) => (
                            <span
                              key={rIdx}
                              className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200"
                            >
                              {reason}
                            </span>
                          )) || <span className="text-slate-400">Statistical outlier</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Apache Parquet Export Modal */}
      {exportModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-xl p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center space-x-2">
                <FolderTree className="w-5 h-5 text-sky-600" />
                <h3 className="font-bold text-slate-900 text-base">Apache Parquet Columnar Export</h3>
              </div>
              <button
                onClick={() => setExportModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 font-bold text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs text-slate-600">
              <p>
                Generates columnar, snappy-compressed Apache Parquet datasets partitioned strictly by timestamp
                hierarchy:
              </p>
              <div className="bg-slate-900 text-slate-200 font-mono p-3 rounded-lg text-[11px]">
                {exportStatus?.export_directory || 'data/processed'}/year=YYYY/month=MM/day=DD/events-[uuid].parquet
              </div>

              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Chunk Batch Size</span>
                  <select
                    value={batchSize}
                    onChange={(e) => setBatchSize(Number(e.target.value))}
                    className="mt-1 border border-slate-200 rounded p-1 text-xs w-full bg-white font-medium"
                  >
                    <option value={1000}>1,000 events / chunk</option>
                    <option value={5000}>5,000 events / chunk</option>
                    <option value={10000}>10,000 events / chunk</option>
                    <option value={50000}>50,000 events / chunk</option>
                  </select>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Compression</span>
                  <div className="mt-1 font-mono font-semibold text-slate-800 p-1">Snappy (Lossless)</div>
                </div>
              </div>

              {lastExportResult && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 space-y-1">
                  <div className="flex items-center space-x-1.5 text-emerald-800 font-bold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Export Completed Successfully</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[11px] text-emerald-900 font-mono pt-1">
                    <div>Records: {lastExportResult.records_exported.toLocaleString()}</div>
                    <div>Files: {lastExportResult.files_created}</div>
                    <div>Rate: {lastExportResult.records_per_second.toLocaleString()} evt/s</div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setExportModalOpen(false)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Close
              </button>
              <button
                onClick={handleExecuteExport}
                disabled={exportingInProgress}
                className="inline-flex items-center px-4 py-2 bg-sky-600 text-white rounded-lg text-xs font-semibold hover:bg-sky-700 shadow-xs transition-colors disabled:opacity-50"
              >
                <Download className={`w-3.5 h-3.5 mr-1.5 ${exportingInProgress ? 'animate-spin' : ''}`} />
                {exportingInProgress ? 'Exporting...' : 'Trigger Export'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
