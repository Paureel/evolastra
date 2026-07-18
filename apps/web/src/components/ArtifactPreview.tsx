import type { Entity } from "../types";

export function ArtifactPreview({ artifact, onClose }: { artifact: Entity | null; onClose: () => void }) {
  if (!artifact) return null;
  const preview = artifact.preview as { kind?: string; values?: Array<{ label: string; value: number }>; text?: string; sampled?: boolean; row_count?: number } | undefined;
  const values = preview?.values ?? [];
  const max = Math.max(0.01, ...values.map((item) => item.value));
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="artifact-modal" role="dialog" aria-modal="true" aria-labelledby="artifact-title">
        <div className="modal-head">
          <div><span className="eyebrow">SANDBOXED PREVIEW · NO CODE EXECUTION</span><h2 id="artifact-title">{String(artifact.title ?? "Artifact")}</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Close preview">×</button>
        </div>
        {values.length > 0 ? (
          <div className="bar-chart" role="img" aria-label={`Bar chart with ${values.length} values`}>
            {values.map((item) => (
              <div className="bar-row" key={item.label}>
                <span>{item.label}</span><progress max={max} value={item.value} /><strong>{item.value.toFixed(2)}</strong>
              </div>
            ))}
          </div>
        ) : <pre className="markdown-preview">{preview?.text ?? JSON.stringify(preview ?? {}, null, 2)}</pre>}
        <footer className="preview-footer">
          <span>{String(artifact.mime_type ?? "application/octet-stream")}</span>
          <span>{preview?.sampled ? "Sampled" : "Complete"}{preview?.row_count ? ` · ${preview.row_count} rows` : ""}</span>
          <span>Integrity {String(artifact.hash ?? "metadata-only")}</span>
        </footer>
      </section>
    </div>
  );
}
