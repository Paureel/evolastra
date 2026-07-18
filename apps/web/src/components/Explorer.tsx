import type { GraphState, RunSummary } from "../types";
import { StatusMark } from "./StatusMark";

interface ExplorerProps {
  runs: RunSummary[];
  activeRunId: string | null;
  onRunChange: (runId: string) => void;
  state: GraphState | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function Explorer({ runs, activeRunId, onRunChange, state, selectedId, onSelect }: ExplorerProps) {
  const nexus = state?.nodes.find((node) => !node.parent_node_id);
  return (
    <aside className="explorer panel" aria-label="Analysis explorer">
      <div className="panel-heading">
        <span className="eyebrow">SECTOR INDEX</span>
        <span className="panel-count">{runs.length.toString().padStart(2, "0")}</span>
      </div>
      <label className="field-label" htmlFor="run-select">Active analysis</label>
      <select id="run-select" value={activeRunId ?? ""} onChange={(event) => onRunChange(event.target.value)}>
        {runs.map((run) => <option value={run.id} key={run.id}>{run.title}</option>)}
      </select>
      {state ? (
        <nav className="branch-ledger" aria-label="Semantic branches">
          <button className={selectedId === (nexus?.id ?? state.run.id) ? "tree-row selected" : "tree-row"} onClick={() => onSelect(nexus?.id ?? state.run.id)}>
            <span className="tree-index nexus-glyph">N</span>
            <span><strong>{state.run.title}</strong><small>Run nexus</small></span>
          </button>
          {state.nodes
            .filter((node) => node.parent_node_id)
            .sort((left, right) => (left._sequence ?? 0) - (right._sequence ?? 0))
            .map((node, index) => (
              <button className={selectedId === node.id ? "tree-row selected" : "tree-row"} onClick={() => onSelect(node.id)} key={node.id}>
                <span className="tree-index">{String(index + 1).padStart(2, "0")}</span>
                <span><strong>{node.title}</strong><small><StatusMark status={node.status} /></small></span>
              </button>
            ))}
        </nav>
      ) : <div className="panel-empty">Waiting for the semantic graph…</div>}
    </aside>
  );
}
