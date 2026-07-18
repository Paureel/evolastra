import { recordApproval } from "../api";
import type { Entity, GraphState, SpaceMapMode } from "../types";
import { StatusMark } from "./StatusMark";

const COLLECTIONS: Array<keyof GraphState> = [
  "nodes", "agents", "tool_calls", "datasets", "dataset_versions", "artifacts", "claims", "evidence", "findings", "anomalies", "approvals",
];

export function findEntity(state: GraphState | null, id: string | null): { entity: Entity; kind: string } | null {
  if (!state || !id) return null;
  if (state.run.id === id) return { entity: state.run, kind: "run" };
  for (const key of COLLECTIONS) {
    const collection = state[key];
    if (!Array.isArray(collection)) continue;
    const match = (collection as Entity[]).find((entity) => entity.id === id);
    if (match) return { entity: match, kind: key.toString().replace(/s$/, "") };
  }
  return null;
}

function valueLabel(value: unknown): string {
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.join(", ");
  return "";
}

interface InspectorProps {
  state: GraphState | null;
  selectedId: string | null;
  onRefresh: () => Promise<void>;
  onOpenArtifact: (entity: Entity) => void;
  onOpenSystem: (id: string) => void;
  spaceMode: SpaceMapMode | null;
}

export function Inspector({ state, selectedId, onRefresh, onOpenArtifact, onOpenSystem, spaceMode }: InspectorProps) {
  const selected = findEntity(state, selectedId);
  if (!state) return <aside className="inspector panel panel-empty">Select a live run to inspect evidence.</aside>;
  if (!selected) {
    return (
      <aside className="inspector panel">
        <div className="panel-heading"><span className="eyebrow">INSPECTOR</span></div>
        <div className="empty-orbit" aria-hidden="true" />
        <h2>No object selected</h2>
        <p>Choose a system, artifact, agent, or finding. Every object keeps a route back to its event provenance.</p>
      </aside>
    );
  }
  const { entity, kind } = selected;
  const shown = Object.entries(entity).filter(([key, value]) =>
    !key.startsWith("_") && !["id", "run_id", "title", "name", "description", "summary", "statement", "status", "preview"].includes(key) &&
    ["string", "number", "boolean"].includes(typeof value) || Array.isArray(value),
  ).slice(0, 9);
  const title = String(entity.title ?? entity.name ?? entity.tool_name ?? entity.id);
  return (
    <aside className="inspector panel" aria-label={`${kind} inspector`}>
      <div className="panel-heading"><span className="eyebrow">{kind.toUpperCase()}</span><StatusMark status={String(entity.status ?? "recorded")} /></div>
      <h2>{title}</h2>
      <p className="inspector-summary">{String(entity.summary ?? entity.statement ?? entity.description ?? "No narrative summary was recorded.")}</p>
      <dl className="fact-grid">
        {shown.map(([key, value]) => (
          <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{valueLabel(value)}</dd></div>
        ))}
      </dl>
      {kind === "node" && spaceMode !== "system" && <button className="primary-button" onClick={() => onOpenSystem(entity.id)}>Enter system view</button>}
      {kind === "artifact" && <button className="primary-button" onClick={() => onOpenArtifact(entity)}>Open safe preview</button>}
      {kind === "approval" && entity.status === "pending" && (
        <div className="approval-actions">
          <button className="primary-button" onClick={() => void recordApproval(state.run.id, entity.id, "approved").then(onRefresh)}>Approve</button>
          <button className="quiet-button" onClick={() => void recordApproval(state.run.id, entity.id, "rejected").then(onRefresh)}>Reject</button>
        </div>
      )}
      <div className="provenance-stamp"><span>ENTITY</span><code>{entity.id}</code><span>SEQUENCE</span><code>{String(entity._sequence ?? "—")}</code></div>
    </aside>
  );
}
