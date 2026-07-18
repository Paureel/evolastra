import type { Entity } from "../types";

type PreviewRow = Record<string, unknown>;

interface PreviewPayload {
  kind?: string;
  values?: unknown[];
  text?: string;
  sampled?: boolean;
  row_count?: number;
}

const LABEL_KEYS = ["label", "gene", "pair", "metric", "hypothesis", "category", "name"];
const SERIES_COLORS = ["#ffd36a", "#71e6e1", "#ad8aed"];

function isRow(value: unknown): value is PreviewRow {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function previewOf(artifact: Entity): PreviewPayload {
  return isRow(artifact.preview) ? artifact.preview as PreviewPayload : {};
}

function rowsOf(artifact: Entity): PreviewRow[] {
  const values = previewOf(artifact).values;
  return Array.isArray(values) ? values.filter(isRow) : [];
}

function labelKeyFor(rows: PreviewRow[]): string | null {
  return LABEL_KEYS.find((key) => rows.some((row) => typeof row[key] === "string")) ??
    Object.keys(rows[0] ?? {}).find((key) => rows.some((row) => typeof row[key] === "string")) ?? null;
}

function numericKeysFor(rows: PreviewRow[], labelKey: string | null): string[] {
  const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const numeric = keys.filter((key) => key !== labelKey && rows.some((row) => Number.isFinite(Number(row[key]))));
  const preferred = ["value", "gain_pct", "high_gain_pct", "loss_pct", "deep_loss_pct", "both", "odds_ratio", "q_value"];
  return [...preferred.filter((key) => numeric.includes(key)), ...numeric.filter((key) => !preferred.includes(key))];
}

function numberValue(value: unknown): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function formatNumber(value: unknown, key = ""): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "—");
  if (key.endsWith("_pct")) return `${number.toFixed(1)}%`;
  if (key === "q_value" || key === "p_value") return number < 0.001 ? number.toExponential(2) : number.toFixed(3);
  return Number.isInteger(number) ? number.toLocaleString() : number.toFixed(2);
}

function labelFor(row: PreviewRow, labelKey: string | null, index: number): string {
  return String((labelKey && row[labelKey]) ?? `Row ${index + 1}`);
}

function CnaFrequencyFigure({ rows, compact = false }: { rows: PreviewRow[]; compact?: boolean }) {
  const shown = rows.slice(0, compact ? 8 : 12);
  const axisMaximum = Math.max(10, Math.ceil(Math.max(...shown.flatMap((row) => [numberValue(row.gain_pct), numberValue(row.loss_pct)])) / 10) * 10);
  if (compact) {
    return <div className="figure-thumbnail-plot" aria-hidden="true">
      {shown.map((row, index) => <span key={`${String(row.gene)}:${index}`}><i className="thumb-loss" style={{ width: `${numberValue(row.loss_pct) / axisMaximum * 48}%` }} /><i className="thumb-gain" style={{ width: `${numberValue(row.gain_pct) / axisMaximum * 48}%` }} /></span>)}
    </div>;
  }
  return <figure className="scientific-figure cna-frequency-figure" aria-labelledby="cna-figure-caption">
    <figcaption id="cna-figure-caption"><strong>Copy-number event frequency</strong><span>Loss ← tumors (%) → Gain</span></figcaption>
    <div className="figure-legend" aria-label="Figure legend"><span><i className="legend-loss" />Loss</span><span><i className="legend-deep-loss" />Deep loss</span><span><i className="legend-gain" />Gain</span><span><i className="legend-high-gain" />High gain</span></div>
    <div className="cna-axis" aria-hidden="true"><span>{axisMaximum}%</span><i /><span>0</span><i /><span>{axisMaximum}%</span></div>
    <div className="cna-rows">
      {shown.map((row, index) => {
        const loss = numberValue(row.loss_pct);
        const deepLoss = numberValue(row.deep_loss_pct);
        const gain = numberValue(row.gain_pct);
        const highGain = numberValue(row.high_gain_pct);
        return <div className="cna-row" key={`${String(row.gene)}:${index}`}>
          <span className="figure-row-label"><strong>{String(row.gene ?? `Row ${index + 1}`)}</strong><small>{String(row.cytoband ?? "")}</small></span>
          <span className="cna-half cna-loss" aria-label={`${String(row.gene)} loss ${loss.toFixed(1)} percent, deep loss ${deepLoss.toFixed(1)} percent`}><i style={{ width: `${loss / axisMaximum * 100}%` }} /><b style={{ width: `${deepLoss / axisMaximum * 100}%` }} /></span>
          <span className="cna-center" aria-hidden="true" />
          <span className="cna-half cna-gain" aria-label={`${String(row.gene)} gain ${gain.toFixed(1)} percent, high gain ${highGain.toFixed(1)} percent`}><i style={{ width: `${gain / axisMaximum * 100}%` }} /><b style={{ width: `${highGain / axisMaximum * 100}%` }} /></span>
          <span className="figure-row-values"><small>−{loss.toFixed(1)}</small><small>+{gain.toFixed(1)}</small></span>
        </div>;
      })}
    </div>
    {rows.length > shown.length && <p className="figure-note">Showing the first {shown.length} of {rows.length} bounded rows.</p>}
  </figure>;
}

