import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Layers,
  Search,
  Filter,
  RefreshCw,
  Eye,
  CheckCircle,
  AlertTriangle,
  FileCode,
  Shield,
  ArrowRight,
  Hash,
  Copy,
  Check
} from 'lucide-react';
import {
  fetchEvents,
  fetchRawEventTraceability,
  UniversalEventItem,
  RawEventTraceability
} from '../services/api';

export const Events: React.FC = () => {
  const location = useLocation();
  const [events, setEvents] = useState<UniversalEventItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [vendorFilter, setVendorFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [actionFilter, setActionFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>((location.state as any)?.search || '');
  const [page, setPage] = useState<number>(0);
  const pageSize = 25;

  // Drawer / Traceability Modal
  const [selectedEvent, setSelectedEvent] = useState<UniversalEventItem | null>(null);
  const [rawTrace, setRawTrace] = useState<RawEventTraceability | null>(null);
  const [loadingTrace, setLoadingTrace] = useState<boolean>(false);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);
  const [copiedPayload, setCopiedPayload] = useState<boolean>(false);

  const loadEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEvents({
        limit: pageSize,
        offset: page * pageSize,
        vendor: vendorFilter || undefined,
        severity: severityFilter || undefined,
        action: actionFilter || undefined,
      });
      setEvents(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load events.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [page, vendorFilter, severityFilter, actionFilter]);

  const handleOpenTrace = async (event: UniversalEventItem) => {
    setSelectedEvent(event);
    setLoadingTrace(true);
    setTraceError(null);
    setRawTrace(null);
    setCopiedHash(false);
    setCopiedPayload(false);

    try {
      const trace = await fetchRawEventTraceability(event.event_id);
      setRawTrace(trace);
    } catch (err: any) {
      setTraceError(err.message || 'Failed to load raw event traceability record.');
    } finally {
      setLoadingTrace(false);
    }
  };

  const copyToClipboard = (text: string, type: 'hash' | 'payload') => {
    navigator.clipboard.writeText(text);
    if (type === 'hash') {
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    } else {
      setCopiedPayload(true);
      setTimeout(() => setCopiedPayload(false), 2000);
    }
  };

  const getSeverityBadge = (severity?: string | null) => {
    const s = (severity || 'unknown').toLowerCase();
    switch (s) {
      case 'critical':
      case '1':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'high':
      case '2':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'medium':
      case '3':
      case '4':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'low':
      case '5':
      case '6':
        return 'bg-sky-50 text-sky-700 border-sky-200';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  const getActionBadge = (action?: string | null) => {
    const a = (action || '').toLowerCase();
    if (a.includes('block') || a.includes('drop') || a.includes('deny')) {
      return 'bg-rose-50 text-rose-700 border-rose-200';
    }
    if (a.includes('allow') || a.includes('permit') || a.includes('pass')) {
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
    return 'bg-slate-50 text-slate-700 border-slate-200';
  };

  const filteredEvents = events.filter((e) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (e.event_id && e.event_id.toLowerCase().includes(term)) ||
      (e.source_ip && e.source_ip.toLowerCase().includes(term)) ||
      (e.destination_ip && e.destination_ip.toLowerCase().includes(term)) ||
      (e.vendor && e.vendor.toLowerCase().includes(term)) ||
      (e.product && e.product.toLowerCase().includes(term)) ||
      (e.message && e.message.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-sky-50 text-sky-600 rounded-lg border border-sky-100">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Universal Normalized Events</h2>
            <p className="text-sm text-slate-500">
              Query standardized, analytics-ready security events adhering to Universal Event Schema (UES).
            </p>
          </div>
        </div>

        <button
          onClick={loadEvents}
          disabled={loading}
          className="inline-flex items-center px-3.5 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition-colors"
        >
          <RefreshCw className={`w-4 h-4 mr-2 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
          Refresh Feed
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-2 flex-1 min-w-[260px] max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search IP, Event ID, Vendor, or Message..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-slate-50/50"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 text-xs text-slate-500">
            <Filter className="w-3.5 h-3.5" />
            <span className="font-semibold">Filters:</span>
          </div>

          <select
            value={vendorFilter}
            onChange={(e) => {
              setVendorFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">All Vendors</option>
            <option value="cisco">Cisco</option>
            <option value="fortinet">Fortinet</option>
            <option value="paloalto">Palo Alto</option>
            <option value="checkpoint">Check Point</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="informational">Informational</option>
          </select>

          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">All Actions</option>
            <option value="allowed">Allowed / Permit</option>
            <option value="blocked">Blocked / Deny</option>
            <option value="dropped">Dropped</option>
          </select>
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center">
            <RefreshCw className="w-8 h-8 mx-auto text-sky-600 animate-spin mb-3" />
            <p className="text-sm font-medium text-slate-600">Retrieving normalized events from PostgreSQL...</p>
          </div>
        ) : error ? (
          <div className="py-12 text-center text-rose-600 px-4">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="text-sm font-semibold">{error}</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="py-16 text-center text-slate-500">
            <Layers className="w-10 h-10 mx-auto mb-3 text-slate-300" />
            <p className="text-sm font-medium text-slate-700">No events found matching criteria</p>
            <p className="text-xs text-slate-400 mt-1">
              Try adjusting filters or send logs via Ingestion Engine / Live Syslog listener.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-slate-500 font-medium">
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">Vendor / Device</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Source $\rightarrow$ Destination</th>
                  <th className="py-3 px-4">Protocol</th>
                  <th className="py-3 px-4">Event ID</th>
                  <th className="py-3 px-4 text-right">Traceability</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredEvents.map((evt) => (
                  <tr key={evt.event_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                      {evt.timestamp ? new Date(evt.timestamp).toISOString().replace('T', ' ').substring(0, 19) : 'N/A'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="font-semibold text-slate-900">{evt.vendor || 'Unknown'}</span>
                      {evt.product && <span className="text-slate-400 ml-1">({evt.product})</span>}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${getSeverityBadge(evt.severity)}`}>
                        {evt.severity || 'unknown'}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${getActionBadge(evt.action)}`}>
                        {evt.action || 'unknown'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600 whitespace-nowrap">
                      <span>{evt.source_ip || '*'}:{evt.source_port ?? '*'}</span>
                      <ArrowRight className="w-3 h-3 inline mx-1.5 text-slate-400" />
                      <span>{evt.destination_ip || '*'}:{evt.destination_port ?? '*'}</span>
                    </td>
                    <td className="py-3 px-4 uppercase font-mono font-medium text-slate-600 whitespace-nowrap">
                      {evt.protocol || 'N/A'}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                      {evt.event_id.substring(0, 14)}...
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => handleOpenTrace(evt)}
                        className="inline-flex items-center px-2.5 py-1 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 rounded border border-sky-200 transition-colors shadow-xs"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1" />
                        Trace Raw
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="p-3.5 bg-slate-50/50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing page <span className="font-semibold text-slate-800">{page + 1}</span> (Max {pageSize} per page)
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0 || loading}
              className="px-3 py-1 bg-white border border-slate-200 rounded font-medium text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={events.length < pageSize || loading}
              className="px-3 py-1 bg-white border border-slate-200 rounded font-medium text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Raw Traceability & Event Details Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-sky-50 text-sky-700 rounded-lg border border-sky-100">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">Normalized Event Traceability Dossier</h3>
                  <p className="text-xs text-slate-500 font-mono">Event ID: {selectedEvent.event_id}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-slate-700 text-sm font-semibold px-2 py-1 rounded"
              >
                ✕ Close
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 text-xs">
              {/* Cryptographic Traceability Guarantee Card */}
              <div className="bg-sky-50/40 border border-sky-200 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-sky-600" />
                    <span className="font-bold text-sky-900 text-sm">Air-Gapped Raw-to-Normalized Traceability</span>
                  </div>
                  {rawTrace?.integrity?.verified && (
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded font-semibold text-[11px] flex items-center">
                      <Check className="w-3 h-3 mr-1" /> SHA-256 Verified
                    </span>
                  )}
                </div>

                {loadingTrace ? (
                  <div className="py-4 text-center text-slate-500">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-1 text-sky-600" />
                    <span>Resolving raw event record and verifying cryptographic hash...</span>
                  </div>
                ) : traceError ? (
                  <div className="p-3 bg-rose-50 text-rose-700 border border-rose-200 rounded">
                    {traceError}
                  </div>
                ) : rawTrace ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-white p-3 rounded-lg border border-sky-100">
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase font-semibold">Raw Event Pointer</span>
                        <span className="font-mono text-slate-800 font-medium">{rawTrace.raw_event_id}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase font-semibold">Source Identifier</span>
                        <span className="font-mono text-slate-800 font-medium">{rawTrace.source_id}</span>
                      </div>
                      <div className="md:col-span-2">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-slate-400 text-[10px] uppercase font-semibold flex items-center">
                            <Hash className="w-3 h-3 mr-1 text-slate-400" /> Cryptographic SHA-256 Digest
                          </span>
                          <button
                            onClick={() => copyToClipboard(rawTrace.payload_hash_sha256, 'hash')}
                            className="text-sky-600 hover:text-sky-800 flex items-center text-[11px]"
                          >
                            {copiedHash ? <Check className="w-3 h-3 mr-1 text-emerald-600" /> : <Copy className="w-3 h-3 mr-1" />}
                            {copiedHash ? 'Copied' : 'Copy Hash'}
                          </button>
                        </div>
                        <code className="block bg-slate-50 p-2 rounded border border-slate-200 font-mono text-[11px] text-slate-800 break-all">
                          {rawTrace.payload_hash_sha256}
                        </code>
                      </div>
                    </div>

                    {/* Original Raw Payload */}
                    <div>
                      <div className="flex items-center justify-between mb-1 mt-3">
                        <span className="text-slate-700 font-semibold flex items-center">
                          <FileCode className="w-3.5 h-3.5 mr-1 text-slate-500" /> Original Immutable Raw Payload
                        </span>
                        <button
                          onClick={() => copyToClipboard(rawTrace.raw_payload, 'payload')}
                          className="text-sky-600 hover:text-sky-800 flex items-center text-[11px]"
                        >
                          {copiedPayload ? <Check className="w-3 h-3 mr-1 text-emerald-600" /> : <Copy className="w-3 h-3 mr-1" />}
                          {copiedPayload ? 'Copied' : 'Copy Payload'}
                        </button>
                      </div>
                      <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg font-mono text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed">
                        {rawTrace.raw_payload}
                      </pre>
                    </div>
                  </div>
                ) : null}
              </div>

              {/* Universal Event Schema Breakdown */}
              <div className="space-y-3">
                <h4 className="font-bold text-slate-800 text-sm">Canonical UES Field Mapping</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Vendor</span>
                    <span className="font-semibold text-slate-900">{selectedEvent.vendor || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Product</span>
                    <span className="font-semibold text-slate-900">{selectedEvent.product || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Device Type</span>
                    <span className="font-semibold text-slate-900">{selectedEvent.device_type || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Severity</span>
                    <span className="font-semibold text-slate-900">{selectedEvent.severity || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Source IP:Port</span>
                    <span className="font-mono text-slate-900 font-semibold">{selectedEvent.source_ip || '*'}:{selectedEvent.source_port ?? '*'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Dest IP:Port</span>
                    <span className="font-mono text-slate-900 font-semibold">{selectedEvent.destination_ip || '*'}:{selectedEvent.destination_port ?? '*'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Protocol</span>
                    <span className="font-mono text-slate-900 font-semibold uppercase">{selectedEvent.protocol || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Action / Outcome</span>
                    <span className="font-semibold text-slate-900">{selectedEvent.action || 'N/A'} / {selectedEvent.outcome || 'N/A'}</span>
                  </div>
                </div>

                {/* Custom Fields Extensibility Display */}
                {selectedEvent.custom_fields && Object.keys(selectedEvent.custom_fields).length > 0 && (
                  <div className="mt-3">
                    <span className="text-slate-700 font-semibold block mb-1">Preserved Custom Vendor Attributes</span>
                    <pre className="bg-slate-50 p-3 rounded-lg border border-slate-200 font-mono text-xs text-slate-800 overflow-x-auto">
                      {JSON.stringify(selectedEvent.custom_fields, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 shadow-xs"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
