import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { AudioPlayer } from '../components/AudioPlayer';
import { BulkEditToolbar } from '../components/BulkEditToolbar';
import { ErrorSummary } from '../components/ErrorSummary';
import { StatusBadge } from '../components/StatusBadge';
import type { Asset, Taxonomy } from '../types/api';

export function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [taxonomy, setTaxonomy] = useState<Taxonomy>({});
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<unknown>(null);

  async function loadAssets(nextFilter = filter) {
    const params: Record<string, string> = nextFilter ? { sample_type: nextFilter } : {};
    const response = await api.listAssets(params);
    setAssets(response.items);
  }

  useEffect(() => {
    api.taxonomy().then(setTaxonomy).catch(setError);
    loadAssets('').catch(setError);
  }, []);

  function updateLocal(id: string, patch: Partial<Asset>) {
    setAssets((current) => current.map((asset) => (asset.id === id ? { ...asset, ...patch } : asset)));
  }

  async function save(asset: Asset) {
    const response = await api.patchAsset(asset.id, asset);
    setAssets((current) => current.map((item) => (item.id === asset.id ? response.asset : item)));
  }

  async function bulkApply(patch: Record<string, string>) {
    await api.bulkUpdateAssets(Array.from(selected), patch);
    setSelected(new Set());
    await loadAssets();
  }

  const sampleTypes = taxonomy.sample_type ?? ['wake_positive', 'similar_negative', 'partial_wake', 'ordinary_negative'];
  const qualityStatuses = taxonomy.quality_status ?? ['draft', 'ready', 'deprecated'];

  return (
    <section>
      <h1>Assets</h1>
      <ErrorSummary error={error} />
      <div className="toolbar">
        <select
          value={filter}
          onChange={(event) => {
            setFilter(event.target.value);
            loadAssets(event.target.value).catch(setError);
          }}
        >
          <option value="">all sample types</option>
          {sampleTypes.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <button onClick={() => loadAssets().catch(setError)}>刷新</button>
      </div>
      <BulkEditToolbar selectedCount={selected.size} onApply={(patch) => bulkApply(patch).catch(setError)} />
      <table>
        <thead>
          <tr>
            <th></th>
            <th>audio</th>
            <th>text</th>
            <th>type</th>
            <th>quality</th>
            <th>voice/noise</th>
            <th>validation</th>
            <th>action</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => (
            <tr key={asset.id}>
              <td>
                <input
                  type="checkbox"
                  checked={selected.has(asset.id)}
                  onChange={(event) =>
                    setSelected((current) => {
                      const next = new Set(current);
                      event.target.checked ? next.add(asset.id) : next.delete(asset.id);
                      return next;
                    })
                  }
                />
              </td>
              <td>
                <AudioPlayer assetId={asset.id} />
                <div className="muted">{asset.duration_sec.toFixed(2)}s</div>
              </td>
              <td>
                <input value={asset.text} onChange={(event) => updateLocal(asset.id, { text: event.target.value })} />
              </td>
              <td>
                <select value={asset.sample_type} onChange={(event) => updateLocal(asset.id, { sample_type: event.target.value })}>
                  {sampleTypes.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </td>
              <td>
                <select value={asset.quality_status} onChange={(event) => updateLocal(asset.id, { quality_status: event.target.value })}>
                  {qualityStatuses.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </td>
              <td>
                {asset.voice_source}
                <br />
                {asset.noise_scene}
              </td>
              <td>
                <StatusBadge status={asset.validation.ok ? asset.quality_status : 'invalid'} />
                {asset.validation.errors.map((line) => (
                  <div className="muted" key={line}>
                    {line}
                  </div>
                ))}
              </td>
              <td>
                <button onClick={() => save(asset).catch(setError)}>保存</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
