import type { Entity, GraphState, RunSummary, ViewName } from "../types";
import { buildTechTiers, type TechState } from "../techTree";
import { ArtifactFigureThumbnail } from "./ArtifactPreview";
import { StatusMark } from "./StatusMark";

function EntityTable({ items, onSelect }: { items: Entity[]; onSelect: (id: string) => void }) {
  if (!items.length) return <div className="workspace-empty"><span className="empty-orbit" /><h3>Nothing recorded yet</h3><p>This view fills as durable events are projected.</p></div>;
  return (
    <div className="entity-table" role="table">
      {items.map((item) => (
        <button role="row" className="entity-row" key={item.id} onClick={() => onSelect(item.id)}>
          <span role="cell"><strong>{String(item.title ?? item.name ?? item.tool_name ?? item.id)}</strong><small>{String(item.summary ?? item.statement ?? item.description ?? item.id)}</small></span>
          <span role="cell"><StatusMark status={String(item.status ?? item.validation_status ?? "recorded")} /></span>
          <span role="cell" className="mono">#{String(item._sequence ?? "—")}</span>
        </button>
      ))}
    </div>
  );
}

export function WorkspaceView({ view, state, runs, currentRunId, onSelect, onOpenShipyard, onOpenArtifact }: { view: ViewName; state: GraphState; runs: RunSummary[]; currentRunId: string | null; onSelect: (id: string) => void; onOpenShipyard: (blueprintId: string) => void; onOpenArtifact: (artifact: Entity) => void }) {
  if (view === "tree") {
    const root = state.nodes.find((node) => !node.parent_node_id);
    const tiers = buildTechTiers(state.nodes.filter((node) => node.parent_node_id));
    const counts = tiers.flatMap((tier) => tier.nodes).reduce<Record<TechState, number>>((result, node) => {
      result[node.techState] += 1;
      return result;
    }, { completed: 0, researching: 0, available: 0, locked: 0 });
    const stateLabel: Record<TechState, string> = { completed: "Researched", researching: "Researching", available: "Available", locked: "Locked" };
    return <section className="workspace-view tech-tree-view" aria-label="Research tech tree">
      <div className="tech-tree-title">
        <div><span className="eyebrow">RESEARCH PROGRESSION</span><h2>Tech tree</h2><p>Analysis capabilities unlock as their prerequisite research completes.</p></div>
        <div className="tech-tree-summary" aria-label="Technology status summary"><span><i className="tech-dot completed" />{counts.completed} researched</span><span><i className="tech-dot researching" />{counts.researching} active</span><span><i className="tech-dot available" />{counts.available} available</span><span><i className="tech-dot locked" />{counts.locked} locked</span></div>
      </div>
      <div className="tech-tree-scroll">
        <div className="tech-tree-map" role="region" aria-label="Technology dependencies" style={{ gridTemplateColumns: `220px repeat(${tiers.length}, minmax(190px, 1fr))`, minWidth: `${220 + tiers.length * 224}px` }}>
          <div className="tech-nexus-column">
            <span className="tech-tier-label"><b>Research nexus</b><small>Objective</small></span>
            {root && <button className="tech-node tech-nexus researching" onClick={() => onSelect(root.id)}>
              <span className="tech-node-glyph" aria-hidden="true"><i>✧</i></span>
              <span className="tech-node-copy"><small>PRIMARY DIRECTIVE</small><strong>{root.title}</strong><span>{Math.round((root.progress ?? 0) * 100)}% complete</span></span>
              <i className="tech-port" aria-hidden="true" />
            </button>}
          </div>
          {tiers.map((tier, tierIndex) => (
            <div className="tech-tier" role="group" aria-label={tier.label} key={tier.id}>
              <span className="tech-tier-label"><b>{tier.label}</b><small>Tier {tierIndex + 1}</small></span>
              <div className="tech-tier-nodes">
                {tier.nodes.map((node) => <div className="tech-node-stack" key={node.id}>
                  <button
                    aria-disabled={node.techState === "locked"}
                    className={`tech-node ${node.techState}`}
                    onClick={() => { if (node.techState !== "locked") onSelect(node.id); }}
                  >
                    <i className="tech-connector-in" aria-hidden="true" />
                    <span className="tech-node-glyph" aria-hidden="true"><i>{tier.glyph}</i></span>
                    <span className="tech-node-copy"><small>{stateLabel[node.techState]}</small><strong>{node.title}</strong><span>{String(node.node_type ?? "research")} · {Math.round((node.progress ?? 0) * 100)}%</span></span>
                    <span className="tech-progress" aria-hidden="true"><i style={{ width: `${Math.round((node.progress ?? 0) * 100)}%` }} /></span>
                    <i className="tech-port" aria-hidden="true" />
                  </button>
                  {node.techState === "completed" && <button className="tech-build-button" onClick={() => onOpenShipyard(`specialist:${node.id}`)}>Build specialist ship</button>}
                </div>)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>;
  }
  if (view === "findings") return <section className="workspace-view"><div className="workspace-title"><span className="eyebrow">EPISTEMIC WORKSPACE</span><h2>Findings and contradictions</h2><p>Validation is explicit; confident prose never substitutes for evidence.</p></div><EntityTable items={[...state.findings, ...state.claims.filter((claim) => claim.status === "disputed")]} onSelect={onSelect} /></section>;
  if (view === "timeline") return <section className="workspace-view"><div className="workspace-title"><span className="eyebrow">DURABLE EVENT TIME</span><h2>Semantic timeline</h2></div><EntityTable items={[...state.nodes, ...state.artifacts, ...state.findings, ...state.anomalies].sort((a, b) => (b._sequence ?? 0) - (a._sequence ?? 0))} onSelect={onSelect} /></section>;
  if (view === "artifacts") return <section className="workspace-view figure-workspace" aria-label="Analysis figures">
    <div className="workspace-title"><span className="eyebrow">SAFE SCIENTIFIC PLATES</span><h2>Figures and previews</h2><p>Rendered from bounded artifact data. No uploaded HTML, scripts, notebooks, or SVG behavior executes here.</p></div>
    {state.artifacts.length ? <div className="figure-gallery">{state.artifacts.map((artifact, index) => <button className="figure-card" key={artifact.id} onClick={() => { onSelect(artifact.id); onOpenArtifact(artifact); }} aria-label={`Open figure ${String(artifact.title ?? artifact.id)}`}>
      <span className="figure-card-index">FIG {String(index + 1).padStart(2, "0")}</span>
      <ArtifactFigureThumbnail artifact={artifact} />
      <span className="figure-card-copy"><strong>{String(artifact.title ?? artifact.id)}</strong><small>{String((artifact.preview as { row_count?: number } | undefined)?.row_count ?? "—")} rows · {String(artifact.mime_type ?? "data")}</small></span>
      <span className="figure-card-action">Open figure <i aria-hidden="true">↗</i></span>
    </button>)}</div> : <div className="workspace-empty"><span className="empty-orbit" /><h3>No figures yet</h3><p>Figures appear when an analysis records bounded artifact preview data.</p></div>}
  </section>;
  if (view === "comparison") {
    const current = runs.find((run) => run.id === currentRunId);
    const other = runs.find((run) => run.id !== currentRunId);
    const keys = ["nodes", "agents", "tool_calls", "artifacts", "claims", "findings", "anomalies"];
    return <section className="workspace-view"><div className="workspace-title"><span className="eyebrow">RUN COMPARISON</span><h2>{other ? `${current?.title ?? "Current run"} ↔ ${other.title}` : "A second run is required"}</h2><p>Counts compare semantic projections; use exports for exact event-level diffing.</p></div>{other && current ? <div className="comparison-grid">{keys.map((key) => <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{current.counts[key] ?? 0}</strong><i>{(other.counts[key] ?? 0) - (current.counts[key] ?? 0) >= 0 ? "+" : ""}{(other.counts[key] ?? 0) - (current.counts[key] ?? 0)}</i><small>{other.counts[key] ?? 0} comparison</small></div>)}</div> : <div className="workspace-empty"><span className="empty-orbit" /><h3>No comparison run</h3><p>Start or import another run, then return to this view.</p></div>}</section>;
  }
  const map: Partial<Record<ViewName, Entity[]>> = { agents: state.agents, datasets: [...state.datasets, ...state.dataset_versions], metrics: state.metrics, telemetry: state.tool_calls };
  const names: Partial<Record<ViewName, string>> = { agents: "Agents and handoffs", datasets: "Datasets and lineage", metrics: "Tokens, cost, and timing", telemetry: "Tool and operational activity" };
  return <section className="workspace-view"><div className="workspace-title"><span className="eyebrow">{view.toUpperCase()}</span><h2>{names[view] ?? view}</h2></div><EntityTable items={map[view] ?? []} onSelect={onSelect} /></section>;
}
