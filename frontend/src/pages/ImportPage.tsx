import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import { StatusBadge } from '../components/StatusBadge';
import type { ImportCommitFile, Taxonomy, UploadRow } from '../types/api';

type EditableRow = UploadRow & ImportCommitFile;

function defaultRow(row: UploadRow): EditableRow {
  return {
    ...row,
    path: row.path,
    text: '',
    sample_type: 'wake_positive',
    quality_status: 'draft',
    voice_source: 'human',
    gender: 'unknown',
    age_group: 'unknown',
    volume: 'normal',
    pitch: 'normal',
    speed: 'normal',
    noise_scene: 'clean',
    impairment_type: 'none',
    notes: null
  };
}

export function ImportPage() {
  const [taxonomy, setTaxonomy] = useState<Taxonomy>({});
  const [rows, setRows] = useState<EditableRow[]>([]);
  const [batchName, setBatchName] = useState('browser_import');
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.taxonomy().then(setTaxonomy).catch(setError);
  }, []);

  async function upload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError(null);
    setMessage('');
    const response = await api.uploadWavs(Array.from(files));
    setRows(response.files.map(defaultRow));
    setMessage(`上传完成：可处理 ${response.uploaded}，失败 ${response.failed}`);
  }

  function updateRow(index: number, patch: Partial<EditableRow>) {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  function bulkApply(patch: Partial<EditableRow>) {
    setRows((current) => current.map((row) => (row.status === 'can_import' ? { ...row, ...patch } : row)));
  }

  async function commit() {
    setError(null);
    const files = rows
      .filter((row) => row.status === 'can_import')
      .map(({ original_filename, duration_sec, sample_rate, channels, bit_depth, sha256, status, error: _rowError, ...file }) => file);
    const response = await api.commitImport(batchName, files);
    if (response.files) {
      const byPath = new Map(response.files.map((item) => [item.path, item]));
      setRows((current) =>
        current.map((row) => {
          const result = byPath.get(row.path);
          if (!result || result.status !== 'error') return row;
          return { ...row, status: 'error', error: result.errors.join('; ') };
        })
      );
    }
    setMessage(`导入完成：${response.imported_count} 条，重复 ${response.duplicate_count} 条，失败 ${response.failed_count ?? 0} 条`);
  }

  const sampleTypes = taxonomy.sample_type ?? ['wake_positive', 'similar_negative', 'partial_wake', 'ordinary_negative'];
  const options = (key: string, fallback: string[]) => taxonomy[key] ?? fallback;

  return (
    <section>
      <h1>Import Wizard</h1>
      <ErrorSummary error={error} />
      {message ? <p className="warning-box">{message}</p> : null}
      <div className="toolbar">
        <input value={batchName} onChange={(event) => setBatchName(event.target.value)} aria-label="batch name" />
        <input type="file" accept=".wav,audio/wav" multiple onChange={(event) => upload(event.target.files).catch(setError)} />
        <button onClick={() => bulkApply({ text: '你好小智', sample_type: 'wake_positive' })}>批量正样本</button>
        <button onClick={() => bulkApply({ quality_status: 'ready' })}>批量 ready</button>
        <button className="primary" disabled={rows.filter((row) => row.status === 'can_import').length === 0} onClick={() => commit().catch(setError)}>
          提交导入
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>file</th>
            <th>status</th>
            <th>text</th>
            <th>sample_type</th>
            <th>quality</th>
            <th>voice</th>
            <th>gender</th>
            <th>noise</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.path}-${index}`}>
              <td>
                {row.original_filename}
                <br />
                <span className="muted">{row.duration_sec.toFixed(2)}s</span>
              </td>
              <td>
                <StatusBadge status={row.status} />
                {row.error ? <div className="muted">{row.error}</div> : null}
              </td>
              <td>
                <input value={row.text} onChange={(event) => updateRow(index, { text: event.target.value })} />
              </td>
              <td>
                <select value={row.sample_type} onChange={(event) => updateRow(index, { sample_type: event.target.value })}>
                  {sampleTypes.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </td>
              <td>
                <select value={row.quality_status} onChange={(event) => updateRow(index, { quality_status: event.target.value })}>
                  {options('quality_status', ['draft', 'ready', 'deprecated']).map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </td>
              <td>
                <select value={row.voice_source} onChange={(event) => updateRow(index, { voice_source: event.target.value })}>
                  {options('voice_source', ['human', 'synthetic', 'unknown']).map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </td>
              <td>
                <select value={row.gender} onChange={(event) => updateRow(index, { gender: event.target.value })}>
                  {options('gender', ['male', 'female', 'unknown']).map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </td>
              <td>
                <select value={row.noise_scene} onChange={(event) => updateRow(index, { noise_scene: event.target.value })}>
                  {options('noise_scene', ['clean', 'home', 'office', 'unknown']).map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
