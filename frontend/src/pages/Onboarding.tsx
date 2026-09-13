import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Play,
  Check,
  Edit2,
  Sliders,
  Shield,
  Save,
} from 'lucide-react';
import {
  analyzeUnknownLogs,
  validateLogMapping,
  testProfileOnSamples,
  createMappingProfile,
  activateMappingProfile,
  LogAnalysisResult,
  MappingRule,
  MappingValidationResult
} from '../services/api';

const PRESET_VENDOR_A = [
  'src=10.0.1.15 dst=198.51.100.25 dpt=443 act=allow proto=tcp msg="Perimeter traffic permitted" flow_id=1001',
  'src=10.0.1.28 dst=198.51.100.30 dpt=80 act=deny proto=tcp msg="Unauthorized web attempt" flow_id=1002',
  'src=10.0.2.55 dst=203.0.113.10 dpt=22 act=deny proto=tcp msg="SSH brute force blocked" flow_id=1003'
];

const PRESET_VENDOR_B = [
  'sourceAddress=10.0.0.3 destinationAddress=192.168.1.5 destinationPort=22 action=deny severity=high protocol=tcp traceId=TRC-000101',
  'sourceAddress=10.0.0.12 destinationAddress=192.168.1.50 destinationPort=443 action=allow severity=low protocol=tcp traceId=TRC-000102',
  'sourceAddress=10.0.1.88 destinationAddress=198.51.100.1 destinationPort=53 action=allow severity=informational protocol=udp traceId=TRC-000103'
];

const PRESET_VENDOR_C = [
  '2026-09-10T12:00:00Z|edge-gw-01|10.0.5.10|198.51.100.40|443|allow|tcp|low',
  '2026-09-10T12:01:15Z|edge-gw-02|10.0.5.25|198.51.100.55|22|deny|tcp|high',
  '2026-09-10T12:02:30Z|edge-gw-01|10.0.6.14|203.0.113.88|80|deny|tcp|medium'
];

