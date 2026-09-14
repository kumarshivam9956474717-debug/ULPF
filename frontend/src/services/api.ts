export interface HealthStatus {
  status: string;
  service: string;
  version: string;
}

export interface FormatDetectionResult {
  detected_format: string;
  confidence: number;
  reason: string;
}

export interface IngestResponse {
  success: boolean;
  raw_event_id: string;
  normalized_event_id: string | null;
  detected_format: string;
  parser_id: string | null;
  parser_version: string | null;
  validation_status: string;
  errors: string[];
  warnings: string[];
  normalized_event: Record<string, any> | null;
}

export async function fetchHealthStatus(): Promise<HealthStatus> {
  const response = await fetch('/api/v1/health');
  if (!response.ok) {
    throw new Error(`API health check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function detectFormat(raw_payload: string): Promise<FormatDetectionResult> {
  const response = await fetch('/api/v1/detect-format', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_payload }),
  });
  if (!response.ok) {
    throw new Error(`Format detection failed with status: ${response.status}`);
  }
  return response.json();
}

export async function ingestLog(
  raw_payload: string,
  source_id?: string,
  format_hint?: string
): Promise<IngestResponse> {
  const response = await fetch('/api/v1/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      raw_payload,
      source_id: source_id || undefined,
      format_hint: format_hint === 'auto' ? undefined : format_hint,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Ingestion failed with status: ${response.status}`);
  }
  return response.json();
}

export interface BatchIngestResponse {
  processing_run_id: string;
  total_received: number;
  total_parsed: number;
  total_normalized: number;
  total_failed: number;
  processing_time_ms: number;
  format_statistics: Record<string, number>;
  parser_statistics: Record<string, number>;
}

