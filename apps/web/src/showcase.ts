import type { Entity, GraphState, MultiplayerState, RunSummary } from "./types";

export const PUBLIC_SHOWCASE_PATH = "/demo/stad-three-empires-v1.json";
export const PUBLIC_SHOWCASE_ID = "stad-three-empires-v1";

export interface PublicShowcaseBundle {
  schema_version: 1;
  id: typeof PUBLIC_SHOWCASE_ID;
  public: true;
  title: string;
  notice: string;
  run: RunSummary;
  state: GraphState;
  multiplayer: MultiplayerState;
}

const ENTITY_COLLECTIONS = [
  "nodes", "agents", "tool_calls", "datasets", "dataset_versions",
  "transformations", "artifacts", "claims", "evidence", "findings",
  "decisions", "anomalies", "approvals", "annotations", "metrics", "edges",
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function parsePublicShowcase(value: unknown): PublicShowcaseBundle {
  if (!isRecord(value) || value.schema_version !== 1 || value.id !== PUBLIC_SHOWCASE_ID || value.public !== true) {
    throw new Error("The public showcase manifest is not recognized.");
  }
  if (!isRecord(value.run) || value.run.id !== "demo_run_stad_three_empires" || value.run.privacy_class !== "public") {
    throw new Error("The public showcase run is not explicitly public.");
  }
  const state = value.state;
  if (!isRecord(state) || !Array.isArray(state.nodes) || !Number.isInteger(state.last_sequence)) {
    throw new Error("The public showcase projection is incomplete.");
  }
  if (ENTITY_COLLECTIONS.some((key) => !Array.isArray(state[key]))) {
    throw new Error("The public showcase projection collections are incomplete.");
  }
  if (Number(state.last_sequence) < 1 || Number(state.last_sequence) > 12 || state.run !== undefined && (!isRecord(state.run) || state.run.id !== value.run.id)) {
    throw new Error("The public showcase projection is outside its supported bounds.");
  }
  if (!isRecord(value.multiplayer) || value.multiplayer.enabled !== true) {
    throw new Error("The public showcase federation is incomplete.");
  }
  return value as unknown as PublicShowcaseBundle;
}

export async function loadPublicShowcase(): Promise<PublicShowcaseBundle> {
  const response = await fetch(PUBLIC_SHOWCASE_PATH, { credentials: "omit" });
  if (!response.ok) throw new Error(`The public showcase could not be loaded (${response.status}).`);
  return parsePublicShowcase(await response.json());
}

function visibleAt(entity: Entity, sequence: number): boolean {
  return Number(entity._sequence ?? 1) <= sequence;
}

export function showcaseStateAtSequence(bundle: PublicShowcaseBundle, requestedSequence: number | null): GraphState {
  const latest = bundle.state.last_sequence;
  const sequence = requestedSequence === null ? latest : Math.max(1, Math.min(latest, Math.floor(requestedSequence)));
  const state = { ...bundle.state } as GraphState;
  for (const key of ENTITY_COLLECTIONS) {
    (state as unknown as Record<string, unknown>)[key] = bundle.state[key].filter((entity) => visibleAt(entity, sequence));
  }
  state.last_sequence = sequence;
  state.event_count = ENTITY_COLLECTIONS.reduce((total, key) => total + state[key].length, 0);
  return state;
}

export function showcaseMultiplayerAtState(bundle: PublicShowcaseBundle, state: GraphState): MultiplayerState {
  const visibleNodes = new Set(state.nodes.map((node) => node.id));
  const visibleFindings = new Set(state.findings.map((finding) => finding.id));
  return {
    ...bundle.multiplayer,
    claims: (bundle.multiplayer.claims ?? []).filter((claim) => visibleNodes.has(claim.node_id)),
    publications: (bundle.multiplayer.publications ?? []).filter((publication) => visibleFindings.has(publication.finding_id)),
  };
}

export interface ShowcaseSearchResult {
  id: string;
  entity_type: string;
  title: string;
  context: string;
}

function entityText(entity: Entity): string {
  return [entity.title, entity.name, entity.summary, entity.statement, entity.description, entity.id]
    .filter((value): value is string => typeof value === "string")
    .join(" ");
}

export function searchPublicShowcase(state: GraphState, query: string): ShowcaseSearchResult[] {
  const needle = query.trim().toLocaleLowerCase();
  if (needle.length < 2) return [];
  const collections: Array<[string, Entity[]]> = [
    ["system", state.nodes],
    ["finding", state.findings],
    ["figure", state.artifacts],
    ["agent", state.agents],
    ["dataset", state.datasets],
  ];
  return collections.flatMap(([entity_type, entities]) => entities.flatMap((entity) => {
    if (!entityText(entity).toLocaleLowerCase().includes(needle)) return [];
    return [{
      id: entity.id,
      entity_type,
      title: String(entity.title ?? entity.name ?? entity.id),
      context: String(entity.summary ?? entity.statement ?? entity.description ?? "Public showcase result"),
    }];
  })).slice(0, 30);
}
