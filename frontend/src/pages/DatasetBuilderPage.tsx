import { useState } from 'react';
import { api } from '../api/client';
import { CoveragePanel } from '../components/CoveragePanel';
import { ErrorSummary } from '../components/ErrorSummary';
import type { DatasetPreview, DatasetVersion } from '../types/api';

export function DatasetBuilderPage() {
  const [name, setName] = useState('wakeword_regression');
  const [targetKeyword, setTargetKeyword] = useState('你好小智');
  const [positiveQuota, setPositiveQuota] = useState(10);
  const [similarQuota, setSimilarQuota] = useState(10);
  const [partialQuota, setPartialQuota] = useState(10);
  const [seed, setSeed] = useState(20260617);
  const [specId, setSpecId] = useState('');
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [built, setBuilt] = useState<DatasetVersion | null>(null);
  const [error, setError] = useState<unknown>(null);

  const quotas = {
    wake_positive: positiveQuota,
    similar_negative: similarQuota,
    partial_wake: partialQuota
  };

  async function createSpec() {
    setError(null);
    const response = await api.createDatasetSpec({
      name,
      description: 'Created from platform UI',
      target_keyword: targetKeyword,
      sampling_seed: seed,
      quotas,
      filters: { quality_status: ['ready'] },
      balance_by: ['sample_type', 'gender', 'noise_scene'],
      min_duration_sec: null,
      max_duration_sec: null
    });
    setSpecId(response.id);
    setPreview(null);
    setBuilt(null);
  }

  async function previewSpec() {
    if (!specId) return;
    setPreview(await api.previewDatasetSpec(specId));
  }

  async function buildSpec() {
    if (!specId) return;
    setBuilt(await api.buildDatasetSpec(specId));
  }

  return (
    <section>
      <h1>Dataset Builder</h1>
      <ErrorSummary error={error} />
      <div className="panel">
        <div className="form-grid">
          <label>
            name
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            target keyword
            <input value={targetKeyword} onChange={(event) => setTargetKeyword(event.target.value)} />
          </label>
          <label>
            seed
            <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </label>
          <label>
            wake_positive
            <input type="number" value={positiveQuota} onChange={(event) => setPositiveQuota(Number(event.target.value))} />
          </label>
          <label>
            similar_negative
            <input type="number" value={similarQuota} onChange={(event) => setSimilarQuota(Number(event.target.value))} />
          </label>
          <label>
            partial_wake
            <input type="number" value={partialQuota} onChange={(event) => setPartialQuota(Number(event.target.value))} />
          </label>
        </div>
        <div className="toolbar">
          <button className="primary" onClick={() => createSpec().catch(setError)}>
            创建 spec
          </button>
          <button disabled={!specId} onClick={() => previewSpec().catch(setError)}>
            预览覆盖率
          </button>
          <button disabled={!specId} onClick={() => buildSpec().catch(setError)}>
            构建 version
          </button>
        </div>
        {specId ? <p className="muted">当前 spec: {specId}</p> : null}
      </div>
      {preview ? <CoveragePanel coverage={preview.coverage_summary} /> : null}
      {built ? <div className="warning-box">已构建：{built.name}，item_count={built.item_count}</div> : null}
    </section>
  );
}
