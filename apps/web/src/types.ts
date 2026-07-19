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

export interface SemanticSignature {
  program: string;
  alterationDirection: string;
  genes: string[];
  cytobands: string[];
  mechanisms: string[];
  therapeuticModalities: string[];
  validationModalities: string[];
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
  tags?: string[];
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
  semanticSignature?: SemanticSignature;
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
    network_access: boolean;
    web_search: string;
    environment_filtered: boolean;
    context_isolated: boolean;
  };
}

export interface MissionReceipt {
  accepted: boolean;
  ship_id: string;
  thread_id: string;
  turn_id: string;
  status: string;
}

export interface MultiplayerPlayer {
  id: string;
  display_name: string;
  color: string;
  role: "host" | "member";
  online: boolean;
  last_seen_at: string;
}

export interface MultiplayerClaim {
  id: string;
  node_id: string;
  player_id: string;
  claimed_at: string;
}

export interface MultiplayerPublication {
  id: string;
  finding_id: string;
  player_id: string;
  title: string;
  summary: string;
  published_at: string;
}

export interface MultiplayerState {
  enabled: boolean;
  session?: {
    id: string;
    run_id: string;
    mode: "host" | "guest";
    status: "active" | "paused" | "closed";
    revision: number;
    host_url: string;
    project_fingerprint: string;
    local_player_id: string;
    title: string;
    simulation_active?: boolean;
  };
  players?: MultiplayerPlayer[];
  claims?: MultiplayerClaim[];
  publications?: MultiplayerPublication[];
  connection_error?: string;
}

export interface MultiplayerReadiness {
  tailscale_installed: boolean;
  tailnet_ready: boolean;
  suggested_share_url: string | null;
  serve_command: string;
  stores_project_data: boolean;
}
