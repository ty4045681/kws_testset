import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ErrorSummary } from '../components/ErrorSummary';
import type { Taxonomy } from '../types/api';

export function SettingsPage() {
  const [taxonomy, setTaxonomy] = useState<Taxonomy>({});
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.taxonomy().then(setTaxonomy).catch(setError);
  }, []);

  return (
    <section>
      <h1>Settings</h1>
      <ErrorSummary error={error} />
      <div className="panel">
        <h2>运行配置</h2>
        <p>后端配置来自 <code>configs/app.yaml</code>。数据目录、导出目录和目标关键词由后端读取，UI 第一版只展示说明，不直接修改配置文件。</p>
        <pre>uv run python -m kws_testset serve</pre>
      </div>
      <div className="panel">
        <h2>Taxonomy</h2>
        {Object.entries(taxonomy).map(([key, values]) => (
          <div className="coverage-field" key={key}>
            <h4>{key}</h4>
            <div className="tag-list">{values.map((value) => <span className="tag" key={`${key}-${value}`}>{value}</span>)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
