export type Status = "created" | "requested" | "running" | "completed" | "failed" | "validated" | "disputed" | "promoted" | "resolved" | "pending" | string;

export interface Entity {
  id: string;
  run_id?: string;
  title?: string;
  name?: string;
  description?: string;
  summary?: string;
  statement?: string;
  status?: Status;
  _sequence?: number;
  [key: string]: unknown;
}

export interface NodeEntity extends Entity {
  parent_node_id?: string | null;
  node_type?: string;
  progress?: number;
  assigned_agent_ids?: string[];
}

export interface EdgeEntity extends Entity {
  source_id: string;
  target_id: string;
  edge_type?: string;
}

export interface GraphState {
  schema_version: number;
  run: Entity & { run_seed?: number; objective?: string; token_metrics?: Record<string, number>; cost_metrics?: Record<string, number> };
  nodes: NodeEntity[];
  agents: Entity[];
  tool_calls: Entity[];
  datasets: Entity[];
  dataset_versions: Entity[];
  transformations: Entity[];
  artifacts: Entity[];
  claims: Entity[];
  evidence: Entity[];
  findings: Entity[];
  decisions: Entity[];
  anomalies: Entity[];
  approvals: Entity[];
  annotations: Entity[];
  metrics: Entity[];
  edges: EdgeEntity[];
  unknown_events: string[];
  last_sequence: number;
  event_count: number;
}

export interface RunSummary {
  id: string;
  title: string;
  objective: string;
  status: Status;
  seed: number;
  privacy_class: string;
  last_sequence: number;
  created_at: string;
  updated_at: string;
  counts: Record<string, number>;
  latest_metric?: Entity;
}

export type ViewName = "galaxy" | "system" | "advanced" | "tree" | "findings" | "timeline" | "agents" | "artifacts" | "datasets" | "metrics" | "telemetry" | "comparison";

export type SpaceMapMode = "galaxy" | "system";

export interface SceneEntity {
  id: string;
  title: string;
  kind: "home" | "node" | "artifact" | "finding" | "anomaly" | "agent" | "tool";
  status: Status;
  parentId?: string | null;
  progress?: number;
  sequence?: number;
}

export interface PositionedEntity extends SceneEntity {
  x: number;
  y: number;
  z: number;
  radius: number;
  angle: number;
  depth?: number;
}

export interface ShipBlueprint {
  id: string;
  name: string;
  hull: "frigate" | "mothership" | "colony" | "specialist";
  role: string;
  description: string;
  capabilities: string[];
  source_node_id?: string | null;
  source_title?: string | null;
}

export interface ShipyardState {
  blueprints: ShipBlueprint[];
  ships: Entity[];
  dispatch_enabled: boolean;
  codex_available: boolean;
  safety: {
    transport: string;
    sandbox: string;
    approval_policy: string;
    workspace_fixed: boolean;
  };
}

export interface MissionReceipt {
  accepted: boolean;
  ship_id: string;
  thread_id: string;
  turn_id: string;
  status: string;
}
