import type { CoverageSummary } from '../types/api';

export function CoveragePanel({ coverage }: { coverage: CoverageSummary | null }) {
  if (!coverage) return <p className="muted">暂无覆盖率数据。</p>;
  return (
    <div className="coverage-panel">
      <div className="metric-card">
        <span>Total</span>
        <strong>{coverage.total}</strong>
      </div>
      {coverage.shortfalls && Object.keys(coverage.shortfalls).length > 0 ? <div className="warning-box">Shortfalls: {JSON.stringify(coverage.shortfalls)}</div> : null}
      {coverage.by_field
        ? Object.entries(coverage.by_field).map(([field, values]) => (
            <div className="coverage-field" key={field}>
              <h4>{field}</h4>
              <div className="tag-list">
                {Object.entries(values).map(([value, count]) => (
                  <span className="tag" key={`${field}-${value}`}>
                    {value}: {count}
                  </span>
                ))}
              </div>
            </div>
          ))
        : null}
    </div>
  );
}
