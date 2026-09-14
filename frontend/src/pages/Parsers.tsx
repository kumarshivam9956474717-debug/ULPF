import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Cpu,
  Plus,
  Search,
  CheckCircle2,
  X,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Shield,
  FileCode,
} from 'lucide-react';
import { fetchParsers, registerParser, ParserItem, ParserCreatePayload } from '../services/api';

const DEFAULT_CATALOG: Array<{
  id: string;
  parser_id: string;
  name: string;
  vendor: string;
  product?: string;
  device_type?: string;
  supported_formats: string[];
  description?: string;
  enabled: boolean;
  isBuiltIn?: boolean;
}> = [
  {
    id: 'builtin-cisco-asa',
    parser_id: 'cisco_asa',
    name: 'Cisco ASA / Firepower',
    vendor: 'Cisco',
    product: 'ASA 5500 / Firepower 2100',
    device_type: 'Perimeter Firewall',
    supported_formats: ['syslog'],
    description: 'Lossless extraction of Cisco %ASA security event codes, teardowns, and connection drops.',
    enabled: true,
    isBuiltIn: true,
  },
  {
    id: 'builtin-paloalto-panos',
    parser_id: 'paloalto_panos',
    name: 'Palo Alto PAN-OS',
    vendor: 'Palo Alto Networks',
    product: 'PA-Series NGFW',
    device_type: 'NGFW & Threat Prevention',
    supported_formats: ['syslog', 'cef'],
    description: 'High-speed parsing for PAN-OS traffic, threat, and system telemetry with application identification.',
    enabled: true,
    isBuiltIn: true,
  },
  {
    id: 'builtin-fortinet-fortigate',
    parser_id: 'fortinet_fortigate',
    name: 'Fortinet FortiGate',
    vendor: 'Fortinet',
    product: 'FortiGate UTM / NGFW',
    device_type: 'NGFW & UTM',
    supported_formats: ['key-value', 'syslog'],
    description: 'Key-value delimiter parser extracting UTM antivirus, IPS, and VPN session boundaries.',
    enabled: true,
    isBuiltIn: true,
  },
  {
    id: 'builtin-checkpoint-gaia',
    parser_id: 'checkpoint_gaia',
    name: 'Check Point Quantum',
    vendor: 'Check Point',
    product: 'Quantum Security Gateway',
    device_type: 'Perimeter Gateway',
    supported_formats: ['syslog', 'json'],
    description: 'Lossless parser for Check Point Gaia log daemon and Quantum perimeter inspect alerts.',
    enabled: true,
    isBuiltIn: true,
  },
  {
    id: 'builtin-suricata-eve',
    parser_id: 'suricata_eve',
    name: 'Suricata / Snort IDS',
    vendor: 'Open Source / OISF',
    product: 'Suricata EVE / Snort 3',
    device_type: 'IDPS / Sensor',
    supported_formats: ['json', 'syslog'],
    description: 'Deep packet inspection log parser extracting signature IDs, payloads, and flow metrics.',
    enabled: true,
    isBuiltIn: true,
  },
];

const AVAILABLE_FORMATS = ['syslog', 'cef', 'json', 'leef', 'key-value', 'regex'];

