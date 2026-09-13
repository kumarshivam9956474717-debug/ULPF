import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Building2,
  AlertTriangle,
  FileCheck,
  TrendingUp,
  Download,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Eye,
  FileText,
  Layers,
  BarChart3,
  ListFilter,
  X
} from 'lucide-react';
import {
  EntityAssessment,
  EvidenceChain,
  fetchSupervisoryEntities,
  fetchEntityAssessment,
  runSupervisoryAnalysis,
  fetchEvidenceChain,
  submitHumanReview,
  exportSupervisoryReport,
  fetchSupervisoryReportData
} from '../services/api';

export const SupervisoryAssessment: React.FC = () => {
  const [entities, setEntities] = useState<Array<{ entity_id: string; entity_name: string; status: string }>>([]);
  const [selectedEntityId, setSelectedEntityId] = useState<string>('CSE-ALPHA-01');
  const [assessment, setAssessment] = useState<EntityAssessment | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);

  // Assessment Report Modal State
  const [reportModalOpen, setReportModalOpen] = useState<boolean>(false);
  const [reportData, setReportData] = useState<any>(null);
  const [loadingReport, setLoadingReport] = useState<boolean>(false);
  const [reportError, setReportError] = useState<string | null>(null);

  // Evidence Chain Drill-down Modal State
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [evidenceChain, setEvidenceChain] = useState<EvidenceChain | null>(null);
  const [loadingChain, setLoadingChain] = useState<boolean>(false);
  const [reviewerName, setReviewerName] = useState<string>('Examiner-Lead');
  const [reviewStatus, setReviewStatus] = useState<string>('CONFIRMED');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);
  const [reviewSuccessMsg, setReviewSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadEntities();
    loadAssessment('CSE-ALPHA-01');
  }, []);

  const loadEntities = async () => {
    try {
      const list = await fetchSupervisoryEntities();
      setEntities(list);
    } catch (err) {
      console.error('Failed to load entities:', err);
    }
  };

  const loadAssessment = async (entityId: string) => {
    setLoading(true);
    try {
      const data = await fetchEntityAssessment(entityId);
      setAssessment(data);
    } catch (err) {
      console.error('Failed to load assessment:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    setAnalyzing(true);
    try {
      const data = await runSupervisoryAnalysis(selectedEntityId);
      setAssessment(data);
    } catch (err) {
      console.error('Failed to run supervisory analysis:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleOpenEvidenceChain = async (findingId: string) => {
    setSelectedFindingId(findingId);
    setLoadingChain(true);
    setReviewSuccessMsg(null);
    try {
      const chain = await fetchEvidenceChain(findingId);
      setEvidenceChain(chain);
      setReviewStatus(chain.indicator_summary?.status || 'CONFIRMED');
    } catch (err) {
      console.error('Failed to fetch evidence chain:', err);
    } finally {
      setLoadingChain(false);
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFindingId || !reviewNotes) return;
    setSubmittingReview(true);
    try {
      await submitHumanReview(selectedFindingId, reviewerName, reviewStatus, reviewNotes);
      setReviewSuccessMsg('Human review submitted & logged to audit trail.');
      loadAssessment(selectedEntityId);
    } catch (err) {
      console.error('Failed to submit review:', err);
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      setReportError(null);
      const blob = await exportSupervisoryReport(selectedEntityId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `supervisory_report_${selectedEntityId}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Failed to export report:', err);
      setReportError(err?.message || 'Failed to export assessment report.');
    }
  };

  const handleOpenReport = async () => {
    setLoadingReport(true);
    setReportError(null);
    setReportModalOpen(true);
    try {
      const data = await fetchSupervisoryReportData(selectedEntityId);
      setReportData(data);
    } catch (err: any) {
      console.error('Failed to load report data:', err);
      setReportError(err?.message || 'Failed to load assessment report data.');
    } finally {
      setLoadingReport(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toUpperCase()) {
      case 'CRITICAL':
      case 'PRIORITY 1':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'HIGH':
      case 'PRIORITY 2':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'MEDIUM':
      case 'PRIORITY 3':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'LOW':
      case 'ROUTINE':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px] text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mr-3 text-cyan-400" />
        <span>Loading Supervisory Intelligence Assessment Workspace...</span>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8 max-w-[1600px] mx-auto text-slate-100">
      {/* 1. Entity Overview & Header Bar */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-slate-900/80 p-6 rounded-xl border border-slate-800 backdrop-blur">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
                Supervisory Intelligence & Assessment Workspace
              </h1>
              <p className="text-slate-400 text-sm">
                Human Supervisory Assessment & Priority Review (SIH26156 NTRO Baseline)
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Entity Selector */}
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-2 rounded-lg border border-slate-700">
            <Building2 className="w-4 h-4 text-cyan-400" />
            <select
              value={selectedEntityId}
              onChange={(e) => {
                setSelectedEntityId(e.target.value);
                loadAssessment(e.target.value);
              }}
              className="bg-transparent text-sm text-slate-200 focus:outline-none cursor-pointer"
            >
              {entities.map((e) => (
                <option key={e.entity_id} value={e.entity_id} className="bg-slate-900 text-slate-200">
                  {e.entity_name} ({e.entity_id})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold px-4 py-2 rounded-lg transition"
          >
            <RefreshCw className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
            <span>{analyzing ? 'Analyzing...' : 'Run Supervisory Analysis'}</span>
          </button>

          <div className="flex items-center gap-2 border-l border-slate-700 pl-3">
            <button
              onClick={handleOpenReport}
              className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs px-3 py-2 rounded-lg shadow-sm transition"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Open Assessment Report</span>
            </button>
            <button
              onClick={() => handleExport('json')}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg border border-slate-700 transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>
            <button
              onClick={() => handleExport('csv')}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg border border-slate-700 transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>
      </div>

      {reportError && (
        <div className="p-3 bg-red-950/60 border border-red-500/40 rounded-lg text-red-300 text-xs flex justify-between items-center">
          <span>{reportError}</span>
          <button onClick={() => setReportError(null)} className="text-red-400 hover:text-red-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {assessment && (
        <>
          {/* 2. Overall Supervisory Risk Indicator */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 col-span-1 md:col-span-2">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-2">
                Overall Supervisory Risk Indicator
              </div>
              <div className="flex items-baseline gap-4">
                <div className="text-4xl font-extrabold text-slate-100">
                  {assessment.overall_score.toFixed(1)} <span className="text-sm font-normal text-slate-400">/ 100</span>
                </div>
                <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${getPriorityColor(assessment.risk_category)}`}>
                  {assessment.risk_category}
                </span>
                <span className="text-xs text-slate-400">
                  Confidence: <span className="text-slate-200 font-semibold">{(assessment.confidence * 100).toFixed(0)}%</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-3 leading-relaxed">
                {assessment.supervisory_risk_indicator.explanation}
              </p>
            </div>

            <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-2">
                Cyber Resilience Indicator
              </div>
              <div className="text-3xl font-bold text-slate-100">
                {assessment.cyber_resilience_indicator.toFixed(1)}
              </div>
              <div className="text-xs text-emerald-400 mt-2 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Multi-Source Redundancy Active</span>
              </div>
            </div>

            <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-2">
                Period-over-Period Trend
              </div>
              <div className="text-2xl font-bold text-cyan-400 flex items-center gap-2">
                <TrendingUp className="w-6 h-6" />
                <span>{assessment.trend}</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                {assessment.trend_analysis.explanation}
              </p>
            </div>
          </div>

          {/* 3. Eight Capability Dimensions Grid */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-5 h-5 text-cyan-400" />
              <span>Eight Supervisory Capability Dimensions</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {assessment.capabilities.map((cap) => (
                <div key={cap.capability_name} className="bg-slate-900/70 p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex justify-between items-start">
                    <span className="text-sm font-semibold text-slate-200">{cap.capability_name}</span>
                    <span className="text-lg font-bold text-cyan-400">{cap.score.toFixed(1)}</span>
                  </div>
                  {/* Progress Bar */}
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${cap.score >= 75 ? 'bg-cyan-500' : cap.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                      style={{ width: `${cap.score}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{cap.explanation}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 4. Priority Alert Review Samples Table */}
          <div className="bg-slate-900/80 rounded-xl border border-slate-800 p-5 space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                <ListFilter className="w-5 h-5 text-cyan-400" />
                <span>Prioritized Alert Samples for Supervisory Review</span>
              </h2>
              <span className="text-xs text-slate-400">Intelligent Sampling (Severity + Anomaly + Closure Speed)</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2.5 px-3">Priority Label</th>
                    <th className="py-2.5 px-3">Score</th>
                    <th className="py-2.5 px-3">Event ID</th>
                    <th className="py-2.5 px-3">Severity</th>
                    <th className="py-2.5 px-3">Anomaly Score</th>
                    <th className="py-2.5 px-3">Closure Speed</th>
                    <th className="py-2.5 px-3">Selection Reasons</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {assessment.priority_samples.slice(0, 10).map((s) => (
                    <tr key={s.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-2.5 px-3">
                        <span className={`px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${getPriorityColor(s.priority_label)}`}>
                          {s.priority_label}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-slate-200">{s.priority_score.toFixed(1)}</td>
                      <td className="py-2.5 px-3 font-mono text-cyan-400">{s.event_id}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${getPriorityColor(s.severity)}`}>
                          {s.severity}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {s.anomaly_score ? s.anomaly_score.toFixed(2) : '0.00'}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {s.closure_time_seconds ? `${s.closure_time_seconds.toFixed(1)}s` : 'N/A'}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {s.reasons.join('; ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 5. Execution Gaps & Negative Space Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Execution Gaps */}
            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-4">
              <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                <span>Operational Execution Gaps ({assessment.top_execution_gaps.length})</span>
              </h2>
              {assessment.top_execution_gaps.length === 0 ? (
                <p className="text-xs text-slate-500">No operational execution gaps detected.</p>
              ) : (
                <div className="space-y-3">
                  {assessment.top_execution_gaps.map((gap) => (
                    <div key={gap.id} className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/60 space-y-2">
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold text-amber-300">{gap.indicator}</span>
                        <button
                          onClick={() => handleOpenEvidenceChain(gap.id)}
                          className="flex items-center gap-1 text-[11px] text-cyan-400 hover:underline"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Drill Evidence</span>
                        </button>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">{gap.explanation}</p>
                      <div className="text-[11px] text-slate-400 bg-slate-900/50 p-2 rounded border border-slate-800">
                        <span className="text-cyan-400 font-semibold">Recommended Review: </span>
                        {gap.recommended_manual_review}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Negative Space Indicators */}
            <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-4">
              <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-400" />
                <span>Negative-Space Indicators ({assessment.negative_space_indicators.length})</span>
              </h2>
              {assessment.negative_space_indicators.length === 0 ? (
                <p className="text-xs text-slate-500">No telemetric negative-space gaps detected.</p>
              ) : (
                <div className="space-y-3">
                  {assessment.negative_space_indicators.map((neg) => (
                    <div key={neg.id} className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/60 space-y-2">
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold text-red-400">{neg.title}</span>
                        <button
                          onClick={() => handleOpenEvidenceChain(neg.id)}
                          className="flex items-center gap-1 text-[11px] text-cyan-400 hover:underline"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Drill Evidence</span>
                        </button>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">{neg.explanation}</p>
                      <div className="text-[11px] text-slate-400 bg-slate-900/50 p-2 rounded border border-slate-800">
                        <span className="text-cyan-400 font-semibold">Action: </span>
                        {neg.recommended_manual_review}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 6. Peer Benchmarking Matrix */}
          <div className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                <span>Peer Benchmarking Comparison</span>
              </h2>
              <span className="text-xs text-slate-400">
                Peer Group: <span className="text-slate-200 font-semibold">{assessment.peer_benchmarking.peer_group}</span> ({assessment.peer_benchmarking.peer_count} peers)
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {assessment.peer_benchmarking.metrics.map((m) => (
                <div key={m.metric_name} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700 space-y-2">
                  <div className="text-xs text-slate-400 font-semibold">{m.metric_name}</div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-xl font-bold text-slate-100">{m.entity_value}</span>
                    <span className="text-xs text-slate-400">Peer Median: {m.peer_median}</span>
                  </div>
                  <div className="text-[11px] text-cyan-400 font-medium bg-slate-900/50 p-1.5 rounded">
                    {m.assessment_phrase}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* 7. Evidence Chain Explorer & SHA-256 Drill-Down Modal */}
      {selectedFindingId && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full p-6 space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <FileCheck className="w-6 h-6 text-cyan-400" />
                  <span>Bi-Directional Evidence Chain & Verification</span>
                </h3>
                <p className="text-xs text-slate-400">Finding ID: {selectedFindingId}</p>
              </div>
              <button
                onClick={() => setSelectedFindingId(null)}
                className="text-slate-400 hover:text-slate-200 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            {loadingChain ? (
              <div className="flex items-center justify-center py-12 text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin mr-2 text-cyan-400" />
                <span>Assembling evidence chain & verifying SHA-256 hashes...</span>
              </div>
            ) : evidenceChain ? (
              <div className="space-y-6">
                {/* SHA-256 Verification Badge */}
                <div className={`p-4 rounded-lg border flex items-center gap-3 ${evidenceChain.sha256_verification_passed ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                  <CheckCircle2 className="w-6 h-6" />
                  <div>
                    <div className="font-semibold text-sm">
                      {evidenceChain.sha256_verification_passed ? 'SHA-256 Integrity Verification PASSED' : 'Integrity Verification FAILED'}
                    </div>
                    <div className="text-xs text-slate-400">
                      All raw log payloads match original cryptographic hashes stored at ingestion.
                    </div>
                  </div>
                </div>

                {/* Evidence Chain Flow */}
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3 font-mono text-xs text-slate-300">
                  <div className="text-cyan-400 font-bold">Evidence Chain Hierarchy:</div>
                  <div>Finding: {evidenceChain.finding_title} ({evidenceChain.finding_type})</div>
                  <div>  └─ Severity: {evidenceChain.severity} | Confidence: {(evidenceChain.confidence * 100).toFixed(0)}%</div>
                  <div>  └─ Underlying Events: {evidenceChain.underlying_event_ids.join(', ')}</div>
                  <div>  └─ Raw Event Verbatim Samples:</div>
                  {evidenceChain.raw_event_samples.map((raw) => (
                    <div key={raw.raw_event_id} className="ml-6 text-slate-400 border-l border-slate-800 pl-3 my-1">
                      <div>Raw Event ID: {raw.raw_event_id}</div>
                      <div>SHA-256 Hash: {raw.sha256_hash}</div>
                      <div className="text-slate-200">Payload Excerpt: "{raw.payload_excerpt}"</div>
                    </div>
                  ))}
                </div>

                {/* Human Examiner Review Form */}
                <form onSubmit={handleSubmitReview} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700 space-y-4">
                  <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-cyan-400" />
                    <span>Human Examiner Supervisory Review Audit Form</span>
                  </h4>

                  {reviewSuccessMsg && (
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded">
                      {reviewSuccessMsg}
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <label className="block text-slate-400 mb-1">Examiner Name</label>
                      <input
                        type="text"
                        value={reviewerName}
                        onChange={(e) => setReviewerName(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 mb-1">Decision Status</label>
                      <select
                        value={reviewStatus}
                        onChange={(e) => setReviewStatus(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200 cursor-pointer"
                      >
                        <option value="CONFIRMED">CONFIRMED</option>
                        <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                        <option value="DISMISSED">DISMISSED</option>
                        <option value="INSUFFICIENT_EVIDENCE">INSUFFICIENT_EVIDENCE</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-400 text-xs mb-1">Examiner Notes & Findings</label>
                    <textarea
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      rows={3}
                      placeholder="Enter detailed supervisory notes explaining the examiner's review decision..."
                      className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={submittingReview}
                    className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs px-4 py-2 rounded transition"
                  >
                    {submittingReview ? 'Submitting Review...' : 'Submit Review & Update Audit Trail'}
                  </button>
                </form>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Failed to load evidence chain details.</p>
            )}
          </div>
        </div>
      )}

      {/* Assessment Report Modal */}
      {reportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-slate-100">Official Supervisory Assessment Report</h3>
              </div>
              <button
                onClick={() => setReportModalOpen(false)}
                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingReport ? (
              <div className="p-8 text-center text-xs text-slate-400 font-mono flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                <span>Loading official supervisory assessment report...</span>
              </div>
            ) : reportData ? (
              <div className="space-y-4 text-xs">
                {/* Supervisory Notice */}
                <div className="p-3 bg-slate-800/60 border border-slate-700 rounded-lg text-slate-300 leading-relaxed text-[11px]">
                  <strong className="text-cyan-400">Supervisory Notice: </strong>
                  {reportData.disclaimer}
                </div>

                {/* Executive Summary Card */}
                <div className="p-4 bg-slate-800/40 rounded-lg border border-slate-700 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700 pb-2">
                    <div>
                      <div className="text-sm font-bold text-slate-100 font-mono">
                        Target Entity: {reportData.section_1_system_generated_analytics?.entity_id}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Assessment ID: {reportData.section_1_system_generated_analytics?.assessment_id}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-bold font-mono">
                        {reportData.section_1_system_generated_analytics?.risk_category} RISK
                      </span>
                      <span className="text-sm font-bold text-slate-100 font-mono bg-slate-900 px-3 py-1 rounded border border-slate-700">
                        {reportData.section_1_system_generated_analytics?.overall_score?.toFixed(1)} / 100
                      </span>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Generated: {reportData.section_1_system_generated_analytics?.generated_at || 'Current Window'} | Mode: AIR-GAPPED OFFLINE EVALUATION
                  </div>
                </div>

                {/* Section 1: System-Generated Indicators */}
                <div className="space-y-2">
                  <div className="font-semibold text-slate-200">
                    Section 1: System-Generated Analytical Indicators ({reportData.section_1_system_generated_analytics?.indicators?.length || 0})
                  </div>
                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-800 text-slate-300">
                        <tr>
                          <th className="p-2.5">Indicator Title</th>
                          <th className="p-2.5">Severity</th>
                          <th className="p-2.5">Status</th>
                          <th className="p-2.5">Empirical Explanation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 bg-slate-900/60">
                        {reportData.section_1_system_generated_analytics?.indicators?.map((ind: any) => (
                          <tr key={ind.id} className="hover:bg-slate-800/30">
                            <td className="p-2.5 font-medium text-slate-200">{ind.title}</td>
                            <td className="p-2.5">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                ind.severity === 'CRITICAL' ? 'bg-red-500/10 text-red-400' :
                                ind.severity === 'HIGH' ? 'bg-amber-500/10 text-amber-400' : 'bg-cyan-500/10 text-cyan-300'
                              }`}>
                                {ind.severity}
                              </span>
                            </td>
                            <td className="p-2.5 font-mono text-emerald-400">{ind.status}</td>
                            <td className="p-2.5 text-slate-400 leading-relaxed">{ind.explanation}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Section 2: Human Supervisory Audit Trail */}
                <div className="space-y-2">
                  <div className="font-semibold text-slate-200">
                    Section 2: Human Supervisory Conclusions & Audit Trail ({reportData.section_2_human_supervisory_conclusions?.audit_trail?.length || 0})
                  </div>
                  {reportData.section_2_human_supervisory_conclusions?.audit_trail?.length > 0 ? (
                    <div className="space-y-2">
                      {reportData.section_2_human_supervisory_conclusions.audit_trail.map((rev: any) => (
                        <div key={rev.review_id} className="p-3 bg-slate-800/40 rounded border border-slate-700 flex flex-wrap justify-between gap-2">
                          <div>
                            <span className="font-bold text-slate-200">{rev.reviewer}: </span>
                            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono text-[10px] font-bold">
                              {rev.decision}
                            </span>
                            <p className="text-slate-400 mt-1 text-[11px]">{rev.notes}</p>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono">{rev.timestamp}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 bg-slate-800/30 rounded border border-slate-800 text-slate-400">
                      No human supervisory reviews recorded yet for this entity.
                    </div>
                  )}
                </div>

                {/* Download Actions inside Modal */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
                  <div className="flex items-center gap-2 text-emerald-400 font-mono text-[11px]">
                    <ShieldCheck className="w-4 h-4" />
                    <span>Cryptographically Authenticated (Air-Gapped Assessment)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExport('json')}
                      className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Download JSON</span>
                    </button>
                    <button
                      onClick={() => handleExport('csv')}
                      className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Download CSV</span>
                    </button>
                    <button
                      onClick={() => setReportModalOpen(false)}
                      className="px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-slate-400">No report data available.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
