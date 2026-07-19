import { buildMapBrief } from "../mapBrief";
import type { GraphState, SceneEntity, SpaceMapMode } from "../types";
import { StatusMark } from "./StatusMark";

interface MapBriefProps {
  state: GraphState;
  scene: SceneEntity[];
  selectedId: string | null;
  seed: number;
  mode: SpaceMapMode;
  onOpenSystem: (id: string) => void;
  onOpenShipyard: () => void;
  onOpenAdvanced: () => void;
  readOnly?: boolean;
}

export function MapBrief({ state, scene, selectedId, seed, mode, onOpenSystem, onOpenShipyard, onOpenAdvanced, readOnly = false }: MapBriefProps) {
  const brief = buildMapBrief(state, scene, selectedId, seed);
  if (!brief) return null;

  return (
    <aside className={`map-brief map-brief-${brief.kind}`} aria-label={`Selected ${brief.kindLabel}`} aria-live="polite">
      <div className="map-brief-heading">
        <span className="map-brief-object" aria-hidden="true"><i /></span>
        <div><span className="eyebrow">SELECTED · {brief.kindLabel.toUpperCase()}</span><h2>{brief.title}</h2></div>
        <StatusMark status={brief.status} />
      </div>
      <p className="map-brief-summary">{brief.summary}</p>
      <div className="map-brief-assignment">
        <span>{brief.assignmentLabel}</span>
        <strong>{brief.assignmentValue}</strong>
      </div>
      <dl className="map-brief-facts">
        {brief.facts.map((fact) => <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}
      </dl>
      <div className="map-brief-actions">
        {mode === "galaxy" && brief.systemId && <button className="primary-button" onClick={() => onOpenSystem(brief.systemId!)}>Enter system</button>}
        {mode === "system" && brief.kind === "home" && !readOnly && <button className="primary-button" onClick={onOpenShipyard}>Open shipyard</button>}
        <button className="quiet-button" onClick={onOpenAdvanced}>Full details</button>
      </div>
    </aside>
  );
}