export const Parsers: React.FC = () => {
  const [parsers, setParsers] = useState<ParserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('ALL');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // Form Fields
  const [formData, setFormData] = useState({
    parser_id: '',
    name: '',
    vendor: '',
    product: '',
    device_type: 'Perimeter Firewall',
    supported_formats: ['syslog'] as string[],
    description: '',
    version: '1.0.0',
    enabled: true,
  });

  const loadParsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchParsers();
      setParsers(data);
    } catch (err: any) {
      console.warn('Could not fetch parsers from backend, using default catalog:', err);
      // Backend may be cold or offline, still render cleanly
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadParsers();
  }, []);

  const handleFormatToggle = (fmt: string) => {
    setFormData((prev) => {
      const exists = prev.supported_formats.includes(fmt);
      return {
        ...prev,
        supported_formats: exists
          ? prev.supported_formats.filter((f) => f !== fmt)
          : [...prev.supported_formats, fmt],
      };
    });
  };

  const handleOpenModal = () => {
    setFormError(null);
    setFormSuccess(null);
    setFormData({
      parser_id: '',
      name: '',
      vendor: '',
      product: '',
      device_type: 'Perimeter Firewall',
      supported_formats: ['syslog'],
      description: '',
      version: '1.0.0',
      enabled: true,
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.parser_id.trim() || !formData.name.trim() || !formData.vendor.trim()) {
      setFormError('Parser ID, Name, and Vendor are required fields.');
      return;
    }

    if (formData.supported_formats.length === 0) {
      setFormError('Please select at least one supported format.');
      return;
    }

    setSubmitting(true);
    setFormError(null);

    const payload: ParserCreatePayload = {
      parser_id: formData.parser_id.trim().toLowerCase().replace(/\s+/g, '_'),
      name: formData.name.trim(),
      vendor: formData.vendor.trim(),
      product: formData.product.trim() || undefined,
      device_type: formData.device_type.trim() || undefined,
      supported_formats: formData.supported_formats,
      description: formData.description.trim() || undefined,
      enabled: formData.enabled,
      initial_version: {
        version: formData.version.trim() || '1.0.0',
        checksum: 'sha256-modular-init',
        active: true,
        configuration: {
          vendor: formData.vendor.trim(),
          device_type: formData.device_type.trim(),
        },
      },
    };

    try {
      const created = await registerParser(payload);
      setFormSuccess(`Parser "${created.name}" successfully registered in ULPF Registry!`);
      await loadParsers();
      setTimeout(() => {
        setIsModalOpen(false);
      }, 1200);
    } catch (err: any) {
      setFormError(err.message || 'Failed to register parser.');
    } finally {
      setSubmitting(false);
    }
  };

  // Combine DB parsers with built-in catalog, de-duplicating by parser_id
  const combinedParsers = [
    ...parsers.map((p) => ({ ...p, isBuiltIn: false })),
    ...DEFAULT_CATALOG.filter((cat) => !parsers.some((p) => p.parser_id === cat.parser_id)),
  ];

  // Filtering
  const filteredParsers = combinedParsers.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.vendor.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.parser_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.product && p.product.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesFormat =
      selectedFormat === 'ALL' ||
      p.supported_formats.some((fmt) => fmt.toLowerCase() === selectedFormat.toLowerCase());

    return matchesSearch && matchesFormat;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-sky-50 text-sky-600 rounded-lg border border-sky-100">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-slate-900">Modular Parser Registry</h2>
              <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                Active Registry
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Decoupled parsing modules for vendor-specific log extraction without touching core engine pipelines.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5 self-start sm:self-auto">
          <button
            onClick={loadParsers}
            disabled={loading}
            className="p-2 text-slate-500 hover:text-slate-800 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition"
            title="Refresh Registry"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-600' : ''}`} />
          </button>

          <Link
            to="/onboarding"
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>No-Code Studio</span>
          </Link>

          <button
            onClick={handleOpenModal}
            className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-bold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm shadow-sky-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>Register New Parser</span>
          </button>
        </div>
      </div>

      {/* Search & Format Filter Bar */}
      {error && (
        <div className="flex items-center space-x-2 p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by vendor, name, or parser ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition"
          />
        </div>

        <div className="flex items-center space-x-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          <span className="text-xs text-slate-400 mr-1 font-medium">Format:</span>
          {['ALL', ...AVAILABLE_FORMATS].map((fmt) => (
            <button
              key={fmt}
              onClick={() => setSelectedFormat(fmt)}
              className={`px-2.5 py-1 text-xs rounded-md font-medium capitalize transition-colors ${
                selectedFormat === fmt
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Parser Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredParsers.map((target) => (
          <div
            key={target.id || target.parser_id}
            className="bg-white p-5 rounded-xl border border-slate-200/90 shadow-sm hover:shadow-md transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <span className="text-[11px] font-bold text-sky-700 bg-sky-50 border border-sky-100 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  {target.vendor}
                </span>

                <span
                  className={`px-2 py-0.5 text-[11px] font-semibold rounded-full border ${
                    target.isBuiltIn
                      ? 'bg-slate-50 text-slate-600 border-slate-200'
                      : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  }`}
                >
                  {target.isBuiltIn ? 'Core Built-In' : 'Custom Registered'}
                </span>
              </div>

              <h3 className="text-sm font-bold text-slate-900 mt-2.5 flex items-center gap-1.5">
                <FileCode className="w-4 h-4 text-slate-400 shrink-0" />
                <span>{target.name}</span>
              </h3>

              <p className="text-xs text-slate-500 mt-1 font-medium">
                {target.product || target.device_type}
              </p>

              <p className="text-xs text-slate-600 mt-2.5 line-clamp-2 leading-relaxed">
                {target.description || 'Modular parser extracting security event payloads into UES schema.'}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-400 font-medium">Formats:</span>
                <div className="flex items-center gap-1">
                  {target.supported_formats.map((fmt) => (
                    <span
                      key={fmt}
                      className="px-1.5 py-0.5 bg-slate-100 text-slate-700 font-mono text-[10px] rounded uppercase"
                    >
                      {fmt}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between text-xs font-mono text-slate-500 pt-1">
                <span className="text-[11px] text-slate-400">ID:</span>
                <span className="text-sky-600 font-semibold truncate max-w-[170px]">
                  {target.parser_id}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredParsers.length === 0 && (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center space-y-3">
          <Cpu className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-base font-bold text-slate-800">No Parsers Found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            No parser matched your current filter criteria. Try changing the format filter or register a new modular parser.
          </p>
          <button
            onClick={handleOpenModal}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Register New Parser</span>
          </button>
        </div>
      )}

      {/* Architecture Guidance Box */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm text-xs text-slate-600 space-y-2">
        <div className="flex items-center space-x-2 text-slate-800 font-bold">
          <Shield className="w-4 h-4 text-sky-600" />
          <span>Decoupled Parser Architecture (NTRO / SIH26156 Standard)</span>
        </div>
        <p className="leading-relaxed">
          Each parser is strictly encapsulated behind the interface implementing{' '}
          <code className="font-mono bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded border border-slate-200">
            parse_raw(payload: str) -&gt; ExtractedEvent
          </code>
          . Adding a new vendor format never alters database schemas, the normalization pipeline, or frontend presentation.
        </p>
      </div>

      {/* Register New Parser Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-sky-100 text-sky-700 rounded-lg">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Register Modular Parser</h3>
                  <p className="text-xs text-slate-500">
                    Add a vendor module to the OmniLogix Parser Registry
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-lg transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {formError && (
                <div className="flex items-center space-x-2 p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {formSuccess && (
                <div className="flex items-center space-x-2 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{formSuccess}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Parser ID (Slug) *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., juniper_srx"
                    value={formData.parser_id}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        parser_id: e.target.value.toLowerCase().replace(/\s+/g, '_'),
                      })
                    }
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                  />
                  <span className="text-[10px] text-slate-400">Unique identifier for pipeline resolution</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Parser Display Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Juniper SRX Security Gateway"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Vendor *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Juniper Networks"
                    value={formData.vendor}
                    onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Product Family
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., SRX Series Services Gateway"
                    value={formData.product}
                    onChange={(e) => setFormData({ ...formData, product: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Device Type
                  </label>
                  <select
                    value={formData.device_type}
                    onChange={(e) => setFormData({ ...formData, device_type: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                  >
                    <option value="Perimeter Firewall">Perimeter Firewall</option>
                    <option value="NGFW & Threat Prevention">NGFW & Threat Prevention</option>
                    <option value="IDPS / Sensor">IDPS / Sensor</option>
                    <option value="VPN Gateway">VPN Gateway</option>
                    <option value="WAF / Reverse Proxy">WAF / Reverse Proxy</option>
                    <option value="Router / L3 Switch">Router / L3 Switch</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Initial Version
                  </label>
                  <input
                    type="text"
                    value={formData.version}
                    onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                  />
                </div>
              </div>

              {/* Supported Formats Selection */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Supported Wire Formats *
                </label>
                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_FORMATS.map((fmt) => {
                    const isSelected = formData.supported_formats.includes(fmt);
                    return (
                      <button
                        type="button"
                        key={fmt}
                        onClick={() => handleFormatToggle(fmt)}
                        className={`px-3 py-1 text-xs rounded-lg font-mono uppercase transition-all flex items-center space-x-1.5 border ${
                          isSelected
                            ? 'bg-sky-600 text-white border-sky-600 shadow-xs'
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        <span>{fmt}</span>
                        {isSelected && <CheckCircle2 className="w-3 h-3" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  placeholder="Summary of log patterns, fields extracted, and security indicators..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                />
              </div>

              {/* Modal Footer Actions */}
              <div className="pt-3 border-t border-slate-200 flex items-center justify-between">
                <Link
                  to="/onboarding"
                  className="text-xs text-sky-600 hover:text-sky-700 font-medium flex items-center gap-1"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Need regex pattern testing? Try No-Code Studio</span>
                </Link>

                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 text-xs font-bold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm flex items-center space-x-1.5 transition disabled:opacity-50"
                  >
                    {submitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>{submitting ? 'Registering...' : 'Register Parser'}</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