export const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Step 1: Input
  const [rawText, setRawText] = useState<string>(PRESET_VENDOR_A.join('\n'));
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Step 2: Analysis Results
  const [analysisResult, setAnalysisResult] = useState<LogAnalysisResult | null>(null);

  // Step 3: Reviewed Mappings
  const [rules, setRules] = useState<MappingRule[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [customTargetField, setCustomTargetField] = useState<string>('');

  // Step 4: Validation
  const [validating, setValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<MappingValidationResult | null>(null);

  // Step 5: Test Profile
  const [testing, setTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<MappingValidationResult | null>(null);

  // Step 6: Metadata & Save
  const [profileName, setProfileName] = useState<string>('VendorA Perimeter Firewall');
  const [vendor, setVendor] = useState<string>('VendorA');
  const [product, setProduct] = useState<string>('EdgeFW');
  const [deviceType, setDeviceType] = useState<string>('firewall');
  const [saving, setSaving] = useState<boolean>(false);
  const [savedProfileId, setSavedProfileId] = useState<string | null>(null);

  // Step 7: Activation
  const [activating, setActivating] = useState<boolean>(false);
  const [isActivated, setIsActivated] = useState<boolean>(false);

  const getSampleArray = (): string[] => {
    return rawText
      .split('\n')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  };

  const handleRunAnalysis = async () => {
    const samples = getSampleArray();
    if (samples.length === 0) {
      setAnalysisError('Please enter at least one raw log sample.');
      return;
    }
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await analyzeUnknownLogs(samples);
      setAnalysisResult(res);

      // Initialize rules from suggestions
      const initialRules: MappingRule[] = res.suggested_mappings.map((sm) => ({
        source_field: sm.source_field,
        target_field: sm.target_field,
        is_custom: sm.is_custom,
        confidence: sm.confidence,
        transform: sm.transform || 'none'
      }));
      setRules(initialRules);
      setCurrentStep(2);
    } catch (err: any) {
      setAnalysisError(err.message || 'Analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleValidateMappings = async () => {
    if (!analysisResult) return;
    setValidating(true);
    try {
      const res = await validateLogMapping({
        sample_logs: getSampleArray(),
        source_format: analysisResult.detected_format,
        delimiter: analysisResult.delimiter,
        kv_delimiter: analysisResult.kv_delimiter,
        mappings: rules
      });
      setValidationResult(res);
      setCurrentStep(4);
    } catch (err: any) {
      alert(`Validation failed: ${err.message}`);
    } finally {
      setValidating(false);
    }
  };

  const handleRunTest = async () => {
    if (!analysisResult) return;
    setTesting(true);
    try {
      const res = await testProfileOnSamples({
        configuration: {
          delimiter: analysisResult.delimiter,
          kv_delimiter: analysisResult.kv_delimiter,
          source_format: analysisResult.detected_format
        },
        field_mappings: rules,
        sample_logs: getSampleArray()
      });
      setTestResult(res);
      if (res.is_valid) {
        setCurrentStep(5);
      } else {
        alert('Validation errors encountered during sample test. Please adjust mappings.');
      }
    } catch (err: any) {
      alert(`Testing error: ${err.message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleSaveProfile = async () => {
    if (!analysisResult) return;
    setSaving(true);
    try {
      const res = await createMappingProfile({
        name: profileName,
        vendor: vendor,
        product: product,
        device_type: deviceType,
        source_format: analysisResult.detected_format,
        configuration: {
          delimiter: analysisResult.delimiter,
          kv_delimiter: analysisResult.kv_delimiter,
          source_format: analysisResult.detected_format
        },
        field_mappings: rules,
        confidence: analysisResult.format_confidence
      });
      setSavedProfileId(res.id);
      setCurrentStep(7);
    } catch (err: any) {
      alert(`Failed to save profile: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async () => {
    if (!savedProfileId) return;
    setActivating(true);
    try {
      await activateMappingProfile(savedProfileId);
      setIsActivated(true);
    } catch (err: any) {
      alert(`Activation failed: ${err.message}`);
    } finally {
      setActivating(false);
    }
  };

  const toggleRuleCustom = (index: number) => {
    const updated = [...rules];
    const curr = updated[index];
    if (curr.is_custom) {
      curr.is_custom = false;
      curr.target_field = curr.source_field;
    } else {
      curr.is_custom = true;
      curr.target_field = `custom_${curr.source_field.toLowerCase()}`;
    }
    setRules(updated);
  };

  const saveEditedTarget = (index: number) => {
    if (!customTargetField.trim()) return;
    const updated = [...rules];
    updated[index].target_field = customTargetField.trim();
    updated[index].is_custom = customTargetField.startsWith('custom_');
    setRules(updated);
    setEditingIndex(null);
    setCustomTargetField('');
  };

  const getConfidenceBadge = (level?: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-rose-50 text-rose-700 border-rose-200';
    }
  };

  const steps = [
    { num: 1, title: 'Upload Samples' },
    { num: 2, title: 'Analyze Structure' },
    { num: 3, title: 'Review Mapping' },
    { num: 4, title: 'Validate Preview' },
    { num: 5, title: 'Test Profile' },
    { num: 6, title: 'Save Profile' },
    { num: 7, title: 'Activate' }
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-sky-50 text-sky-600 rounded-lg border border-sky-100">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">No-Code Unknown Log Onboarding</h2>
            <p className="text-sm text-slate-500">
              Deterministic offline field-mapping engine and reusable configuration-driven parser generator.
            </p>
          </div>
        </div>

        <button
          onClick={() => navigate('/profiles')}
          className="inline-flex items-center px-3.5 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 shadow-xs"
        >
          <Sliders className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
          Manage Saved Profiles
        </button>
      </div>

      {/* Wizard Step Progress Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between overflow-x-auto pb-2 sm:pb-0 gap-2">
          {steps.map((s) => {
            const isDone = currentStep > s.num;
            const isCurrent = currentStep === s.num;
            return (
              <div
                key={s.num}
                onClick={() => {
                  if (s.num < currentStep) setCurrentStep(s.num);
                }}
                className={`flex items-center space-x-2 text-xs font-medium cursor-pointer whitespace-nowrap px-2 py-1 rounded transition-colors ${
                  isCurrent
                    ? 'text-sky-700 font-bold bg-sky-50 border border-sky-200'
                    : isDone
                    ? 'text-emerald-700 hover:text-emerald-800'
                    : 'text-slate-400 cursor-not-allowed'
                }`}
              >
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
                    isCurrent
                      ? 'bg-sky-600 text-white'
                      : isDone
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {isDone ? <Check className="w-3 h-3" /> : s.num}
                </span>
                <span>{s.title}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* STEP 1: Upload / Paste Sample Logs */}
      {currentStep === 1 && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Step 1 — Paste or Select Sample Unknown Logs</h3>
            <p className="text-xs text-slate-500">
              Provide one or more log lines from the new vendor device. Multiple samples increase detection confidence.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">Quick Synthetic Presets:</span>
            <button
              onClick={() => {
                setRawText(PRESET_VENDOR_A.join('\n'));
                setProfileName('VendorA Perimeter Firewall');
                setVendor('VendorA');
                setProduct('EdgeFW');
              }}
              className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200"
            >
              Vendor A (Key-Value)
            </button>
            <button
              onClick={() => {
                setRawText(PRESET_VENDOR_B.join('\n'));
                setProfileName('VendorB Edge Security');
                setVendor('VendorB');
                setProduct('EdgeSecure');
              }}
              className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200"
            >
              Vendor B (camelCase KV)
            </button>
            <button
              onClick={() => {
                setRawText(PRESET_VENDOR_C.join('\n'));
                setProfileName('VendorC Perimeter Gateway');
                setVendor('VendorC');
                setProduct('GatewayPro');
              }}
              className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200"
            >
              Vendor C (Pipe-Delimited)
            </button>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Raw Log Samples ({getSampleArray().length} records detected)</span>
              <span className="text-[11px] text-slate-400">One log record per line</span>
            </div>
            <textarea
              rows={6}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste raw log lines here..."
              className="w-full font-mono text-xs p-3 border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500 leading-relaxed"
            />
          </div>

          {analysisError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-500" />
              <span>{analysisError}</span>
            </div>
          )}

          <div className="flex justify-end">
            <button
              onClick={handleRunAnalysis}
              disabled={analyzing || getSampleArray().length === 0}
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors"
            >
              <Sparkles className={`w-3.5 h-3.5 mr-1.5 ${analyzing ? 'animate-spin' : ''}`} />
              {analyzing ? 'Analyzing Structure...' : 'Analyze Structure & Detect Schema'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Structure Analysis Summary */}
      {currentStep === 2 && analysisResult && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-base">Step 2 — Structural Pattern Discovered</h3>
              <p className="text-xs text-slate-500">
                Log structure, delimiters, and candidate fields extracted from {analysisResult.sample_count} sample(s).
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-slate-600">Detection Confidence:</span>
              <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {(analysisResult.format_confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Detected Format</span>
              <span className="font-bold text-slate-800 uppercase text-xs">{analysisResult.detected_format}</span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Token Delimiter</span>
              <span className="font-mono font-bold text-slate-800 text-xs">
                {analysisResult.delimiter === ' ' ? 'Space [ ]' : `"${analysisResult.delimiter}"`}
              </span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">KV Delimiter</span>
              <span className="font-mono font-bold text-slate-800 text-xs">
                {analysisResult.kv_delimiter ? `"${analysisResult.kv_delimiter}"` : 'N/A'}
              </span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Fields Identified</span>
              <span className="font-bold text-sky-700 text-xs">{analysisResult.fields.length} candidate fields</span>
            </div>
          </div>

          {/* Candidate Fields Table */}
          <div>
            <h4 className="font-semibold text-slate-800 text-xs uppercase tracking-wider mb-2">
              Discovered Candidate Tokens & Inferred Data Types
            </h4>
            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-medium">
                  <tr>
                    <th className="py-2 px-3">Candidate Key</th>
                    <th className="py-2 px-3">Sample Value</th>
                    <th className="py-2 px-3">Inferred Semantic Type</th>
                    <th className="py-2 px-3">Sample Frequency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {analysisResult.fields.map((f, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50">
                      <td className="py-2 px-3 font-mono font-semibold text-slate-900">{f.source_field}</td>
                      <td className="py-2 px-3 font-mono text-slate-600 truncate max-w-xs">{f.sample_value || 'None'}</td>
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                          {f.inferred_type}
                        </span>
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-500">{(f.occurrence_rate * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex justify-between pt-2">
            <button
              onClick={() => setCurrentStep(1)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back to Samples
            </button>
            <button
              onClick={() => setCurrentStep(3)}
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-xs"
            >
              <span>Review Mapping Suggestions</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Human Review of Mappings */}
      {currentStep === 3 && analysisResult && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-base">Step 3 — Review & Refine Field Mappings</h3>
              <p className="text-xs text-slate-500">
                Confirm canonical Universal Event Schema (UES) targets, mark custom attributes, or adjust low-confidence mappings.
              </p>
            </div>
            <span className="text-xs text-slate-500">
              Total Mappings: <span className="font-bold text-slate-800">{rules.length}</span>
            </span>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-medium">
                <tr>
                  <th className="py-2.5 px-3">Source Field</th>
                  <th className="py-2.5 px-3">Sample Value</th>
                  <th className="py-2.5 px-3">Inferred Type</th>
                  <th className="py-2.5 px-3">Target UES Field</th>
                  <th className="py-2.5 px-3">Confidence</th>
                  <th className="py-2.5 px-3">Method</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {rules.map((rule, idx) => {
                  const suggestion = analysisResult.suggested_mappings[idx];
                  const fieldCand = analysisResult.fields[idx];
                  const isEditing = editingIndex === idx;

                  return (
                    <tr key={idx} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">{rule.source_field}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-600 truncate max-w-[140px]">
                        {fieldCand?.sample_value || 'N/A'}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                          {fieldCand?.inferred_type || 'string'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {isEditing ? (
                          <div className="flex items-center space-x-1">
                            <input
                              type="text"
                              value={customTargetField}
                              onChange={(e) => setCustomTargetField(e.target.value)}
                              placeholder="e.g. source_ip"
                              className="border border-sky-500 rounded px-1.5 py-0.5 text-xs font-mono w-32 bg-white"
                              autoFocus
                            />
                            <button
                              onClick={() => saveEditedTarget(idx)}
                              className="px-1.5 py-0.5 bg-sky-600 text-white rounded text-[10px] font-semibold"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingIndex(null)}
                              className="px-1 py-0.5 text-slate-500 text-[10px]"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <span
                            className={`font-semibold ${
                              rule.is_custom ? 'text-indigo-600' : 'text-emerald-700'
                            }`}
                          >
                            {rule.target_field}
                            {rule.is_custom && <span className="text-[10px] ml-1 text-indigo-400">(custom)</span>}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getConfidenceBadge(suggestion?.confidence_level)}`}>
                          {suggestion?.confidence_level || 'MEDIUM'} ({((rule.confidence || 0.8) * 100).toFixed(0)}%)
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[11px] text-slate-500">
                        {suggestion?.method || 'user_configured'}
                      </td>
                      <td className="py-2.5 px-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            onClick={() => {
                              setEditingIndex(idx);
                              setCustomTargetField(rule.target_field);
                            }}
                            className="p-1 hover:bg-slate-100 text-slate-500 rounded"
                            title="Edit Target Field"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => toggleRuleCustom(idx)}
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              rule.is_custom
                                ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                            }`}
                          >
                            {rule.is_custom ? 'Custom' : 'Make Custom'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between pt-2">
            <button
              onClick={() => setCurrentStep(2)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back to Structure
            </button>
            <button
              onClick={handleValidateMappings}
              disabled={validating}
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
            >
              <CheckCircle2 className={`w-3.5 h-3.5 mr-1.5 ${validating ? 'animate-spin' : ''}`} />
              {validating ? 'Validating Normalization...' : 'Validate Mapping & Preview UES'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Validation & UES Preview */}
      {currentStep === 4 && validationResult && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-base">Step 4 — Normalization Simulation Preview</h3>
              <p className="text-xs text-slate-500">
                Simulated execution against sample records. Verifies schema conformance and lossless custom field retention.
              </p>
            </div>
            <span
              className={`px-3 py-1 rounded text-xs font-bold border ${
                validationResult.is_valid
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}
            >
              {validationResult.is_valid ? 'Validation Passed' : 'Validation Issues Detected'}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Mapped UES Fields</span>
              <span className="font-bold text-emerald-700 text-sm">{validationResult.mapped_fields.length}</span>
              <div className="text-[10px] text-slate-400 mt-0.5 truncate">{validationResult.mapped_fields.join(', ')}</div>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Custom Attributes</span>
              <span className="font-bold text-indigo-700 text-sm">{validationResult.custom_fields.length}</span>
              <div className="text-[10px] text-slate-400 mt-0.5 truncate">{validationResult.custom_fields.join(', ') || 'None'}</div>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Unmapped Retained</span>
              <span className="font-bold text-sky-700 text-sm">{validationResult.unmapped_fields.length}</span>
              <div className="text-[10px] text-slate-400 mt-0.5 truncate">{validationResult.unmapped_fields.join(', ') || 'None'}</div>
            </div>
          </div>

          {/* Sample Normalized UES Preview */}
          {validationResult.sample_normalized_preview && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-700 font-semibold">
                <span>Simulated Universal Event (UES) Output:</span>
                <span className="text-[11px] text-slate-400 font-mono">schema_version: 1.0.0</span>
              </div>
              <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-72 leading-relaxed">
                {JSON.stringify(validationResult.sample_normalized_preview, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex justify-between pt-2">
            <button
              onClick={() => setCurrentStep(3)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back to Mapping
            </button>
            <button
              onClick={handleRunTest}
              disabled={testing || !validationResult.is_valid}
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 mr-1.5 ${testing ? 'animate-spin' : ''}`} />
              {testing ? 'Running Sample Tests...' : 'Test Profile Against All Samples'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: Test Profile Results */}
      {currentStep === 5 && testResult && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-base">Step 5 — Profile Pre-Activation Test Passed</h3>
              <p className="text-xs text-slate-500">
                All sample records verified through validation engine without fatal errors.
              </p>
            </div>
            <span className="px-3 py-1 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded font-semibold text-xs flex items-center">
              <Check className="w-3.5 h-3.5 mr-1" /> 100% Pass Rate
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-400 block font-medium">Tested Samples</span>
              <span className="text-xl font-bold text-slate-900">{testResult.records_tested}</span>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-400 block font-medium">Passed Records</span>
              <span className="text-xl font-bold text-emerald-600">{testResult.records_passed}</span>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-400 block font-medium">Failed Records</span>
              <span className="text-xl font-bold text-slate-900">{testResult.records_failed}</span>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-400 block font-medium">Warnings</span>
              <span className="text-xl font-bold text-amber-600">{testResult.warnings.length}</span>
            </div>
          </div>

          <div className="flex justify-between pt-2">
            <button
              onClick={() => setCurrentStep(4)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back to Preview
            </button>
            <button
              onClick={() => setCurrentStep(6)}
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-xs"
            >
              <span>Configure Profile Metadata</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 6: Save Profile Metadata */}
      {currentStep === 6 && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-slate-900 text-base">Step 6 — Save Reusable Mapping Profile</h3>
            <p className="text-xs text-slate-500">
              Name this profile and define its device taxonomy. It will be saved as DRAFT before final activation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Profile Name</label>
              <input
                type="text"
                value={profileName}
                onChange={(e) => setProfileName(e.target.value)}
                placeholder="e.g. Acme Edge Firewall"
                className="w-full text-xs p-2.5 border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Vendor Identifier</label>
              <input
                type="text"
                value={vendor}
                onChange={(e) => setVendor(e.target.value)}
                placeholder="e.g. Acme"
                className="w-full text-xs p-2.5 border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Product</label>
              <input
                type="text"
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                placeholder="e.g. GateKeeper"
                className="w-full text-xs p-2.5 border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Device Type</label>
              <select
                value={deviceType}
                onChange={(e) => setDeviceType(e.target.value)}
                className="w-full text-xs p-2.5 border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-sky-500"
              >
                <option value="firewall">Firewall / NGFW</option>
                <option value="router">Edge Router</option>
                <option value="switch">Perimeter Switch</option>
                <option value="waf">Web Application Firewall (WAF)</option>
                <option value="vpn">VPN Gateway</option>
                <option value="idps">Intrusion Detection/Prevention (IDPS)</option>
                <option value="security_device">Generic Security Device</option>
              </select>
            </div>
          </div>

          <div className="flex justify-between pt-2">
            <button
              onClick={() => setCurrentStep(5)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back to Test
            </button>
            <button
              onClick={handleSaveProfile}
              disabled={saving || !profileName.trim()}
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50"
            >
              <Save className={`w-3.5 h-3.5 mr-1.5 ${saving ? 'animate-spin' : ''}`} />
              {saving ? 'Saving Profile...' : 'Save Profile (DRAFT)'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 7: Activation & Confirmation */}
      {currentStep === 7 && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-slate-900 text-base">Step 7 — Activate for Automated Ingestion</h3>
            <p className="text-xs text-slate-500">
              Once activated, this profile registers with the Parser Registry to parse future matching logs automatically.
            </p>
          </div>

          <div className="bg-sky-50/50 border border-sky-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center space-x-2 text-sky-900 font-bold text-sm">
              <Shield className="w-4 h-4 text-sky-600" />
              <span>Zero-Code Production Readiness Guarantee</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Activating <strong>{profileName}</strong> will deploy an instance of <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-sky-200 text-sky-800">ConfigurableParser</code> into
              the pipeline. Subsequent logs matching this structure will automatically parse, normalize into canonical UES attributes, preserve custom fields, and link to raw logs with SHA-256 integrity.
            </p>
          </div>

          {isActivated ? (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-2 text-center py-6">
              <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
              <h4 className="font-bold text-emerald-900 text-base">Profile Successfully Activated!</h4>
              <p className="text-xs text-emerald-700 max-w-md mx-auto">
                Future logs matching this format will now be parsed and normalized into PostgreSQL automatically without Python code changes.
              </p>
              <div className="pt-3">
                <button
                  onClick={() => navigate('/profiles')}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs"
                >
                  Go to Parser Profiles
                </button>
              </div>
            </div>
          ) : (
            <div className="flex justify-between pt-2">
              <button
                onClick={() => navigate('/profiles')}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Keep in DRAFT
              </button>
              <button
                onClick={handleActivate}
                disabled={activating}
                className="inline-flex items-center px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors disabled:opacity-50"
              >
                <CheckCircle2 className={`w-4 h-4 mr-1.5 ${activating ? 'animate-spin' : ''}`} />
                {activating ? 'Activating Parser...' : 'Activate Profile for Production'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
