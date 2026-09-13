import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Eye,
  Info,
  Zap,
  TrendingUp,
  Layers,
  Filter,
  FileSpreadsheet,
  FileJson,
  FileText,
  Check,
  X,
  Server,
  AlertOctagon,
  ShieldCheck,
} from 'lucide-react';
import {
  SecurityOverview,
  SourceHealthMetrics,
  CoverageFindingItem,
  CorrelationGroup,
  FindingResponse,
  AnalyzeRunResponse,
  fetchSecurityOverview,
  fetchSourcesHealth,
  fetchCoverageGaps,
  fetchSourceBaselines,
  fetchCorrelationCandidates,
  triggerSecurityAnalysisScan,
  fetchSecurityFindings,
  reviewFinding,
  dismissFinding,
  exportFindingsReport,
  fetchFindingsReportData,
  fetchSecurityTrends,
} from '../services/api';

type TabType = 'findings' | 'sources' | 'coverage' | 'deviations' | 'correlations';

export const SecurityAnalytics: React.FC = () => {
  const navigate = useNavigate();

  // State
  const [activeTab, setActiveTab] = useState<TabType>('findings');
  const [timeframe, setTimeframe] = useState<string>('24h');
  const [overview, setOverview] = useState<SecurityOverview | null>(null);
  const [sourcesHealth, setSourcesHealth] = useState<SourceHealthMetrics[]>([]);
  const [coverageGaps, setCoverageGaps] = useState<CoverageFindingItem[]>([]);
  const [baselines, setBaselines] = useState<Array<Record<string, any>>>([]);
  const [correlations, setCorrelations] = useState<CorrelationGroup[]>([]);
  const [findings, setFindings] = useState<FindingResponse[]>([]);
  const [trends, setTrends] = useState<{ timeframe: string; points: Array<{ timestamp: string; events: number; anomalies: number }> } | null>(null);

  const [scanning, setScanning] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  // Findings Report Modal State
  const [reportModalOpen, setReportModalOpen] = useState<boolean>(false);
  const [reportData, setReportData] = useState<any>(null);
  const [loadingReport, setLoadingReport] = useState<boolean>(false);

  // Filters for Findings
  const [statusFilter, setStatusFilter] = useState<string>('OPEN');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  // Finding Detail Modal
  const [selectedFinding, setSelectedFinding] = useState<FindingResponse | null>(null);

  const loadAllData = async () => {
    setError(null);
    try {
      const [ovData, srcData, covData, baseData, corrData, findData, trendsData] = await Promise.all([
        fetchSecurityOverview(),
        fetchSourcesHealth(),
        fetchCoverageGaps(),
        fetchSourceBaselines(),
        fetchCorrelationCandidates(15),
        fetchSecurityFindings({
          status: statusFilter || undefined,
          severity: severityFilter || undefined,
          finding_type: typeFilter || undefined,
          limit: 100,
        }),
        fetchSecurityTrends(timeframe).catch(() => null),
      ]);

      setOverview(ovData);
      setSourcesHealth(srcData);
      setCoverageGaps(covData);
      setBaselines(baseData);
      setCorrelations(corrData);
      setFindings(findData);
      if (trendsData) setTrends(trendsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load security analytics data');
    }
  };

  useEffect(() => {
    loadAllData();
  }, [timeframe, statusFilter, severityFilter, typeFilter]);

  const handleRunScan = async () => {
    setScanning(true);
    setScanMessage(null);
    try {
      const res: AnalyzeRunResponse = await triggerSecurityAnalysisScan();
      setScanMessage(`Scan completed successfully! ${res.new_findings_count} new findings generated.`);
      await loadAllData();
    } catch (err: any) {
      setError(err.message || 'Security analysis scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleOpenReport = async () => {
    setLoadingReport(true);
    setReportModalOpen(true);
    try {
      const data = await fetchFindingsReportData();
      setReportData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load findings report data');
    } finally {
      setLoadingReport(false);
    }
  };

  const handleReview = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const updated = await reviewFinding(id);
      setFindings((prev) => prev.map((f) => (f.id === id ? updated : f)));
      if (selectedFinding?.id === id) setSelectedFinding(updated);
      setScanMessage(`Finding '${id.slice(0, 8)}...' marked as REVIEWED.`);
      fetchSecurityOverview().then(setOverview).catch(() => {});
    } catch (err: any) {
      setError(`Review failed: ${err.message}`);
    }
  };

  const handleDismiss = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const updated = await dismissFinding(id);
      setFindings((prev) => prev.map((f) => (f.id === id ? updated : f)));
      if (selectedFinding?.id === id) setSelectedFinding(updated);
      setScanMessage(`Finding '${id.slice(0, 8)}...' marked as DISMISSED.`);
      fetchSecurityOverview().then(setOverview).catch(() => {});
    } catch (err: any) {
      setError(`Dismiss failed: ${err.message}`);
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    setExporting(true);
    try {
      const blob = await exportFindingsReport(format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ulpf_security_findings.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setScanMessage(`Report exported successfully as ${format.toUpperCase()}.`);
    } catch (err: any) {
      setError(`Export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const getPriorityBadgeClass = (category: string) => {
    switch (category) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MEDIUM':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'LOW':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getHealthBadgeClass = (status: string) => {
    switch (status) {
      case 'HEALTHY':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'DEGRADED':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'SUSPICIOUS':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'INACTIVE':
      default:
        return 'bg-red-100 text-red-800 border-red-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-6 h-6 text-sky-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Security Analytics & Data Quality Intelligence
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Offline supervisory findings, negative-space coverage gap analysis, baseline deviations, and cross-source correlations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 focus:ring-2 focus:ring-sky-500 focus:outline-none"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>

          <button
            onClick={handleRunScan}
            disabled={scanning}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
            <span>{scanning ? 'Scanning...' : 'Run Analytics Scan'}</span>
          </button>

          <button
            onClick={handleOpenReport}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
            title="Open Interactive Findings Report"
          >
            <FileText className="w-3.5 h-3.5 text-sky-400" />
            <span>Open Findings Report</span>
          </button>

          <div className="flex items-center space-x-1 border border-slate-200 rounded-lg overflow-hidden bg-slate-50">
            <button
              onClick={() => handleExport('json')}
              disabled={exporting}
              className="px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200 flex items-center space-x-1"
              title="Export Report as JSON"
            >
              <FileJson className="w-3.5 h-3.5 text-slate-600" />
              <span>JSON</span>
            </button>
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting}
              className="px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200 flex items-center space-x-1 border-l border-slate-200"
              title="Export Report as CSV"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
              <span>CSV</span>
            </button>
          </div>
        </div>
      </div>

      {scanMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs font-medium flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{scanMessage}</span>
          </div>
          <button onClick={() => setScanMessage(null)} className="text-emerald-600 hover:text-emerald-800 font-bold">×</button>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs font-medium flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <XCircle className="w-4 h-4 text-red-600" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800 font-bold">×</button>
        </div>
      )}

      {/* Top Overview KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
        {/* Quality Index */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Data Quality Index</span>
            <SparklesIcon className="w-4 h-4 text-sky-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{overview?.data_quality_index ?? 100}%</span>
            <span className="text-[10px] font-semibold text-emerald-600">Optimal</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-sky-500 h-1.5 rounded-full"
              style={{ width: `${overview?.data_quality_index ?? 100}%` }}
            />
          </div>
        </div>

        {/* Source Health */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Log Sources Health</span>
            <Server className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{overview?.healthy_sources_count ?? 0}</span>
            <span className="text-xs text-slate-500">/ {overview?.total_sources ?? 0} Healthy</span>
          </div>
          <div className="text-[11px] font-medium text-slate-500 mt-1 flex space-x-2">
            <span className="text-amber-600">{overview?.degraded_sources_count ?? 0} Degraded</span>
            <span className="text-red-600">{overview?.inactive_sources_count ?? 0} Inactive</span>
          </div>
        </div>

        {/* Open Findings */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Supervisory Findings</span>
            <ShieldAlert className="w-4 h-4 text-orange-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{overview?.open_findings_count ?? 0}</span>
            <span className="text-xs font-semibold text-red-600">{overview?.critical_findings_count ?? 0} Critical</span>
          </div>
          <div className="text-[11px] font-medium text-slate-500 mt-1">
            <span>{overview?.high_findings_count ?? 0} High Priority</span>
          </div>
        </div>

        {/* Negative-Space Gaps */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Monitoring Gaps</span>
            <AlertOctagon className="w-4 h-4 text-purple-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{coverageGaps.length}</span>
            <span className="text-xs text-purple-600 font-semibold">Gaps Detected</span>
          </div>
          <div className="text-[11px] font-medium text-slate-500 mt-1">
            <span>Negative-Space Analysis</span>
          </div>
        </div>

        {/* Correlations */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Correlations</span>
            <Layers className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{correlations.length}</span>
            <span className="text-xs text-indigo-600 font-semibold">Candidates</span>
          </div>
          <div className="text-[11px] font-medium text-slate-500 mt-1">
            <span>Multi-Vendor Shared IPs</span>
          </div>
        </div>

        {/* Statistical Anomalies */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Statistical Anomalies</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-900">{overview?.anomaly_count ?? 0}</span>
            <span className="text-xs text-amber-600 font-semibold">Outliers</span>
          </div>
          <div className="text-[11px] font-medium text-slate-500 mt-1">
            <span>Isolation Forest</span>
          </div>
        </div>
      </div>

      {/* Activity Trends Bar */}
      {trends && trends.points && trends.points.length > 0 && (
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-3 text-xs">
            <div className="flex items-center space-x-2 font-semibold text-slate-700">
              <TrendingUp className="w-4 h-4 text-sky-600" />
              <span>Telemetry Ingestion & Event Velocity Trend ({trends.timeframe})</span>
            </div>
            <span className="text-slate-400 font-mono text-[11px]">
              {trends.points.reduce((acc, p) => acc + p.events, 0).toLocaleString()} Total Events Ingested
            </span>
          </div>
          <div className="flex items-end gap-1.5 h-16 pt-2 overflow-x-auto">
            {trends.points.slice(-24).map((pt, pIdx) => {
              const maxEvt = Math.max(...trends.points.map((p) => p.events), 1);
              const heightPct = Math.max(8, (pt.events / maxEvt) * 100);
              return (
                <div key={pIdx} className="flex-1 min-w-[20px] flex flex-col items-center group relative">
                  <div
                    className="w-full bg-sky-500 hover:bg-sky-600 rounded-t transition-all cursor-pointer"
                    style={{ height: `${heightPct}%` }}
                  />
                  <div className="hidden group-hover:block absolute bottom-full mb-2 z-10 p-2 bg-slate-900 text-white rounded text-[10px] whitespace-nowrap shadow-lg font-mono">
                    <div>{pt.timestamp}</div>
                    <div className="text-sky-400 font-bold">{pt.events.toLocaleString()} events</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="flex flex-wrap items-center px-4 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('findings')}
            className={`px-4 py-3 text-xs font-bold transition-all border-b-2 flex items-center space-x-2 ${
              activeTab === 'findings'
                ? 'border-sky-600 text-sky-600 bg-sky-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Supervisory Findings ({findings.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('sources')}
            className={`px-4 py-3 text-xs font-bold transition-all border-b-2 flex items-center space-x-2 ${
              activeTab === 'sources'
                ? 'border-sky-600 text-sky-600 bg-sky-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Server className="w-4 h-4" />
            <span>Source Health Matrix ({sourcesHealth.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('coverage')}
            className={`px-4 py-3 text-xs font-bold transition-all border-b-2 flex items-center space-x-2 ${
              activeTab === 'coverage'
                ? 'border-sky-600 text-sky-600 bg-sky-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <AlertOctagon className="w-4 h-4" />
            <span>Coverage & Negative-Space ({coverageGaps.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('deviations')}
            className={`px-4 py-3 text-xs font-bold transition-all border-b-2 flex items-center space-x-2 ${
              activeTab === 'deviations'
                ? 'border-sky-600 text-sky-600 bg-sky-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>Baseline Deviations ({baselines.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('correlations')}
            className={`px-4 py-3 text-xs font-bold transition-all border-b-2 flex items-center space-x-2 ${
              activeTab === 'correlations'
                ? 'border-sky-600 text-sky-600 bg-sky-50/50'
                : 'border-transparent text-slate-500 hover:text-slate-900'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Cross-Source Correlations ({correlations.length})</span>
          </button>
        </div>

        {/* Tab 1: Supervisory Findings Table */}
        {activeTab === 'findings' && (
          <div className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
              <div className="flex items-center space-x-3">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700"
                >
                  <option value="">All Statuses</option>
                  <option value="OPEN">Status: OPEN</option>
                  <option value="REVIEWED">Status: REVIEWED</option>
                  <option value="DISMISSED">Status: DISMISSED</option>
                </select>

                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700"
                >
                  <option value="">All Severities</option>
                  <option value="CRITICAL">Severity: CRITICAL</option>
                  <option value="HIGH">Severity: HIGH</option>
                  <option value="MEDIUM">Severity: MEDIUM</option>
                  <option value="LOW">Severity: LOW</option>
                </select>

                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700"
                >
                  <option value="">All Finding Types</option>
                  <option value="SOURCE_GAP">SOURCE_GAP</option>
                  <option value="VOLUME_SPIKE">VOLUME_SPIKE</option>
                  <option value="VOLUME_DROP">VOLUME_DROP</option>
                  <option value="CORRELATION">CORRELATION</option>
                  <option value="COVERAGE_GAP">COVERAGE_GAP</option>
                  <option value="ANOMALY">ANOMALY</option>
                  <option value="DATA_QUALITY">DATA_QUALITY</option>
                </select>
              </div>

              <span className="text-xs font-medium text-slate-500">
                Displaying {findings.length} prioritized finding(s)
              </span>
            </div>

            {findings.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-500 mb-2 opacity-60" />
                <p className="text-sm font-semibold text-slate-600">No active findings match the selected filters.</p>
                <p className="text-xs mt-1">Run an analytics scan or adjust query filters above.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Priority Score</th>
                      <th className="py-3 px-4">Finding Title & Explanation</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Confidence</th>
                      <th className="py-3 px-4">First / Last Seen</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {findings.map((f) => (
                      <tr
                        key={f.id}
                        onClick={() => setSelectedFinding(f)}
                        className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                      >
                        <td className="py-3 px-4 font-mono font-bold whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs border font-semibold ${getPriorityBadgeClass(f.priority_category)}`}>
                            {f.priority_score.toFixed(1)} / 100 ({f.priority_category})
                          </span>
                        </td>
                        <td className="py-3 px-4 max-w-md">
                          <div className="font-semibold text-slate-900">{f.title}</div>
                          <div className="text-slate-500 text-[11px] truncate mt-0.5">{f.explanation}</div>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                          <span className="px-2 py-0.5 bg-slate-100 rounded text-[11px] border border-slate-200">
                            {f.finding_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-700 whitespace-nowrap">
                          {(f.confidence * 100).toFixed(0)}%
                        </td>
                        <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                          {new Date(f.created_at).toLocaleTimeString()}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${
                              f.status === 'OPEN'
                                ? 'bg-red-50 text-red-700 border-red-200'
                                : f.status === 'REVIEWED'
                                ? 'bg-sky-50 text-sky-700 border-sky-200'
                                : 'bg-slate-100 text-slate-600 border-slate-200'
                            }`}
                          >
                            {f.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap space-x-1">
                          <button
                            onClick={(e) => handleReview(f.id, e)}
                            className="p-1 text-slate-400 hover:text-sky-600 hover:bg-sky-50 rounded"
                            title="Mark as Reviewed"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => handleDismiss(f.id, e)}
                            className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"
                            title="Dismiss Finding"
                          >
                            <X className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setSelectedFinding(f)}
                            className="p-1 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded"
                            title="View Evidence & Rationale"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Source Health Matrix */}
        {activeTab === 'sources' && (
          <div className="p-6">
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Source Emitter</th>
                    <th className="py-3 px-4">Vendor & Device</th>
                    <th className="py-3 px-4">Total Events</th>
                    <th className="py-3 px-4">Events / Hour</th>
                    <th className="py-3 px-4">Parsing Success</th>
                    <th className="py-3 px-4">Anomaly Rate</th>
                    <th className="py-3 px-4">Ingestion Gap</th>
                    <th className="py-3 px-4">Status Rationale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {sourcesHealth.map((s) => (
                    <tr key={s.source_id} className="hover:bg-slate-50/80">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs border font-bold ${getHealthBadgeClass(s.status)}`}>
                          {s.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-900">
                        {s.name}
                        <div className="text-[10px] font-mono text-slate-400 font-normal">{s.source_id}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-700 font-medium">
                        {s.vendor} ({s.device_type})
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold">{s.total_events.toLocaleString()}</td>
                      <td className="py-3 px-4 font-mono text-slate-600">{s.events_per_hour.toFixed(1)}/hr</td>
                      <td className="py-3 px-4 font-mono font-semibold text-emerald-600">{s.parsing_success_rate}%</td>
                      <td className="py-3 px-4 font-mono text-amber-600 font-semibold">{s.anomaly_rate}%</td>
                      <td className="py-3 px-4 font-mono text-slate-600">
                        {s.ingestion_gap_duration_minutes > 999
                          ? 'Never'
                          : `${s.ingestion_gap_duration_minutes.toFixed(1)} mins`}
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px] max-w-xs truncate">{s.status_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Negative-Space & Coverage Analysis */}
        {activeTab === 'coverage' && (
          <div className="p-6 space-y-4">
            <div className="text-xs text-slate-500 mb-2">
              Negative-space detection identifies silent sources, telemetry drops, and absent categories without asserting attack attribution.
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {coverageGaps.map((item, idx) => (
                <div key={idx} className="bg-white p-5 rounded-xl border border-purple-100 shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="px-2.5 py-1 bg-purple-100 text-purple-800 text-xs font-bold rounded-md border border-purple-200">
                        {item.finding_type}
                      </span>
                      <span className="text-xs font-mono text-slate-400">Confidence: {(item.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 mb-1">{item.entity}</h3>
                    <p className="text-xs text-slate-600 mb-3">{item.reason}</p>
                  </div>
                  <div className="pt-3 border-t border-slate-100 text-[11px] font-mono text-slate-500 flex justify-between">
                    <span>Window: {item.time_window}</span>
                    <span className="text-purple-600 font-semibold">Requires Supervisory Review</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Baseline Deviations */}
        {activeTab === 'deviations' && (
          <div className="p-6 space-y-4">
            {baselines.map((b, idx) => (
              <div key={idx} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Source Baseline: {b.source_id}</h3>
                    <p className="text-xs text-slate-500">
                      14-Day Hourly Volume: Avg {b.avg_hourly_volume?.toFixed(1)} | StdDev {b.stddev_hourly_volume?.toFixed(1)}
                    </p>
                  </div>
                  <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2.5 py-1 rounded">
                    {b.sample_hours_count} Sample Hours
                  </span>
                </div>

                {b.deviations && b.deviations.length > 0 ? (
                  <div className="space-y-2">
                    {b.deviations.map((d: any, dIdx: number) => (
                      <div key={dIdx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                          <span className="font-semibold text-amber-900">{d.explanation}</span>
                        </div>
                        <span className="font-mono text-amber-700 font-bold whitespace-nowrap">z-score: {d.z_score}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-emerald-600 font-medium flex items-center space-x-1">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span>Operating within expected 14-day baseline statistical bounds.</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tab 5: Cross-Source Correlations */}
        {activeTab === 'correlations' && (
          <div className="p-6 space-y-4">
            {correlations.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                <Layers className="w-10 h-10 mx-auto text-indigo-400 mb-2 opacity-60" />
                <p className="text-sm font-semibold text-slate-600">No multi-vendor correlation candidates detected in recent window.</p>
              </div>
            ) : (
              correlations.map((c) => (
                <div key={c.correlation_id} className="bg-white p-5 rounded-xl border border-indigo-100 shadow-sm space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div className="flex items-center space-x-2">
                      <span className="px-2.5 py-1 bg-indigo-100 text-indigo-800 font-mono text-xs font-bold rounded">
                        {c.matching_key}
                      </span>
                      <span className="text-xs text-slate-500">
                        {c.event_count} events across {c.distinct_sources_count} vendors ({c.distinct_vendors.join(', ')})
                      </span>
                    </div>
                    <span className="text-xs font-mono text-slate-400">Candidate ID: {c.correlation_id}</span>
                  </div>

                  <p className="text-xs text-slate-700">{c.explanation}</p>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                    <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Matching Events Preview ({c.events_preview.length})
                    </div>
                    <div className="space-y-1 font-mono text-[11px]">
                      {c.events_preview.map((ep, epIdx) => (
                        <div key={epIdx} className="flex items-center justify-between text-slate-700 py-0.5">
                          <span>
                            [{ep.vendor}] {ep.source_ip} → {ep.destination_ip}:{ep.destination_port} ({ep.action})
                          </span>
                          <span className="text-slate-400">{ep.timestamp ? new Date(ep.timestamp).toLocaleTimeString() : ''}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Finding Detail Evidence Drawer/Modal */}
      {selectedFinding && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-3xl rounded-2xl border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center space-x-3">
                <ShieldAlert className="w-6 h-6 text-sky-600" />
                <div>
                  <h2 className="text-lg font-bold text-slate-900">{selectedFinding.title}</h2>
                  <div className="text-xs font-mono text-slate-500 mt-0.5">Finding ID: {selectedFinding.id}</div>
                </div>
              </div>
              <button
                onClick={() => setSelectedFinding(null)}
                className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              {/* Prioritization & Metadata */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div>
                  <div className="text-[11px] font-semibold text-slate-400">Risk Priority</div>
                  <div className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-bold border ${getPriorityBadgeClass(selectedFinding.priority_category)}`}>
                      {selectedFinding.priority_score.toFixed(1)} ({selectedFinding.priority_category})
                    </span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-slate-400">Confidence</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">{(selectedFinding.confidence * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-slate-400">Finding Type</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">{selectedFinding.finding_type}</div>
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-slate-400">Status</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">{selectedFinding.status}</div>
                </div>
              </div>

              {/* Rationale & Explanation */}
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                  <Info className="w-4 h-4 text-sky-600" />
                  <span>Explainability & Rationale</span>
                </h3>
                <div className="p-4 bg-sky-50/60 border border-sky-200 rounded-xl text-slate-800 leading-relaxed font-medium">
                  {selectedFinding.explanation}
                </div>
              </div>

              {/* Recommended Action */}
              {selectedFinding.recommended_action && (
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Recommended Action</span>
                  </h3>
                  <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-xl text-emerald-900 font-medium">
                    {selectedFinding.recommended_action}
                  </div>
                </div>
              )}

              {/* Data Evidence JSON */}
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                  <FileJson className="w-4 h-4 text-slate-600" />
                  <span>Evidence Data Payload</span>
                </h3>
                <pre className="p-4 bg-slate-900 text-slate-200 rounded-xl font-mono text-[11px] overflow-x-auto max-h-48">
                  {JSON.stringify(selectedFinding.evidence, null, 2)}
                </pre>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <button
                onClick={() => {
                  navigate('/events', {
                    state: {
                      search: selectedFinding.source_id || selectedFinding.finding_type,
                    },
                  });
                }}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-semibold shadow-sm transition-all"
              >
                <ExternalLink className="w-4 h-4 text-sky-400" />
                <span>Drill Down to Events Explorer</span>
              </button>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleReview(selectedFinding.id)}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg font-semibold shadow-sm transition-all"
                >
                  Mark Reviewed
                </button>
                <button
                  onClick={() => handleDismiss(selectedFinding.id)}
                  className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-semibold transition-all"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Findings Report Modal */}
      {reportModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-4xl rounded-2xl border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center space-x-3">
                <FileText className="w-6 h-6 text-sky-600" />
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    {reportData?.report_title || 'Security Analytics Supervisory Report'}
                  </h2>
                  <div className="text-xs font-mono text-slate-500 mt-0.5">
                    Generated: {reportData?.generation_timestamp ? new Date(reportData.generation_timestamp).toLocaleString() : 'Current Window'} | Mode: AIR-GAPPED EVALUATION
                  </div>
                </div>
              </div>
              <button
                onClick={() => setReportModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              {loadingReport ? (
                <div className="p-12 text-center text-slate-400 flex items-center justify-center space-x-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-sky-600" />
                  <span>Loading supervisory findings report...</span>
                </div>
              ) : reportData ? (
                <>
                  {/* Disclaimer & Methodology */}
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-slate-600 leading-relaxed">
                    <div>
                      <strong className="text-slate-900">Supervisory Notice: </strong>
                      {reportData.disclaimer}
                    </div>
                    <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-200">
                      <strong>Methodology: </strong>
                      {reportData.analytical_methodology}
                    </div>
                  </div>

                  {/* Summary Metric */}
                  <div className="flex items-center justify-between p-4 bg-sky-50 rounded-xl border border-sky-100 text-sky-900">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-sky-700">Total Supervised Findings</span>
                      <div className="text-2xl font-bold">{reportData.total_findings || 0}</div>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-semibold">
                      <span className="px-2.5 py-1 bg-red-100 text-red-800 rounded border border-red-200">
                        {reportData.findings?.filter((f: any) => f.severity === 'CRITICAL').length || 0} Critical
                      </span>
                      <span className="px-2.5 py-1 bg-orange-100 text-orange-800 rounded border border-orange-200">
                        {reportData.findings?.filter((f: any) => f.severity === 'HIGH').length || 0} High
                      </span>
                      <span className="px-2.5 py-1 bg-amber-100 text-amber-800 rounded border border-amber-200">
                        {reportData.findings?.filter((f: any) => f.severity === 'MEDIUM').length || 0} Medium
                      </span>
                    </div>
                  </div>

                  {/* Findings Table */}
                  <div className="overflow-x-auto rounded-lg border border-slate-200">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                        <tr>
                          <th className="py-2.5 px-3">Priority Score</th>
                          <th className="py-2.5 px-3">Type</th>
                          <th className="py-2.5 px-3">Title & Explanation</th>
                          <th className="py-2.5 px-3">Source ID</th>
                          <th className="py-2.5 px-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {reportData.findings?.map((f: any) => (
                          <tr key={f.id} className="hover:bg-slate-50/80">
                            <td className="py-2.5 px-3 font-mono font-bold whitespace-nowrap">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] border font-semibold ${getPriorityBadgeClass(f.priority_category)}`}>
                                {f.priority_score?.toFixed(1)} ({f.priority_category})
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                              {f.finding_type}
                            </td>
                            <td className="py-2.5 px-3 max-w-sm">
                              <div className="font-semibold text-slate-900">{f.title}</div>
                              <div className="text-slate-500 text-[11px] truncate mt-0.5">{f.explanation}</div>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px] whitespace-nowrap">
                              {f.source_id || 'N/A (Multi)'}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[11px] font-semibold border border-slate-200">
                                {f.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div className="p-8 text-center text-slate-400">No report data found.</div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-emerald-700 text-xs font-semibold">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Deterministic SIH26156 Air-Gapped Supervisory Output</span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleExport('json')}
                  className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg font-semibold text-xs flex items-center space-x-1"
                >
                  <FileJson className="w-3.5 h-3.5 text-slate-600" />
                  <span>Download JSON</span>
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg font-semibold text-xs flex items-center space-x-1"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Download CSV</span>
                </button>
                <button
                  onClick={() => setReportModalOpen(false)}
                  className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-semibold text-xs transition-all"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v3m0 12v3m9-9h-3M6 12H3m15.364-6.364l-2.121 2.121M7.757 16.243l-2.121 2.121m12.728 0l-2.121-2.121M7.757 7.757L5.636 5.636" />
    </svg>
  );
}

export default SecurityAnalytics;
