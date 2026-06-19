import { ApiError } from '../api/client';

function detailToLines(detail: unknown): string[] {
  if (typeof detail === 'string') return [detail];
  if (Array.isArray(detail)) return detail.map(String);
  if (detail && typeof detail === 'object' && 'errors' in detail) {
    const errors = (detail as { errors?: unknown }).errors;
    return Array.isArray(errors) ? errors.map(String) : [JSON.stringify(detail)];
  }
  return [JSON.stringify(detail)];
}

export function ErrorSummary({ error }: { error: unknown }) {
  if (!error) return null;
  const lines = error instanceof ApiError ? detailToLines(error.detail) : [error instanceof Error ? error.message : String(error)];
  return (
    <div className="error-summary">
      <strong>操作失败</strong>
      <ul>
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}
