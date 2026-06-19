export function BulkEditToolbar({ selectedCount, onApply }: { selectedCount: number; onApply: (patch: Record<string, string>) => void }) {
  return (
    <div className="bulk-toolbar">
      <span>已选择 {selectedCount} 条</span>
      <button disabled={selectedCount === 0} onClick={() => onApply({ quality_status: 'ready' })}>
        标记 ready
      </button>
      <button disabled={selectedCount === 0} onClick={() => onApply({ noise_scene: 'clean' })}>
        noise=clean
      </button>
      <button disabled={selectedCount === 0} onClick={() => onApply({ volume: 'normal', pitch: 'normal', speed: 'normal' })}>
        音量/音调/语速 normal
      </button>
    </div>
  );
}
