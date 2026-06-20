import type {
  Asset,
  AssetListResponse,
  BulkUpdateResponse,
  CreateTransformJobRequest,
  DatasetItem,
  DatasetPreview,
  DatasetSpec,
  DatasetVersion,
  ExportResponse,
  ImportBatch,
  ImportCommitFile,
  Taxonomy,
  TransformJob,
  UploadResponse
} from '../types/api';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `API request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function requestJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  const contentType = response.headers.get('content-type') ?? '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === 'object' && body !== null && 'detail' in body ? (body as { detail: unknown }).detail : body;
    throw new ApiError(response.status, detail);
  }
  return body as T;
}

export const api = {
  health: () => requestJson<{ status: string }>('/api/health'),
  taxonomy: () => requestJson<Taxonomy>('/api/taxonomy'),
  uploadWavs: (files: File[]) => {
    const form = new FormData();
    for (const file of files) form.append('files', file);
    return requestJson<UploadResponse>('/api/imports/uploads', { method: 'POST', body: form });
  },
  commitImport: (name: string, files: ImportCommitFile[]) =>
    requestJson<ImportBatch>('/api/imports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, partial: true, files })
    }),
  listImports: () => requestJson<{ items: ImportBatch[] }>('/api/imports'),
  listAssets: (params: Record<string, string | number> = {}) => {
    const search = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]));
    const query = search.toString();
    return requestJson<AssetListResponse>(`/api/assets${query ? `?${query}` : ''}`);
  },
  patchAsset: (id: string, patch: Partial<Asset>) =>
    requestJson<{ asset: Asset }>('/api/assets/' + encodeURIComponent(id), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    }),
  bulkUpdateAssets: (assetIds: string[], patch: Record<string, unknown>) =>
    requestJson<BulkUpdateResponse>('/api/assets/bulk-update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asset_ids: assetIds, patch })
    }),
  listTransformJobs: () => requestJson<{ items: TransformJob[] }>('/api/transform-jobs'),
  createTransformJob: (payload: CreateTransformJobRequest) =>
    requestJson<TransformJob>('/api/transform-jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
  getTransformJob: (id: string) => requestJson<TransformJob>(`/api/transform-jobs/${encodeURIComponent(id)}`),
  listDatasetSpecs: () => requestJson<{ items: DatasetSpec[] }>('/api/dataset-specs'),
  createDatasetSpec: (payload: {
    name: string;
    description: string;
    target_keyword: string;
    sampling_seed: number;
    quotas: Record<string, number>;
    filters: Record<string, string[]>;
    balance_by: string[];
    min_duration_sec?: number | null;
    max_duration_sec?: number | null;
  }) =>
    requestJson<{ id: string; name: string; quotas: Record<string, number> }>('/api/dataset-specs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
  previewDatasetSpec: (id: string) => requestJson<DatasetPreview>(`/api/dataset-specs/${encodeURIComponent(id)}/preview`, { method: 'POST' }),
  buildDatasetSpec: (id: string) => requestJson<DatasetVersion>(`/api/dataset-specs/${encodeURIComponent(id)}/build`, { method: 'POST' }),
  listDatasetVersions: () => requestJson<{ items: DatasetVersion[] }>('/api/dataset-versions'),
  getDatasetVersionItems: (id: string) => requestJson<{ items: DatasetItem[] }>(`/api/dataset-versions/${encodeURIComponent(id)}/items`),
  exportDatasetVersion: (id: string) => requestJson<ExportResponse>(`/api/dataset-versions/${encodeURIComponent(id)}/export`, { method: 'POST' })
};
