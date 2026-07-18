import { stellarProfilesFor } from "./galaxyFrontier";
import type { Entity, GraphState, SceneEntity } from "./types";

export interface MapBriefFact {
  label: string;
  value: string;
}

export interface MapBriefModel {
  id: string;
  kind: SceneEntity["kind"];
  kindLabel: string;
  title: string;
  status: string;
  summary: string;
  systemId: string | null;
  systemTitle: string | null;
  assignmentLabel: string;
  assignmentValue: string;
  facts: MapBriefFact[];
}

function text(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function listText(value: unknown): string | null {
  if (Array.isArray(value)) {
    const values = value.map((item) => String(item).trim()).filter(Boolean);
    return values.length ? values.join(" · ") : null;
  }
  return text(value);
}

function sentence(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return trimmed;
  return `${trimmed.charAt(0).toUpperCase()}${trimmed.slice(1)}${/[.!?]$/.test(trimmed) ? "" : "."}`;
}

function compactType(value: unknown): string {
  return String(value ?? "recorded").replaceAll("_", " ");
}

function findRecord(state: GraphState, sceneEntity: SceneEntity): Entity {
  const collections: Entity[][] = [state.nodes, state.agents, state.tool_calls, state.artifacts, state.findings, state.anomalies];
  return collections.flat().find((entity) => entity.id === sceneEntity.id) ?? { id: sceneEntity.id, title: sceneEntity.title, status: sceneEntity.status };
}

function systemFor(state: GraphState, scene: SceneEntity[], sceneEntity: SceneEntity): { id: string; title: string } | null {
  const systemId = ["home", "node"].includes(sceneEntity.kind) ? sceneEntity.id : sceneEntity.parentId;
  if (!systemId) return null;
  const systemScene = scene.find((entity) => entity.id === systemId);
  const systemNode = state.nodes.find((node) => node.id === systemId);
  return { id: systemId, title: String(systemScene?.title ?? systemNode?.title ?? "Unknown system") };
}

function activityForAgent(agent: Entity, systemTitle: string, systemDescription: string | null): string {
  const explicitTask = text(agent.current_task);
  if (explicitTask) return sentence(explicitTask);
  if (String(agent.status) === "completed") return `Assignment in ${systemTitle} is complete.`;
  if (systemDescription) return `Current assignment: ${sentence(systemDescription)}`;
  return `Working in ${systemTitle}.`;
}

export function buildMapBrief(state: GraphState, scene: SceneEntity[], selectedId: string | null, seed: number): MapBriefModel | null {
  const sceneEntity = scene.find((entity) => entity.id === selectedId);
  if (!sceneEntity) return null;
  const record = findRecord(state, sceneEntity);
  const system = systemFor(state, scene, sceneEntity);
  const systemNode = system ? state.nodes.find((node) => node.id === system.id) : null;
  const systemDescription = text(systemNode?.description);
  const title = String(record.title ?? record.name ?? sceneEntity.title);
  const status = String(record.status ?? sceneEntity.status ?? "recorded");
  const stationedAgents = system
    ? state.agents.filter((agent) => String(agent.current_node_id ?? "") === system.id)
    : [];
  const trackedObjects = system
    ? scene.filter((entity) => entity.parentId === system.id && entity.kind !== "agent").length
    : 0;

  if (sceneEntity.kind === "agent") {
    const role = text(record.role) ?? "Analysis specialist";
    return {
      id: sceneEntity.id,
      kind: sceneEntity.kind,
      kindLabel: "Agent vessel",
      title,
      status,
      summary: activityForAgent(record, system?.title ?? "unassigned space", systemDescription),
      systemId: system?.id ?? null,
      systemTitle: system?.title ?? null,
      assignmentLabel: "Current station",
      assignmentValue: system?.title ?? "Awaiting assignment",
      facts: [
        { label: "Role", value: role },
        { label: "Framework", value: text(record.framework) ?? text(record.model) ?? "Local" },
        { label: "Capabilities", value: listText(record.capabilities) ?? "Analysis" },
      ],
    };
  }

  if (["home", "node"].includes(sceneEntity.kind)) {
    const systemIds = scene.filter((entity) => ["home", "node"].includes(entity.kind)).map((entity) => entity.id);
    const stellarProfile = stellarProfilesFor(systemIds, seed).get(sceneEntity.id);
    const agents = stationedAgents.map((agent) => String(agent.name ?? agent.id));
    return {
      id: sceneEntity.id,
      kind: sceneEntity.kind,
      kindLabel: sceneEntity.kind === "home" ? "Command star system" : "Analysis star system",
      title,
      status,
      summary: text(record.description) ?? text(record.summary) ?? "A charted analysis system in the active investigation.",
      systemId: sceneEntity.id,
      systemTitle: title,
      assignmentLabel: agents.length ? "Agents on station" : "Operational state",
      assignmentValue: agents.length ? agents.slice(0, 3).join(" · ") : status,
      facts: [
        { label: "Stellar class", value: stellarProfile?.label ?? "Main-sequence star" },
        { label: "Progress", value: `${Math.round(Number(record.progress ?? sceneEntity.progress ?? 0) * 100)}%` },
        { label: "Tracked objects", value: trackedObjects.toLocaleString() },
      ],
    };
  }

  const shared = {
    id: sceneEntity.id,
    kind: sceneEntity.kind,
    title,
    status,
    systemId: system?.id ?? null,
    systemTitle: system?.title ?? null,
    assignmentLabel: "Located in",
    assignmentValue: system?.title ?? "Uncharted space",
  };

  if (sceneEntity.kind === "artifact") {
    const provenance = typeof record.provenance === "object" && record.provenance !== null ? record.provenance as Record<string, unknown> : {};
    const producer = state.agents.find((agent) => agent.id === provenance.agent_id);
    return {
      ...shared,
      kindLabel: "Evidence planet",
      summary: text(record.description) ?? "A portable evidence object produced in this system.",
      facts: [
        { label: "Format", value: compactType(record.artifact_type ?? record.mime_type) },
        { label: "Produced by", value: String(producer?.name ?? provenance.agent_id ?? "Unknown agent") },
        { label: "Preview", value: compactType(record.preview_status ?? "recorded") },
      ],
    };
  }

  if (sceneEntity.kind === "finding") {
    return {
      ...shared,
      kindLabel: "Finding beacon",
      summary: text(record.summary) ?? "A finding recorded in this system.",
      facts: [
        { label: "Validation", value: compactType(record.validation_status ?? status) },
        { label: "Importance", value: compactType(record.importance ?? "recorded") },
        { label: "Reproducible", value: record.reproducible === true ? "Yes" : record.reproducible === false ? "No" : "Not recorded" },
      ],
    };
  }

  if (sceneEntity.kind === "tool") {
    return {
      ...shared,
      kindLabel: "Tool operation",
      summary: `${text(record.tool_name) ?? "Codex tool"} ${status === "completed" ? "completed" : "is being tracked"}.`,
      facts: [
        { label: "Tool", value: text(record.tool_name) ?? "Unknown" },
        { label: "State", value: compactType(status) },
        { label: "Content", value: "Redacted by default" },
      ],
    };
  }

  return {
    ...shared,
    kindLabel: "Anomaly signal",
    summary: text(record.description) ?? "An anomaly detected in this system.",
    facts: [
      { label: "Severity", value: compactType(record.severity ?? "recorded") },
      { label: "Resolution", value: text(record.resolution) ?? "Unresolved" },
    ],
  };
}
