import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import type { Asset, DatasetVersion } from '../types/api';

async function loadAllAssets(): Promise<Asset[]> {
  const limit = 500;
  let offset = 0;
  const assets: Asset[] = [];
  while (true) {
    const response = await api.listAssets({ limit, offset });
    assets.push(...response.items);
    offset += response.count;
    if (assets.length >= response.total || response.count === 0) {
      return assets;
    }
  }
}

export function DashboardPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([loadAllAssets(), api.listDatasetVersions()])
      .then(([assetItems, versionResponse]) => {
        setAssets(assetItems);
        setVersions(versionResponse.items);
      })
      .catch(setError);
  }, []);

  const ready = assets.filter((asset) => asset.quality_status === 'ready' && asset.validation.ok).length;
  const needsMetadata = assets.filter((asset) => !asset.validation.ok || asset.quality_status !== 'ready').length;
  const latest = versions[0] ?? null;

  return (
    <section>
      <h1>Dashboard</h1>
      <ErrorSummary error={error} />
      <div className="card-grid">
        <div className="metric-card"><span>Total Assets</span><strong>{assets.length}</strong></div>
        <div className="metric-card"><span>Ready</span><strong>{ready}</strong></div>
        <div className="metric-card"><span>Need Metadata</span><strong>{needsMetadata}</strong></div>
        <div className="metric-card"><span>Dataset Versions</span><strong>{versions.length}</strong></div>
      </div>
      <div className="panel">
        <h2>Latest Version</h2>
        {latest ? <p>{latest.name} · {latest.item_count} items · {latest.build_status}</p> : <p className="muted">暂无版本，请先创建 dataset spec 并构建。</p>}
      </div>
    </section>
  );
}
