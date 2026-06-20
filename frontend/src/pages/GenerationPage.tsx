import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import { StatusBadge } from '../components/StatusBadge';
import type { Asset, TransformJob, TransformKind } from '../types/api';

async function loadAllAssets(): Promise<Asset[]> {
  const limit = 500;
  let offset = 0;
  const assets: Asset[] = [];
  while (true) {
    const response = await api.listAssets({ limit, offset });
    assets.push(...response.items);
    offset += response.count;
    if (assets.length >= response.total || response.count === 0) return assets;
  }
}

function paramsFor(kind: TransformKind, gainDb: number, speedFactor: number, snrDb: number, seed: number): Record<string, string | number> {
  if (kind === 'volume_gain') return { gain_db: gainDb };
  if (kind === 'speed_change') return { speed_factor: speedFactor };
  return { snr_db: snrDb, seed, noise_scene: 'other', snr_bucket: 'unknown' };
}

export function GenerationPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [jobs, setJobs] = useState<TransformJob[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [kind, setKind] = useState<TransformKind>('volume_gain');
  const [gainDb, setGainDb] = useState(6);
  const [speedFactor, setSpeedFactor] = useState(1.1);
  const [snrDb, setSnrDb] = useState(20);
  const [seed, setSeed] = useState(20260620);
  const [lastJob, setLastJob] = useState<TransformJob | null>(null);
  const [error, setError] = useState<unknown>(null);

  async function load() {
    const [assetItems, jobResponse] = await Promise.all([loadAllAssets(), api.listTransformJobs()]);
    setAssets(assetItems);
    setJobs(jobResponse.items);
  }

  useEffect(() => {
    load().catch(setError);
  }, []);

  async function createJob() {
    if (selected.size === 0) {
      setError(new Error('请选择至少一个 asset'));
      return;
    }
    setError(null);
    const job = await api.createTransformJob({
      variant_ids: Array.from(selected),
      transform_kind: kind,
      params: paramsFor(kind, gainDb, speedFactor, snrDb, seed)
    });
    setLastJob(job);
    setSelected(new Set());
    await load();
  }

  return (
    <section>
      <h1>Generation</h1>
      <ErrorSummary error={error} />
      <div className="panel">
        <div className="form-grid">
          <label>
            transform
            <select value={kind} onChange={(event) => setKind(event.target.value as TransformKind)}>
              <option value="volume_gain">volume_gain</option>
              <option value="speed_change">speed_change</option>
              <option value="noise_mix">noise_mix</option>
            </select>
          </label>
          {kind === 'volume_gain' ? (
            <label>
              gain_db
              <input type="number" step="0.5" value={gainDb} onChange={(event) => setGainDb(Number(event.target.value))} />
            </label>
          ) : null}
          {kind === 'speed_change' ? (
            <label>
              speed_factor
              <input type="number" step="0.05" min="0.5" max="2" value={speedFactor} onChange={(event) => setSpeedFactor(Number(event.target.value))} />
            </label>
          ) : null}
          {kind === 'noise_mix' ? (
            <>
              <label>
                snr_db
                <input type="number" step="1" value={snrDb} onChange={(event) => setSnrDb(Number(event.target.value))} />
              </label>
              <label>
                seed
                <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
              </label>
            </>
          ) : null}
        </div>
        <div className="toolbar">
          <button className="primary" disabled={selected.size === 0} onClick={() => createJob().catch(setError)}>
            生成 {selected.size} 条
          </button>
          <button onClick={() => load().catch(setError)}>刷新</button>
        </div>
      </div>

      {lastJob ? (
        <div className="panel">
          <h2>Latest Job</h2>
          <p>
            {lastJob.id} · {lastJob.status} · created={lastJob.created_count} · failed={lastJob.failed_count}
          </p>
          <div className="tag-list">
            {lastJob.created_variant_ids.map((id) => (
              <span className="tag" key={id}>{id}</span>
            ))}
          </div>
          {lastJob.results.filter((result) => result.errors.length > 0).map((result) => (
            <div className="warning-box" key={result.input_variant_id}>
              {result.input_variant_id}: {result.errors.join('; ')}
            </div>
          ))}
        </div>
      ) : null}

      <div className="panel">
        <h2>Assets</h2>
        <table>
          <thead>
            <tr>
              <th></th>
              <th>id</th>
              <th>type</th>
              <th>variant</th>
              <th>quality</th>
              <th>text</th>
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
                <td>{asset.id}</td>
                <td>{asset.sample_type}</td>
                <td>{asset.variant_kind}</td>
                <td><StatusBadge status={asset.quality_status} /></td>
                <td>{asset.text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2>Jobs</h2>
        <table>
          <thead>
            <tr>
              <th>id</th>
              <th>kind</th>
              <th>status</th>
              <th>requested</th>
              <th>created</th>
              <th>failed</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.id}</td>
                <td>{job.transform_kind}</td>
                <td><StatusBadge status={job.status} /></td>
                <td>{job.requested_count}</td>
                <td>{job.created_count}</td>
                <td>{job.failed_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