function QuantitativeFigure({ rows, compact = false }: { rows: PreviewRow[]; compact?: boolean }) {
  const labelKey = labelKeyFor(rows);
  const keys = numericKeysFor(rows, labelKey).slice(0, 3);
  const shown = rows.slice(0, compact ? 8 : 12);
  const maximum = Math.max(0.01, ...shown.flatMap((row) => keys.map((key) => Math.abs(numberValue(row[key])))));
  if (compact) {
    return <div className="figure-thumbnail-plot quantitative" aria-hidden="true">{shown.map((row, index) => <span key={index}><i style={{ width: `${Math.abs(numberValue(row[keys[0]])) / maximum * 100}%` }} /></span>)}</div>;
  }
  return <figure className="scientific-figure quantitative-figure" aria-labelledby="quantitative-figure-caption">
    <figcaption id="quantitative-figure-caption"><strong>Bounded quantitative preview</strong><span>{shown.length} displayed rows · exact values retained</span></figcaption>
    <div className="figure-legend">{keys.map((key, index) => <span key={key}><i style={{ background: SERIES_COLORS[index] }} />{key.replaceAll("_", " ")}</span>)}</div>
    <div className="quantitative-rows">
      {shown.map((row, rowIndex) => <div className="quantitative-row" key={`${labelFor(row, labelKey, rowIndex)}:${rowIndex}`}>
        <span className="figure-row-label"><strong>{labelFor(row, labelKey, rowIndex)}</strong>{typeof row.cytoband === "string" && <small>{row.cytoband}</small>}</span>
        <span className="quantitative-bars">{keys.map((key, index) => <i key={key} title={`${key.replaceAll("_", " ")}: ${formatNumber(row[key], key)}`} style={{ width: `${Math.abs(numberValue(row[key])) / maximum * 100}%`, background: SERIES_COLORS[index] }} />)}</span>
        <span className="quantitative-values">{keys.map((key) => <small key={key}>{formatNumber(row[key], key)}</small>)}</span>
      </div>)}
    </div>
  </figure>;
}

function StructuredPreview({ rows }: { rows: PreviewRow[] }) {
  const labelKey = labelKeyFor(rows);
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))].slice(0, 6);
  if (labelKey && rows.every((row) => Object.keys(row).length <= 2)) {
    return <div className="structured-preview">{rows.map((row, index) => <article key={index}><span>{String(row[labelKey] ?? `Item ${index + 1}`)}</span><p>{String(Object.entries(row).find(([key]) => key !== labelKey)?.[1] ?? "")}</p></article>)}</div>;
  }
  return <div className="structured-preview">
    <div className="preview-table-wrap"><table><thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{rows.slice(0, 20).map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{formatNumber(row[column], column)}</td>)}</tr>)}</tbody></table></div>
  </div>;
}

export function ArtifactFigureThumbnail({ artifact }: { artifact: Entity }) {
  const rows = rowsOf(artifact);
  if (rows.some((row) => "gain_pct" in row && "loss_pct" in row)) return <CnaFrequencyFigure rows={rows} compact />;
  if (numericKeysFor(rows, labelKeyFor(rows)).length) return <QuantitativeFigure rows={rows} compact />;
  return <div className="figure-thumbnail-lines" aria-hidden="true">{rows.slice(0, 5).map((_, index) => <i key={index} />)}</div>;
}

export function ArtifactPreview({ artifact, onClose }: { artifact: Entity | null; onClose: () => void }) {
  if (!artifact) return null;
  const preview = previewOf(artifact);
  const rows = rowsOf(artifact);
  const cna = rows.some((row) => "gain_pct" in row && "loss_pct" in row);
  const quantitative = !cna && numericKeysFor(rows, labelKeyFor(rows)).length > 0;
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="artifact-modal" role="dialog" aria-modal="true" aria-labelledby="artifact-title">
      <div className="modal-head">
        <div><span className="eyebrow">SAFE FIGURE · DATA ONLY · NO CODE EXECUTION</span><h2 id="artifact-title">{String(artifact.title ?? "Artifact")}</h2></div>
        <button className="icon-button" onClick={onClose} aria-label="Close preview">×</button>
      </div>
      <div className="artifact-preview-body">
        {cna ? <CnaFrequencyFigure rows={rows} /> : quantitative ? <QuantitativeFigure rows={rows} /> : rows.length ? <StructuredPreview rows={rows} /> : preview.text ? <pre className="markdown-preview">{preview.text}</pre> : <div className="preview-empty"><span aria-hidden="true">◇</span><h3>No bounded preview data</h3><p>The artifact is recorded, but it does not contain a safe text, table, or numeric figure payload.</p></div>}
      </div>
      <footer className="preview-footer">
        <span>{String(artifact.mime_type ?? "application/octet-stream")}</span>
        <span>{preview.sampled ? "Sampled" : "Complete"}{preview.row_count ? ` · ${preview.row_count} rows` : ""}</span>
        <span title={String(artifact.hash ?? "metadata-only")}>Integrity {String(artifact.hash ?? "metadata-only")}</span>
      </footer>
    </section>
  </div>;
}
