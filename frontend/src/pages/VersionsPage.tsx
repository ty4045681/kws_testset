import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { CoveragePanel } from '../components/CoveragePanel';
import { ErrorSummary } from '../components/ErrorSummary';
import type { DatasetItem, DatasetVersion, ExportResponse } from '../types/api';

export function VersionsPage() {
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [selected, setSelected] = useState<DatasetVersion | null>(null);
  const [items, setItems] = useState<DatasetItem[]>([]);
  const [exportResult, setExportResult] = useState<ExportResponse | null>(null);
  const [error, setError] = useState<unknown>(null);

  async function load() {
    const response = await api.listDatasetVersions();
    setVersions(response.items);
  }

  async function selectVersion(version: DatasetVersion) {
    setSelected(version);
    setExportResult(null);
    const response = await api.getDatasetVersionItems(version.id);
    setItems(response.items);
  }

  async function exportVersion() {
    if (!selected) return;
    setExportResult(await api.exportDatasetVersion(selected.id));
    await load();
  }

  useEffect(() => {
    load().catch(setError);
  }, []);

  return (
    <section>
      <h1>Versions / Export</h1>
      <ErrorSummary error={error} />
      <div className="toolbar">
        <button onClick={() => load().catch(setError)}>刷新</button>
      </div>
      <div className="card-grid">
        <div className="panel">
          <h2>Versions</h2>
          <table>
            <thead>
              <tr>
                <th>name</th>
                <th>items</th>
                <th>status</th>
                <th>action</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((version) => (
                <tr key={version.id}>
                  <td>{version.name}</td>
                  <td>{version.item_count}</td>
                  <td>{version.build_status}</td>
                  <td>
                    <button onClick={() => selectVersion(version).catch(setError)}>查看</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h2>Selected</h2>
          {selected ? (
            <>
              <p>{selected.name}</p>
              <CoveragePanel coverage={selected.coverage_summary} />
              <button className="primary" onClick={() => exportVersion().catch(setError)}>
                导出
              </button>
            </>
          ) : (
            <p className="muted">请选择版本。</p>
          )}
          {exportResult ? (
            <div className="warning-box">
              <strong>导出完成</strong>
              <br />
              {exportResult.export_dir}
              <br />
              negative_hours={exportResult.negative_hours}
            </div>
          ) : null}
        </div>
      </div>
      <div className="panel">
        <h2>Items</h2>
        <table>
          <thead>
            <tr>
              <th>rank</th>
              <th>id</th>
              <th>type</th>
              <th>text</th>
              <th>duration</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.selection_rank}</td>
                <td>{item.id}</td>
                <td>{item.sample_type}</td>
                <td>{item.text}</td>
                <td>{item.duration_sec.toFixed(2)}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
