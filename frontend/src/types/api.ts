export type ValidationPayload = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

export type Taxonomy = Record<string, string[]>;

export type Asset = {
  id: string;
  source_id: string;
  stored_path: string;
  text: string;
  normalized_text: string;
  sample_type: string;
  quality_status: string;
  voice_source: string;
  speaker_id: string | null;
  gender: string;
  age_group: string;
  volume: string;
  pitch: string;
  speed: string;
  noise_scene: string;
  snr_bucket: string | null;
  impairment_type: string;
  variant_kind: string;
  duration_sec: number;
  sample_rate: number;
  channels: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
  validation: ValidationPayload;
};

export type UploadRow = {
  path: string;
  original_filename: string;
  duration_sec: number;
  sample_rate: number;
  channels: number;
  bit_depth: number;
  sha256: string;
  status: string;
  error: string | null;
};

export type UploadResponse = {
  upload_id: string;
  uploaded: number;
  failed: number;
  files: UploadRow[];
};

export type ImportCommitFile = {
  path: string;
  text: string;
  sample_type: string;
  quality_status: string;
  voice_source: string;
  gender: string;
  age_group: string;
  volume: string;
  pitch: string;
  speed: string;
  noise_scene: string;
  impairment_type: string;
  notes?: string | null;
};

export type ImportBatch = {
  id: string;
  name: string;
  source_directory: string | null;
  file_count: number;
  imported_count: number;
  duplicate_count: number;
  failed_count?: number;
  status: string;
  created_at: string;
  completed_at: string | null;
  files?: Array<{ path: string; status: string; errors: string[] }>;
};

export type DatasetSpec = {
  id: string;
  name: string;
  description: string;
  target_keyword: string;
  target_keyword_normalized: string;
  sampling_seed: number;
  status: string;
  quotas: Record<string, number>;
  filters: Record<string, string[]>;
  balance_by: string[];
  min_duration_sec: number | null;
  max_duration_sec: number | null;
  created_at: string;
  updated_at: string;
  overrides?: ManualOverride[];
};

export type ManualOverride = {
  id: string;
  variant_id: string;
  action: string;
  reason: string;
  created_at: string;
};

export type DatasetPreview = {
  spec_id: string;
  candidate_count: number;
  item_count: number;
  counts_by_sample_type: Record<string, number>;
  shortfalls: Record<string, number>;
  coverage_summary: CoverageSummary;
};

export type CoverageSummary = {
  total: number;
  by_field?: Record<string, Record<string, number>>;
  shortfalls?: Record<string, number>;
};

export type DatasetVersion = {
  id: string;
  dataset_spec_id: string;
  version: number;
  name: string;
  build_status: string;
  sampling_seed: number;
  rules_snapshot: Record<string, unknown>;
  coverage_summary: CoverageSummary;
  item_count: number;
  total_duration_sec: number;
  export_path: string | null;
  created_at: string;
  built_at: string | null;
  exported_at: string | null;
};

export type DatasetItem = {
  id: string;
  dataset_version_id: string;
  variant_id: string;
  sample_type: string;
  text: string;
  normalized_text: string;
  duration_sec: number;
  selection_reason: string;
  selection_rank: number;
  metadata_snapshot: Record<string, unknown>;
};

export type ExportResponse = {
  export_dir: string;
  manifest: string;
  rich_manifest: string;
  dataset_yaml: string;
  coverage_summary: string;
  eval_config_snippet: string;
  negative_hours: number;
};
