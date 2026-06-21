import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import { StatusBadge } from '../components/StatusBadge';
import type { Asset, TransformJob, TransformKind } from '../types/api';

type BandLimitMode = 'freq' | 'iir' | 'resample';
type AmpDistortionType = 'gain_db' | 'max_distortion' | 'fence_distortion' | 'jag_distortion' | 'poly_distortion' | 'quad_distortion';

type ParamState = {
  gainDb: number;
  speedFactor: number;
  snrDb: number;
  seed: number;
  bandLimitMode: BandLimitMode;
  cutoffHz: number;
  narrowbandRate: number;
  distortionType: AmpDistortionType;
  distortionRate: number;
  distortionGainDb: number;
  distortionMaxDb: number;
  distortionMaskNumber: number;
};

const transformOptions: TransformKind[] = [
  'volume_gain',
  'speed_change',
  'noise_mix',
  'subband_eq',
  'band_limit',
  'narrowband',
  'spectral_mask',
  'amp_distortion',
  'signal_mimic'
];

const seedKinds = new Set<TransformKind>(['noise_mix', 'subband_eq', 'spectral_mask', 'amp_distortion', 'signal_mimic']);

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

function paramsFor(kind: TransformKind, state: ParamState): Record<string, string | number> {
  if (kind === 'volume_gain') return { gain_db: state.gainDb };
  if (kind === 'speed_change') return { speed_factor: state.speedFactor };
  if (kind === 'noise_mix') return { snr_db: state.snrDb, seed: state.seed, noise_scene: 'other', snr_bucket: 'unknown' };
  if (kind === 'subband_eq') return { seed: state.seed };
  if (kind === 'band_limit') {
    const params: Record<string, string | number> = { mode: state.bandLimitMode, cutoff_hz: state.cutoffHz };
    if (state.bandLimitMode === 'resample') params.target_sample_rate = state.narrowbandRate;
    return params;
  }
  if (kind === 'narrowband') return { target_sample_rate: state.narrowbandRate };
  if (kind === 'spectral_mask') return { seed: state.seed };
  if (kind === 'signal_mimic') return { seed: state.seed };

  const params: Record<string, string | number> = {
    distortion_type: state.distortionType,
    rate: state.distortionRate,
    seed: state.seed
  };
  if (state.distortionType === 'gain_db') params.gain_db = state.distortionGainDb;
  if (state.distortionType === 'max_distortion' || state.distortionType === 'fence_distortion') params.max_db = state.distortionMaxDb;
  if (state.distortionType === 'fence_distortion' || state.distortionType === 'jag_distortion') params.mask_number = state.distortionMaskNumber;
  return params;
}

function invalidNumericParam(params: Record<string, string | number>): string | null {
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'number' && !Number.isFinite(value)) return key;
  }
  return null;
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
  const [bandLimitMode, setBandLimitMode] = useState<BandLimitMode>('freq');
  const [cutoffHz, setCutoffHz] = useState(4000);
  const [narrowbandRate, setNarrowbandRate] = useState(8000);
  const [distortionType, setDistortionType] = useState<AmpDistortionType>('max_distortion');
  const [distortionRate, setDistortionRate] = useState(0.8);
  const [distortionGainDb, setDistortionGainDb] = useState(6);
  const [distortionMaxDb, setDistortionMaxDb] = useState(-1);
  const [distortionMaskNumber, setDistortionMaskNumber] = useState(4);
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
    const params = paramsFor(kind, {
      gainDb,
      speedFactor,
      snrDb,
      seed,
      bandLimitMode,
      cutoffHz,
      narrowbandRate,
      distortionType,
      distortionRate,
      distortionGainDb,
      distortionMaxDb,
      distortionMaskNumber
    });
    const invalidParam = invalidNumericParam(params);
    if (invalidParam) {
      setError(new Error(`${invalidParam} 必须是有效数字`));
      return;
    }
    const job = await api.createTransformJob({
      variant_ids: Array.from(selected),
      transform_kind: kind,
      params
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
              {transformOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
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
            <label>
              snr_db
              <input type="number" step="1" value={snrDb} onChange={(event) => setSnrDb(Number(event.target.value))} />
            </label>
          ) : null}
          {kind === 'band_limit' ? (
            <>
              <label>
                mode
                <select value={bandLimitMode} onChange={(event) => setBandLimitMode(event.target.value as BandLimitMode)}>
                  <option value="freq">freq</option>
                  <option value="iir">iir</option>
                  <option value="resample">resample</option>
                </select>
              </label>
              <label>
                cutoff_hz
                <input type="number" step="100" min="20" max="7999" value={cutoffHz} onChange={(event) => setCutoffHz(Number(event.target.value))} />
              </label>
              {bandLimitMode === 'resample' ? (
                <label>
                  target_sample_rate
                  <input type="number" step="1000" min="1000" max="15000" value={narrowbandRate} onChange={(event) => setNarrowbandRate(Number(event.target.value))} />
                </label>
              ) : null}
            </>
          ) : null}
          {kind === 'narrowband' ? (
            <label>
              target_sample_rate
              <input type="number" step="1000" min="1000" max="15000" value={narrowbandRate} onChange={(event) => setNarrowbandRate(Number(event.target.value))} />
            </label>
          ) : null}
          {kind === 'amp_distortion' ? (
            <>
              <label>
                distortion_type
                <select value={distortionType} onChange={(event) => setDistortionType(event.target.value as AmpDistortionType)}>
                  <option value="gain_db">gain_db</option>
                  <option value="max_distortion">max_distortion</option>
                  <option value="fence_distortion">fence_distortion</option>
                  <option value="jag_distortion">jag_distortion</option>
                  <option value="poly_distortion">poly_distortion</option>
                  <option value="quad_distortion">quad_distortion</option>
                </select>
              </label>
              <label>
                rate
                <input type="number" step="0.05" min="0.01" max="1" value={distortionRate} onChange={(event) => setDistortionRate(Number(event.target.value))} />
              </label>
              {distortionType === 'gain_db' ? (
                <label>
                  gain_db
                  <input type="number" step="0.5" min="-30" max="30" value={distortionGainDb} onChange={(event) => setDistortionGainDb(Number(event.target.value))} />
                </label>
              ) : null}
              {distortionType === 'max_distortion' || distortionType === 'fence_distortion' ? (
                <label>
                  max_db
                  <input type="number" step="0.5" max="0" value={distortionMaxDb} onChange={(event) => setDistortionMaxDb(Number(event.target.value))} />
                </label>
              ) : null}
              {distortionType === 'fence_distortion' || distortionType === 'jag_distortion' ? (
                <label>
                  mask_number
                  <input type="number" step="1" min="0" max="12" value={distortionMaskNumber} onChange={(event) => setDistortionMaskNumber(Number(event.target.value))} />
                </label>
              ) : null}
            </>
          ) : null}
          {seedKinds.has(kind) ? (
            <label>
              seed
              <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
            </label>
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
