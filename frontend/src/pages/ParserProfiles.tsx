import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  SlidersHorizontal,
  Plus,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  History,
  Eye,
  RefreshCw,
  Shield,
  Clock,
} from 'lucide-react';
import {
  fetchMappingProfiles,
  activateMappingProfile,
  disableMappingProfile,
  testProfileOnSamples,
  fetchProfileVersionHistory,
  ProfileResponse,
  AuditLogItem,
  MappingValidationResult,
} from '../services/api';

export const ParserProfiles: React.FC = () => {
  const [profiles, setProfiles] = useState<ProfileResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Test Modal State
  const [testModalProfile, setTestModalProfile] = useState<ProfileResponse | null>(null);
  const [testLogs, setTestLogs] = useState<string>('');
  const [testing, setTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<MappingValidationResult | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // History Modal State
  const [historyModalProfile, setHistoryModalProfile] = useState<ProfileResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // View Details Modal State
  const [viewModalProfile, setViewModalProfile] = useState<ProfileResponse | null>(null);

  const loadProfiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMappingProfiles(statusFilter === 'ALL' ? undefined : statusFilter);
      setProfiles(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load mapping profiles.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfiles();
  }, [statusFilter]);

  const handleActivate = async (id: string) => {
    try {
      await activateMappingProfile(id);
      await loadProfiles();
    } catch (err: any) {
      alert(`Activation failed: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const handleDisable = async (id: string) => {
    try {
      await disableMappingProfile(id);
      await loadProfiles();
    } catch (err: any) {
      alert(`Disable failed: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const openTestModal = (profile: ProfileResponse) => {
    setTestModalProfile(profile);
    setTestResult(null);
    setTestError(null);
    setTestLogs('');
  };

  const runTest = async () => {
    if (!testModalProfile) return;
    const lines = testLogs.split('\n').map((s) => s.trim()).filter(Boolean);
    if (lines.length === 0) {
      setTestError('Please provide at least one sample log event.');
      return;
    }
    setTesting(true);
    setTestError(null);
    try {
      const res = await testProfileOnSamples({
        profile_id: testModalProfile.id,
        sample_logs: lines,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestError(err?.response?.data?.detail || err?.message || 'Profile test execution failed.');
    } finally {
      setTesting(false);
    }
  };

  const openHistoryModal = async (profile: ProfileResponse) => {
    setHistoryModalProfile(profile);
    setHistoryLoading(true);
    try {
      const res = await fetchProfileVersionHistory(profile.id);
      setAuditLogs(res);
    } catch (err: any) {
      alert(`Failed to fetch history: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2 text-sky-600 font-semibold text-xs tracking-wider uppercase mb-1">
            <SlidersHorizontal className="w-4 h-4" />
            <span>Parser Management &amp; Versioning</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Log Mapping Profiles
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Reusable, configuration-driven log parsers generated from the No-Code Onboarding engine.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={loadProfiles}
            disabled={loading}
            className="px-3.5 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm flex items-center space-x-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-600' : ''}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/onboarding"
            className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm flex items-center space-x-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Onboard New Format</span>
          </Link>
        </div>
      </div>

      {/* Filter Tabs & Stats Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-1">
          {['ALL', 'ACTIVE', 'DRAFT', 'DISABLED'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                statusFilter === status
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
        <div className="text-xs text-slate-500 flex items-center space-x-4">
          <span>Total Profiles: <strong className="text-slate-800">{profiles.length}</strong></span>
          <span>Active: <strong className="text-emerald-600">{profiles.filter((p) => p.status === 'ACTIVE').length}</strong></span>
          <span>Draft: <strong className="text-amber-600">{profiles.filter((p) => p.status === 'DRAFT').length}</strong></span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Profiles Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm flex flex-col items-center justify-center space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin text-sky-600" />
            <span>Loading profile configurations...</span>
          </div>
        ) : profiles.length === 0 ? (
          <div className="p-12 text-center">
            <Shield className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-700">No mapping profiles found</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Get started by uploading or pasting sample logs in the No-Code Onboarding wizard.
            </p>
            <Link
              to="/onboarding"
              className="mt-4 inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Launch Onboarding Wizard</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Profile &amp; Vendor</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created / Updated</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {profiles.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{p.name}</div>
                      <div className="text-[11px] text-slate-400">
                        {p.vendor} &bull; {p.product} ({p.device_type})
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-mono text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                        {p.source_format}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-mono font-semibold text-slate-700">v{p.version}</span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-1.5">
                        <div className="w-16 bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              p.confidence >= 0.85
                                ? 'bg-emerald-500'
                                : p.confidence >= 0.6
                                ? 'bg-amber-500'
                                : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.round(p.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-[11px] text-slate-700">
                          {(p.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          p.status === 'ACTIVE'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : p.status === 'DRAFT'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                      <div>{new Date(p.created_at).toLocaleDateString()}</div>
                      <div className="text-[10px] text-slate-400">
                        {new Date(p.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1">
                      <button
                        onClick={() => setViewModalProfile(p)}
                        title="View Profile Details"
                        className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => openTestModal(p)}
                        title="Test Profile"
                        className="p-1.5 text-sky-600 hover:text-sky-800 hover:bg-sky-50 rounded transition-colors"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => openHistoryModal(p)}
                        title="Version History & Audit Log"
                        className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
                      >
                        <History className="w-4 h-4" />
                      </button>

                      {p.status === 'ACTIVE' ? (
                        <button
                          onClick={() => handleDisable(p.id)}
                          title="Disable Profile"
                          className="p-1.5 text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded transition-colors"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleActivate(p.id)}
                          title="Activate Profile"
                          className="p-1.5 text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 rounded transition-colors"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* View Details Modal */}
      {viewModalProfile && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-base">{viewModalProfile.name} (v{viewModalProfile.version})</h3>
                <p className="text-xs text-slate-500">
                  {viewModalProfile.vendor} &bull; {viewModalProfile.product} &bull; {viewModalProfile.source_format}
                </p>
              </div>
              <button
                onClick={() => setViewModalProfile(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                &times; Close
              </button>
            </div>

            <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
              <div>
                <span className="font-semibold text-slate-700 uppercase tracking-wider text-[10px]">Parser Type &amp; Delimiter</span>
                <div className="mt-1 font-mono bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">
                  Type: {viewModalProfile.parser_type} | Delimiter: "{viewModalProfile.configuration?.delimiter || ' '}"
                </div>
              </div>

              <div>
                <span className="font-semibold text-slate-700 uppercase tracking-wider text-[10px]">Configured Mappings ({viewModalProfile.field_mappings.length})</span>
                <div className="mt-1 border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="p-2">Source Field</th>
                        <th className="p-2">Target UES Field</th>
                        <th className="p-2">Transform</th>
                        <th className="p-2">Classification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {viewModalProfile.field_mappings.map((m, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="p-2 font-mono text-slate-800">{m.source_field}</td>
                          <td className="p-2 font-mono text-sky-700 font-semibold">{m.target_field}</td>
                          <td className="p-2 text-slate-500 font-mono">{m.transform || 'direct'}</td>
                          <td className="p-2">
                            {m.is_custom ? (
                              <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded">Custom</span>
                            ) : (
                              <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded">Canonical</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setViewModalProfile(null)}
                className="px-4 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Profile Modal */}
      {testModalProfile && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-base">
                  Test Profile: {testModalProfile.name} (v{testModalProfile.version})
                </h3>
                <p className="text-xs text-slate-500">
                  Execute the configurable parser against sample events before activation.
                </p>
              </div>
              <button
                onClick={() => setTestModalProfile(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                &times; Close
              </button>
            </div>

            <div className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Sample Log Events (One per line)
                </label>
                <textarea
                  rows={4}
                  value={testLogs}
                  onChange={(e) => setTestLogs(e.target.value)}
                  placeholder="Paste log events matching this profile's format..."
                  className="w-full font-mono text-xs p-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              {testError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700">
                  {testError}
                </div>
              )}

              {testResult && (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2">
                    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-center">
                      <div className="text-[10px] text-slate-400 uppercase font-semibold">Total</div>
                      <div className="text-base font-bold text-slate-800">{testResult.records_tested}</div>
                    </div>
                    <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-center">
                      <div className="text-[10px] text-emerald-600 uppercase font-semibold">Success</div>
                      <div className="text-base font-bold text-emerald-700">{testResult.records_passed}</div>
                    </div>
                    <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-center">
                      <div className="text-[10px] text-rose-600 uppercase font-semibold">Failed</div>
                      <div className="text-base font-bold text-rose-700">{testResult.records_failed}</div>
                    </div>
                  </div>

                  {testResult.sample_normalized_preview && (
                    <div>
                      <span className="font-semibold text-slate-700 text-[11px]">Normalized UES Output Sample</span>
                      <pre className="mt-1 p-2.5 bg-slate-900 text-sky-300 rounded-lg font-mono text-[11px] overflow-x-auto">
                        {JSON.stringify(testResult.sample_normalized_preview, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">
                {testResult?.is_valid ? (
                  <span className="text-emerald-600 font-semibold flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Profile passed verification and can be activated.</span>
                  </span>
                ) : testResult ? (
                  <span className="text-rose-600 font-semibold flex items-center space-x-1">
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Profile has test failures. Cannot activate.</span>
                  </span>
                ) : null}
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setTestModalProfile(null)}
                  className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100"
                >
                  Close
                </button>
                <button
                  onClick={runTest}
                  disabled={testing}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm flex items-center space-x-1.5"
                >
                  <Play className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
                  <span>{testing ? 'Running Test...' : 'Run Test'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* History & Audit Modal */}
      {historyModalProfile && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-base">
                  Audit History: {historyModalProfile.name}
                </h3>
                <p className="text-xs text-slate-500">
                  Immutable lifecycle actions, version transitions, and test audit records.
                </p>
              </div>
              <button
                onClick={() => setHistoryModalProfile(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                &times; Close
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex-1 text-xs">
              {historyLoading ? (
                <div className="p-8 text-center text-slate-400">Loading audit trail...</div>
              ) : auditLogs.length === 0 ? (
                <div className="p-8 text-center text-slate-400">No audit events recorded for this profile.</div>
              ) : (
                <div className="space-y-3">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-slate-800 uppercase tracking-wider text-[10px] bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                            {log.action}
                          </span>
                          <span className="font-mono text-slate-600 font-semibold">v{log.version}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(log.timestamp).toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="text-slate-700 mt-1">{log.summary}</div>
                      {log.actor && (
                        <div className="text-[10px] text-slate-400 mt-1">Actor: {log.actor}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setHistoryModalProfile(null)}
                className="px-4 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-100"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