export async function ingestBatchLogs(
  events: string[],
  source_id?: string
): Promise<BatchIngestResponse> {
  const response = await fetch('/api/v1/ingest/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      events,
      source_id: source_id || undefined,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Batch ingestion failed with status: ${response.status}`);
  }
  return response.json();
}

// --------------------------------------------------------------------------
// Syslog Service Types & APIs
// --------------------------------------------------------------------------

export interface SyslogListenerConfig {
  enabled: boolean;
  running: boolean;
  host: string;
  port: number;
}

export interface SyslogMetricsData {
  messages_received: number;
  messages_processed: number;
  messages_failed: number;
  messages_dropped: number;
  oversized_messages: number;
  malformed_messages: number;
  active_tcp_connections: number;
  queue_depth: number;
  processing_latency_ms_avg: number;
  events_per_second: number;
  uptime_seconds: number;
}

export interface SyslogStatusResponse {
  manager_running: boolean;
  udp: SyslogListenerConfig;
  tcp: SyslogListenerConfig;
  tls: SyslogListenerConfig;
  queue: {
    depth: number;
    maxsize: number;
    workers: number;
  };
  metrics: SyslogMetricsData;
}

export async function fetchSyslogStatus(): Promise<SyslogStatusResponse> {
  const response = await fetch('/api/v1/syslog/status');
  if (!response.ok) {
    throw new Error(`Syslog status check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function startSyslogService(): Promise<{ message: string; status: SyslogStatusResponse }> {
  const response = await fetch('/api/v1/syslog/start', { method: 'POST' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to start Syslog service: ${response.status}`);
  }
  return response.json();
}

export async function stopSyslogService(): Promise<{ message: string; status: SyslogStatusResponse }> {
  const response = await fetch('/api/v1/syslog/stop', { method: 'POST' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to stop Syslog service: ${response.status}`);
  }
  return response.json();
}

export async function resetSyslogMetrics(): Promise<{ message: string; metrics: SyslogMetricsData }> {
  const response = await fetch('/api/v1/syslog/metrics/reset', { method: 'POST' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to reset Syslog metrics: ${response.status}`);
  }
  return response.json();
}

export interface LogSourceItem {
  id: string;
  source_id: string;
  vendor: string;
  product?: string | null;
  device_type: string;
  hostname?: string | null;
  source_format?: string | null;
  description?: string | null;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

export async function fetchLogSources(): Promise<LogSourceItem[]> {
  const response = await fetch('/api/v1/sources');
  if (!response.ok) {
    throw new Error(`Failed to fetch log sources: ${response.status}`);
  }
  return response.json();
}

// --------------------------------------------------------------------------
// Universal Normalized Events Types & APIs
// --------------------------------------------------------------------------

export interface UniversalEventItem {
  event_id: string;
  source_event_id?: string | null;
  schema_version: string;
  timestamp: string | null;
  ingestion_timestamp: string;
  timezone?: string | null;
  vendor?: string | null;
  product?: string | null;
  device_type?: string | null;
  device_id?: string | null;
  hostname?: string | null;
  source_format?: string | null;
  source_ip?: string | null;
  source_port?: number | null;
  destination_ip?: string | null;
  destination_port?: number | null;
  protocol?: string | null;
  username?: string | null;
  user_id?: string | null;
  authentication_method?: string | null;
  event_type?: string | null;
  action?: string | null;
  outcome?: string | null;
  severity?: string | null;
  category?: string | null;
  subcategory?: string | null;
  interface?: string | null;
  direction?: string | null;
  zone?: string | null;
  threat_name?: string | null;
  threat_id?: string | null;
  signature_id?: string | null;
  rule_id?: string | null;
  message?: string | null;
  tags?: string[];
  custom_fields?: Record<string, any>;
  raw_event_id: string;
  parser_id?: string | null;
  parser_version?: string | null;
  normalization_version: string;
  raw_event?: string;
}

export interface RawEventTraceability {
  event_id: string;
  raw_event_id: string;
  source_id: string;
  received_at: string;
  raw_payload: string;
  payload_encoding: string;
  payload_hash_sha256: string;
  source_format?: string | null;
  ingestion_batch_id?: string | null;
  created_at: string;
  integrity: {
    status: string;
    verified: boolean;
    computed_hash: string;
    stored_hash: string;
  };
}

export async function fetchEvents(params?: {
  limit?: number;
  offset?: number;
  vendor?: string;
  severity?: string;
  action?: string;
}): Promise<UniversalEventItem[]> {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());
  if (params?.vendor) query.set('vendor', params.vendor);
  if (params?.severity) query.set('severity', params.severity);
  if (params?.action) query.set('action', params.action);

  const response = await fetch(`/api/v1/events?${query.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch events: ${response.status}`);
  }
  return response.json();
}

export async function fetchEventById(eventId: string): Promise<UniversalEventItem> {
  const response = await fetch(`/api/v1/events/${encodeURIComponent(eventId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch event ${eventId}: ${response.status}`);
  }
  return response.json();
}

export async function fetchRawEventTraceability(eventId: string): Promise<RawEventTraceability> {
  const response = await fetch(`/api/v1/events/${encodeURIComponent(eventId)}/raw`);
  if (!response.ok) {
    throw new Error(`Failed to fetch raw event for ${eventId}: ${response.status}`);
  }
  return response.json();
}

// --------------------------------------------------------------------------
// Analytics & Parquet Export Types & APIs
// --------------------------------------------------------------------------

export interface OverviewMetrics {
  total_events: number;
  total_raw_events: number;
  events_per_minute: number;
  events_per_hour: number;
  validation_failures: number;
  parser_failures: number;
  anomaly_count: number;
}

export interface TimelinePoint {
  timestamp: string;
  count: number;
  errors: number;
}

export interface DistributionItem {
  key: string;
  count: number;
  percentage: number;
}

export interface TopItem {
  item: string;
  count: number;
  percentage: number;
}

export interface ExportMetrics {
  export_id: string;
  records_selected: number;
  records_exported: number;
  bytes_written: number;
  files_created: number;
  partition_count: number;
  duration_seconds: number;
  records_per_second: number;
  status: string;
}

export interface ExportStatus {
  status: string;
  export_directory: string;
  last_export: ExportMetrics | null;
}

export async function fetchAnalyticsOverview(vendor?: string, severity?: string): Promise<OverviewMetrics> {
  const query = new URLSearchParams();
  if (vendor) query.set('vendor', vendor);
  if (severity) query.set('severity', severity);
  const response = await fetch(`/api/v1/analytics/overview?${query.toString()}`);
  if (!response.ok) throw new Error(`Overview fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnalyticsTimeline(interval: string = 'hour'): Promise<TimelinePoint[]> {
  const response = await fetch(`/api/v1/analytics/timeline?interval=${interval}`);
  if (!response.ok) throw new Error(`Timeline fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnalyticsVendors(): Promise<DistributionItem[]> {
  const response = await fetch('/api/v1/analytics/vendors');
  if (!response.ok) throw new Error(`Vendors fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnalyticsSeverity(): Promise<DistributionItem[]> {
  const response = await fetch('/api/v1/analytics/severity');
  if (!response.ok) throw new Error(`Severity fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnalyticsCategories(): Promise<DistributionItem[]> {
  const response = await fetch('/api/v1/analytics/categories');
  if (!response.ok) throw new Error(`Categories fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnalyticsTopIps(limit: number = 10): Promise<TopItem[]> {
  const response = await fetch(`/api/v1/analytics/top-ips?limit=${limit}`);
  if (!response.ok) throw new Error(`Top IPs fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnalyticsTopPorts(limit: number = 10): Promise<TopItem[]> {
  const response = await fetch(`/api/v1/analytics/top-ports?limit=${limit}`);
  if (!response.ok) throw new Error(`Top Ports fetch failed: ${response.status}`);
  return response.json();
}

export async function triggerParquetExport(batch_size: number = 10000): Promise<ExportMetrics> {
  const response = await fetch('/api/v1/analytics/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ batch_size }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Export failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchExportStatus(): Promise<ExportStatus> {
  const response = await fetch('/api/v1/analytics/export/status');
  if (!response.ok) throw new Error(`Export status fetch failed: ${response.status}`);
  return response.json();
}

// --------------------------------------------------------------------------
// Offline Anomaly Detection Types & APIs
// --------------------------------------------------------------------------

export interface TrainingResult {
  model_name: string;
  model_version: string;
  records_trained: number;
  duration_seconds: number;
  status: string;
  parameters: Record<string, any>;
}

export interface ScanResult {
  records_scanned: number;
  anomalies_detected: number;
  normal_detected: number;
  duration_seconds: number;
  status: string;
}

export interface AnomalyScoreItem {
  id: string;
  event_id: string;
  model_name: string;
  model_version: string;
  anomaly_score: number;
  is_anomaly: boolean;
  detected_at: string;
  feature_summary?: Record<string, any> | null;
  explanation?: {
    reasons: string[];
    [key: string]: any;
  } | null;
}

export interface AnomalyStatistics {
  total_scanned: number;
  total_anomalies: number;
  anomaly_rate: number;
  model_name: string;
  model_version: string;
  is_model_trained: boolean;
}

export async function triggerAnomalyTrain(limit: number = 5000): Promise<TrainingResult> {
  const response = await fetch('/api/v1/anomaly/train', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limit }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Training failed: ${response.status}`);
  }
  return response.json();
}

export async function triggerAnomalyScan(limit: number = 5000, persist: boolean = true): Promise<ScanResult> {
  const response = await fetch('/api/v1/anomaly/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limit, persist }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Scan failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchAnomalyResults(is_anomaly_only: boolean = true, limit: number = 50): Promise<AnomalyScoreItem[]> {
  const response = await fetch(`/api/v1/anomaly/results?is_anomaly_only=${is_anomaly_only}&limit=${limit}`);
  if (!response.ok) throw new Error(`Anomaly results fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnomalyByEventId(eventId: string): Promise<AnomalyScoreItem> {
  const response = await fetch(`/api/v1/anomaly/results/${encodeURIComponent(eventId)}`);
  if (!response.ok) throw new Error(`Anomaly evaluation fetch failed: ${response.status}`);
  return response.json();
}

export async function fetchAnomalyStatistics(): Promise<AnomalyStatistics> {
  const response = await fetch('/api/v1/anomaly/statistics');
  if (!response.ok) throw new Error(`Anomaly statistics fetch failed: ${response.status}`);
  return response.json();
}

// --------------------------------------------------------------------------
// Phase 5: No-Code Onboarding & Mapping Profile Types & APIs
// --------------------------------------------------------------------------

export interface FieldCandidate {
  source_field: string;
  sample_value?: string | null;
  inferred_type: string;
  occurrence_rate: number;
}

export interface SuggestedMapping {
  source_field: string;
  target_field: string;
  confidence: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  method: string;
  is_custom: boolean;
  transform?: string | null;
}

export interface LogAnalysisResult {
  detected_format: string;
  format_confidence: number;
  delimiter: string;
  kv_delimiter: string;
  has_syslog_header: boolean;
  sample_count: number;
  fields: FieldCandidate[];
  suggested_mappings: SuggestedMapping[];
  warnings: string[];
}

export interface MappingRule {
  source_field: string;
  target_field: string;
  transform?: string | null;
  is_custom?: boolean;
  confidence?: number;
}

export interface MappingValidationResult {
  is_valid: boolean;
  records_tested: number;
  records_passed: number;
  records_failed: number;
  mapped_fields: string[];
  unmapped_fields: string[];
  custom_fields: string[];
  sample_normalized_preview?: Record<string, any> | null;
  warnings: string[];
  errors: string[];
}

export interface AuditLogItem {
  id: string;
  action: string;
  version: string;
  actor?: string | null;
  summary: string;
  timestamp: string;
}

export interface ProfileResponse {
  id: string;
  name: string;
  vendor: string;
  product: string;
  device_type: string;
  source_format: string;
  parser_type: string;
  configuration: Record<string, any>;
  field_mappings: MappingRule[];
  version: string;
  status: string;
  confidence: number;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  audit_logs?: AuditLogItem[];
}

export interface ProfileCreateRequest {
  name: string;
  vendor: string;
  product: string;
  device_type: string;
  source_format: string;
  configuration: Record<string, any>;
  field_mappings: MappingRule[];
  confidence?: number;
  created_by?: string;
}

export interface ProfileUpdateRequest {
  vendor?: string;
  product?: string;
  device_type?: string;
  source_format?: string;
  configuration?: Record<string, any>;
  field_mappings?: MappingRule[];
  confidence?: number;
  increment_version?: boolean;
  actor?: string;
}

export async function analyzeUnknownLogs(sample_logs: string[]): Promise<LogAnalysisResult> {
  const response = await fetch('/api/v1/onboarding/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sample_logs }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Log analysis failed with status: ${response.status}`);
  }
  return response.json();
}

export async function validateLogMapping(req: {
  sample_logs: string[];
  source_format: string;
  delimiter?: string;
  kv_delimiter?: string;
  mappings: MappingRule[];
}): Promise<MappingValidationResult> {
  const response = await fetch('/api/v1/onboarding/validate-mapping', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Mapping validation failed with status: ${response.status}`);
  }
  return response.json();
}

export async function testProfileOnSamples(req: {
  profile_id?: string;
  configuration?: Record<string, any>;
  field_mappings?: MappingRule[];
  sample_logs: string[];
}): Promise<MappingValidationResult> {
  const response = await fetch('/api/v1/onboarding/test-profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Profile testing failed with status: ${response.status}`);
  }
  return response.json();
}

export async function createMappingProfile(req: ProfileCreateRequest): Promise<ProfileResponse> {
  const response = await fetch('/api/v1/onboarding/profiles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create profile: ${response.status}`);
  }
  return response.json();
}

export async function fetchMappingProfiles(status?: string, vendor?: string): Promise<ProfileResponse[]> {
  const query = new URLSearchParams();
  if (status) query.set('status', status);
  if (vendor) query.set('vendor', vendor);
  const response = await fetch(`/api/v1/onboarding/profiles?${query.toString()}`);
  if (!response.ok) throw new Error(`Failed to fetch profiles: ${response.status}`);
  return response.json();
}

export async function fetchMappingProfileById(id: string): Promise<ProfileResponse> {
  const response = await fetch(`/api/v1/onboarding/profiles/${encodeURIComponent(id)}`);
  if (!response.ok) throw new Error(`Failed to fetch profile: ${response.status}`);
  return response.json();
}

export async function updateMappingProfile(id: string, req: ProfileUpdateRequest): Promise<ProfileResponse> {
  const response = await fetch(`/api/v1/onboarding/profiles/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update profile: ${response.status}`);
  }
  return response.json();
}

export async function activateMappingProfile(id: string): Promise<ProfileResponse> {
  const response = await fetch(`/api/v1/onboarding/profiles/${encodeURIComponent(id)}/activate`, {
    method: 'POST',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to activate profile: ${response.status}`);
  }
  return response.json();
}

export async function disableMappingProfile(id: string): Promise<ProfileResponse> {
  const response = await fetch(`/api/v1/onboarding/profiles/${encodeURIComponent(id)}/disable`, {
    method: 'POST',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to disable profile: ${response.status}`);
  }
  return response.json();
}

export async function fetchProfileVersionHistory(id: string): Promise<AuditLogItem[]> {
  const response = await fetch(`/api/v1/onboarding/profiles/${encodeURIComponent(id)}/versions`);
  if (!response.ok) throw new Error(`Failed to fetch version history: ${response.status}`);
  return response.json();
}

// --------------------------------------------------------------------------
// Phase 6: Security Analytics & Data Quality Intelligence Types & APIs
// --------------------------------------------------------------------------

export interface SecurityOverview {
  total_events: number;
  total_sources: number;
  healthy_sources_count: number;
  degraded_sources_count: number;
  suspicious_sources_count: number;
  inactive_sources_count: number;
  open_findings_count: number;
  critical_findings_count: number;
  high_findings_count: number;
  coverage_gaps_count: number;
  correlation_candidates_count: number;
  anomaly_count: number;
  unknown_format_count: number;
  parser_failure_count: number;
  validation_failure_count: number;
  data_quality_index: number;
}

export interface SourceHealthMetrics {
  source_id: string;
  name: string;
  vendor: string;
  device_type: string;
  status: 'HEALTHY' | 'DEGRADED' | 'SUSPICIOUS' | 'INACTIVE';
  total_events: number;
  events_per_hour: number;
  avg_hourly_volume: number;
  last_event_timestamp?: string | null;
  parsing_success_rate: number;
  validation_failure_rate: number;
  anomaly_rate: number;
  unknown_format_rate: number;
  ingestion_gap_duration_minutes: number;
  status_reason: string;
}

export interface CoverageFindingItem {
  finding_type: string;
  entity: string;
  time_window: string;
  confidence: number;
  reason: string;
  evidence: Record<string, any>;
}

export interface BaselineDeviationItem {
  source_id: string;
  deviation_type: string;
  baseline_value: number;
  current_value: number;
  deviation_percentage: number;
  z_score: number;
  explanation: string;
}

export interface CorrelationGroup {
  correlation_id: string;
  matching_key: string;
  shared_entity_type: string;
  shared_entity_value: string;
  event_count: number;
  distinct_sources_count: number;
  distinct_vendors: string[];
  time_window_seconds: number;
  first_seen: string;
  last_seen: string;
  events_preview: Array<Record<string, any>>;
  explanation: string;
}

export interface FindingResponse {
  id: string;
  finding_type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number;
  priority_score: number;
  priority_category: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  source_id?: string | null;
  event_count: number;
  first_seen: string;
  last_seen: string;
  title: string;
  explanation: string;
  evidence: Record<string, any>;
  recommended_action?: string | null;
  status: 'OPEN' | 'REVIEWED' | 'DISMISSED';
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalyzeRunResponse {
  scan_id: string;
  scan_timestamp: string;
  sources_scanned: number;
  findings_generated: number;
  new_findings_count: number;
  health_summary: Record<string, number>;
}

export async function fetchSecurityOverview(): Promise<SecurityOverview> {
  const response = await fetch('/api/v1/security-analytics/overview');
  if (!response.ok) throw new Error(`Failed to fetch security overview: ${response.status}`);
  return response.json();
}

export async function fetchSecurityTrends(timeframe: string = '24h'): Promise<{ timeframe: string; points: Array<{ timestamp: string; events: number; anomalies: number }> }> {
  const response = await fetch(`/api/v1/security-analytics/trends?timeframe=${timeframe}`);
  if (!response.ok) throw new Error(`Failed to fetch security trends: ${response.status}`);
  return response.json();
}

export async function fetchSourcesHealth(): Promise<SourceHealthMetrics[]> {
  const response = await fetch('/api/v1/security-analytics/sources');
  if (!response.ok) throw new Error(`Failed to fetch sources health: ${response.status}`);
  return response.json();
}

export async function fetchCoverageGaps(): Promise<CoverageFindingItem[]> {
  const response = await fetch('/api/v1/security-analytics/coverage');
  if (!response.ok) throw new Error(`Failed to fetch coverage gaps: ${response.status}`);
  return response.json();
}

export async function fetchSourceBaselines(): Promise<Array<Record<string, any>>> {
  const response = await fetch('/api/v1/security-analytics/baselines');
  if (!response.ok) throw new Error(`Failed to fetch baselines: ${response.status}`);
  return response.json();
}

export async function fetchCorrelationCandidates(window_minutes: number = 15): Promise<CorrelationGroup[]> {
  const response = await fetch(`/api/v1/security-analytics/correlations?window_minutes=${window_minutes}`);
  if (!response.ok) throw new Error(`Failed to fetch correlations: ${response.status}`);
  return response.json();
}

export async function triggerSecurityAnalysisScan(): Promise<AnalyzeRunResponse> {
  const response = await fetch('/api/v1/security-analytics/analyze', {
    method: 'POST',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Analysis scan failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchSecurityFindings(params?: {
  status?: string;
  finding_type?: string;
  severity?: string;
  source_id?: string;
  limit?: number;
  offset?: number;
}): Promise<FindingResponse[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.finding_type) query.set('finding_type', params.finding_type);
  if (params?.severity) query.set('severity', params.severity);
  if (params?.source_id) query.set('source_id', params.source_id);
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());

  const response = await fetch(`/api/v1/security-analytics/findings?${query.toString()}`);
  if (!response.ok) throw new Error(`Failed to fetch findings: ${response.status}`);
  return response.json();
}

export async function fetchFindingById(id: string): Promise<FindingResponse> {
  const response = await fetch(`/api/v1/security-analytics/findings/${encodeURIComponent(id)}`);
  if (!response.ok) throw new Error(`Failed to fetch finding: ${response.status}`);
  return response.json();
}

export async function reviewFinding(id: string, actor: string = 'analyst'): Promise<FindingResponse> {
  const response = await fetch(`/api/v1/security-analytics/findings/${encodeURIComponent(id)}/review?actor=${encodeURIComponent(actor)}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`Failed to review finding: ${response.status}`);
  return response.json();
}

export async function dismissFinding(id: string, actor: string = 'analyst'): Promise<FindingResponse> {
  const response = await fetch(`/api/v1/security-analytics/findings/${encodeURIComponent(id)}/dismiss?actor=${encodeURIComponent(actor)}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`Failed to dismiss finding: ${response.status}`);
  return response.json();
}

export async function exportFindingsReport(format: 'json' | 'csv' = 'json'): Promise<Blob> {
  const response = await fetch(`/api/v1/security-analytics/findings/export?format=${format}`);
  if (!response.ok) throw new Error(`Failed to export report: ${response.status}`);
  return response.blob();
}

export async function fetchFindingsReportData(): Promise<any> {
  const response = await fetch('/api/v1/security-analytics/findings/report');
  if (!response.ok) throw new Error(`Failed to fetch report data: ${response.status}`);
  return response.json();
}

// ----------------------------------------------------------------------
// Phase 7 Supervisory Intelligence API Types & Services
// ----------------------------------------------------------------------

export interface CapabilityScoreDetail {
  capability_name: string;
  score: number;
  confidence: number;
  indicators: string[];
  positive_signals: string[];
  negative_signals: string[];
  supporting_evidence: Record<string, any>;
  explanation: string;
}

export interface SupervisoryRiskIndicator {
  entity_id: string;
  entity_name: string;
  score: number;
  priority: string;
  confidence: number;
  contributing_indicators: string[];
  evidence_count: number;
  affected_capabilities: string[];
  trend: string;
  explanation: string;
  generated_at: string;
}

export interface ExecutionGapFinding {
  id: string;
  entity_id: string;
  indicator: string;
  severity: string;
  evidence: Record<string, any>;
  time_period: string;
  confidence: number;
  explanation: string;
  recommended_manual_review: string;
  status: string;
}

export interface NegativeSpaceIndicator {
  id: string;
  entity_id: string;
  indicator_type: string;
  title: string;
  severity: string;
  confidence: number;
  evidence: Record<string, any>;
  explanation: string;
  recommended_manual_review: string;
}

export interface ReviewSample {
  id: string;
  entity_id: string;
  event_id: string;
  raw_event_id: string;
  priority_label: string;
  priority_score: number;
  reasons: string[];
  capability_tags: string[];
  severity: string;
  anomaly_score: number;
  closure_time_seconds?: number;
  timestamp: string;
}

export interface PeerMetricComparison {
  metric_name: string;
  entity_value: number;
  peer_median: number;
  peer_p25: number;
  peer_p75: number;
  deviation_percent: number;
  assessment_phrase: string;
}

export interface PeerBenchmarking {
  entity_id: string;
  peer_group: string;
  peer_count: number;
  metrics: PeerMetricComparison[];
  summary_explanation: string;
}

export interface TrendAnalysis {
  entity_id: string;
  current_period: string;
  previous_period: string;
  trend_status: string;
  overall_score_change: number;
  capability_changes: Record<string, number>;
  explanation: string;
}

export interface EvidenceChain {
  finding_id: string;
  finding_title: string;
  finding_type: string;
  severity: string;
  confidence: number;
  indicator_summary: Record<string, any>;
  supporting_metrics: Record<string, any>;
  underlying_event_ids: string[];
  raw_event_samples: Array<{
    raw_event_id: string;
    sha256_hash: string;
    computed_sha256: string;
    sha256_verified: boolean;
    payload_excerpt: string;
    ingested_at: string | null;
  }>;
  sha256_verification_passed: boolean;
}

export interface EntityAssessment {
  id: string;
  entity_id: string;
  entity_name: string;
  assessment_period: string;
  overall_score: number;
  detection_score: number;
  investigation_score: number;
  escalation_score: number;
  operational_discipline_score: number;
  monitoring_coverage_score: number;
  data_quality_score: number;
  cyber_resilience_indicator: number;
  confidence: number;
  risk_category: string;
  trend: string;
  generated_at: string;
  capabilities: CapabilityScoreDetail[];
  supervisory_risk_indicator: SupervisoryRiskIndicator;
  top_execution_gaps: ExecutionGapFinding[];
  negative_space_indicators: NegativeSpaceIndicator[];
  priority_samples: ReviewSample[];
  peer_benchmarking: PeerBenchmarking;
  trend_analysis: TrendAnalysis;
}

export interface ReviewAudit {
  id: string;
  indicator_id: string;
  reviewer: string;
  previous_status: string;
  decision: string;
  notes: string;
  timestamp: string;
}

export async function fetchSupervisoryEntities(): Promise<Array<{ entity_id: string; entity_name: string; status: string }>> {
  const response = await fetch('/api/v1/supervisory/entities');
  if (!response.ok) throw new Error(`Failed to fetch entities: ${response.status}`);
  return response.json();
}

export async function fetchEntityAssessment(entityId: string = 'CSE-ALPHA-01'): Promise<EntityAssessment> {
  const response = await fetch(`/api/v1/supervisory/assessment/${encodeURIComponent(entityId)}`);
  if (!response.ok) throw new Error(`Failed to fetch assessment: ${response.status}`);
  return response.json();
}

export async function runSupervisoryAnalysis(entityId: string = 'CSE-ALPHA-01'): Promise<EntityAssessment> {
  const response = await fetch(`/api/v1/supervisory/analyze?entity_id=${encodeURIComponent(entityId)}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`Failed to run analysis: ${response.status}`);
  return response.json();
}

export async function fetchEvidenceChain(findingId: string): Promise<EvidenceChain> {
  const response = await fetch(`/api/v1/supervisory/evidence/${encodeURIComponent(findingId)}`);
  if (!response.ok) throw new Error(`Failed to fetch evidence chain: ${response.status}`);
  return response.json();
}

export async function submitHumanReview(
  findingId: string,
  reviewer: string,
  decision: string,
  notes: string
): Promise<ReviewAudit> {
  const response = await fetch(`/api/v1/supervisory/review/${encodeURIComponent(findingId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviewer, decision, notes }),
  });
  if (!response.ok) throw new Error(`Failed to submit review: ${response.status}`);
  return response.json();
}

export async function exportSupervisoryReport(entityId: string = 'CSE-ALPHA-01', format: 'json' | 'csv' = 'json'): Promise<Blob> {
  const response = await fetch(`/api/v1/supervisory/report?entity_id=${encodeURIComponent(entityId)}&format_type=${format}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`Failed to export report: ${response.status}`);
  return response.blob();
}

export async function fetchSupervisoryReportData(entityId: string = 'CSE-ALPHA-01'): Promise<any> {
  const response = await fetch(`/api/v1/supervisory/report?entity_id=${encodeURIComponent(entityId)}&format_type=json`);
  if (!response.ok) throw new Error(`Failed to fetch report data: ${response.status}`);
  return response.json();
}

// ----------------------------------------------------------------------
// Phase 8 SIH Demonstration Mode API Services
// ----------------------------------------------------------------------

export async function resetDemo(): Promise<any> {
  const response = await fetch('/api/v1/demo/reset', { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to reset demo: ${response.status}`);
  return response.json();
}

export async function loadDemoData(): Promise<any> {
  const response = await fetch('/api/v1/demo/load', { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to load demo data: ${response.status}`);
  return response.json();
}

export async function runDemoPipeline(): Promise<any> {
  const response = await fetch('/api/v1/demo/run', { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to run demo pipeline: ${response.status}`);
  return response.json();
}

export async function fetchDemoStatus(): Promise<any> {
  const response = await fetch('/api/v1/demo/status');
  if (!response.ok) throw new Error(`Failed to fetch demo status: ${response.status}`);
  return response.json();
}

export async function fetchDemoDataQuality(): Promise<any> {
  const response = await fetch('/api/v1/demo/data-quality');
  if (!response.ok) throw new Error(`Failed to fetch demo data quality: ${response.status}`);
  return response.json();
}

// ----------------------------------------------------------------------
// Modular Parser Registry API Services
// ----------------------------------------------------------------------

export interface ParserVersionItem {
  version: string;
  checksum: string;
  configuration?: Record<string, any>;
  active: boolean;
  id?: string;
  parser_id?: string;
  created_at?: string;
}

export interface ParserItem {
  id: string;
  parser_id: string;
  name: string;
  vendor: string;
  product?: string;
  device_type?: string;
  supported_formats: string[];
  description?: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  versions: ParserVersionItem[];
}

export interface ParserCreatePayload {
  parser_id: string;
  name: string;
  vendor: string;
  product?: string;
  device_type?: string;
  supported_formats: string[];
  description?: string;
  enabled?: boolean;
  initial_version?: {
    version: string;
    checksum: string;
    active: boolean;
    configuration?: Record<string, any>;
  };
}

export async function fetchParsers(): Promise<ParserItem[]> {
  const response = await fetch('/api/v1/parsers');
  if (!response.ok) {
    throw new Error(`Failed to fetch parsers: ${response.status}`);
  }
  return response.json();
}

export async function registerParser(payload: ParserCreatePayload): Promise<ParserItem> {
  const response = await fetch('/api/v1/parsers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to register parser' }));
    throw new Error(err.detail || `Registration failed with status: ${response.status}`);
  }
  return response.json();
}
