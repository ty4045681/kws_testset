export function AudioPlayer({ assetId }: { assetId: string }) {
  return <audio controls preload="none" src={`/api/assets/${encodeURIComponent(assetId)}/audio`} className="audio-player" />;
}
