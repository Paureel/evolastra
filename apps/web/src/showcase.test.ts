import { describe, expect, it } from "vitest";
import stadShowcaseJson from "../public/demo/stad-three-empires-v1.json";
import { sceneFromState } from "./App";
import { createFrontierField, occupyFrontierSystems } from "./galaxyFrontier";
import { layoutScene, stabilizeGalaxyLayout } from "./layout";
import { parsePublicShowcase, PUBLIC_SHOWCASE_PATH, searchPublicShowcase, showcaseMultiplayerAtState, showcasePhaseLabel, showcaseStateAtSequence, type PublicShowcaseBundle } from "./showcase";

const bundle = {
  schema_version: 1,
  id: "stad-three-empires-v1",
  public: true,
  title: "Showcase",
  notice: "Aggregate-only demo",
  run: { id: "demo_run_stad_three_empires", title: "Showcase", objective: "Demo", status: "completed", seed: 7, privacy_class: "public", last_sequence: 3, created_at: "2026-07-19T00:00:00Z", updated_at: "2026-07-19T00:00:00Z", counts: {} },
  state: {
    schema_version: 1,
    run: { id: "demo_run_stad_three_empires", title: "Showcase" },
    nodes: [{ id: "demo_node_capital", title: "Capital", parent_node_id: null, _sequence: 1 }, { id: "demo_node_myc", title: "MYC–ATR", parent_node_id: "demo_node_capital", summary: "Amplification dependency", _sequence: 2 }],
    findings: [{ id: "demo_finding_myc", title: "MYC gain", node_id: "demo_node_myc", _sequence: 2 }],
    artifacts: [], agents: [], tool_calls: [], datasets: [], dataset_versions: [], transformations: [], claims: [], evidence: [], decisions: [], anomalies: [], approvals: [], annotations: [], metrics: [],
    edges: [{ id: "demo_edge_myc", source_id: "demo_node_capital", target_id: "demo_node_myc", _sequence: 2 }],
    unknown_events: [], last_sequence: 3, event_count: 5,
  },
  multiplayer: {
    enabled: true,
    players: [{ id: "demo_player_gold", display_name: "Gold", color: "#FFD36A", role: "host", online: true, last_seen_at: "2026-07-19T00:00:00Z" }],
    claims: [{ id: "demo_claim_myc", node_id: "demo_node_myc", player_id: "demo_player_gold", claimed_at: "2026-07-19T00:00:00Z" }],
    publications: [{ id: "demo_publication_myc", finding_id: "demo_finding_myc", player_id: "demo_player_gold", title: "MYC", summary: "Aggregate result", published_at: "2026-07-19T00:00:00Z" }],
  },
  replay: {
    last_sequence: 3,
    phases: [
      { sequence: 1, label: "Research nexus", node_ids: ["demo_node_capital"] },
      { sequence: 2, label: "MYC direction", node_ids: ["demo_node_myc"] },
      { sequence: 3, label: "Synthesis", node_ids: [] },
    ],
  },
} as PublicShowcaseBundle;

describe("public showcase", () => {
  it("loads only the one fixed same-origin asset", () => {
    expect(PUBLIC_SHOWCASE_PATH).toBe("/demo/stad-three-empires-v1.json");
    expect(parsePublicShowcase(bundle)).toBe(bundle);
    expect(showcasePhaseLabel(bundle, 2)).toBe("MYC direction");
    expect(() => parsePublicShowcase({ ...bundle, id: "another-demo" })).toThrow(/not recognized/);
    expect(() => parsePublicShowcase({ ...bundle, replay: { last_sequence: 3, phases: [] } })).toThrow(/replay is incomplete/);
  });

  it("replays entities and federation claims by their public phase", () => {
    const first = showcaseStateAtSequence(bundle, 1);
    const second = showcaseStateAtSequence(bundle, 2);
    expect(first.nodes.map((node) => node.id)).toEqual(["demo_node_capital"]);
    expect(second.nodes).toHaveLength(2);
    expect(showcaseMultiplayerAtState(bundle, first).claims).toEqual([]);
    expect(showcaseMultiplayerAtState(bundle, second).claims).toHaveLength(1);
    expect(showcaseMultiplayerAtState(bundle, showcaseStateAtSequence(bundle, 3)).claims)
      .toEqual(showcaseMultiplayerAtState(bundle, second).claims);
  });

  it("keeps the actual three-empire STAD systems and prior owners fixed through every phase", () => {
    const stadBundle = parsePublicShowcase(stadShowcaseJson as unknown as PublicShowcaseBundle);
    const seed = stadBundle.run.seed;
    const frontier = createFrontierField(seed);
    const finalScene = sceneFromState(showcaseStateAtSequence(stadBundle, null)).entities;
    const registry = new Map();
    const initial = stabilizeGalaxyLayout(occupyFrontierSystems(frontier, layoutScene(finalScene, seed, "galaxy")).layout, registry);
    const initialSystems = new Map(
      initial.filter((entity) => entity.kind === "home" || entity.kind === "node").map((entity) => [entity.id, entity]),
    );
    const seenOwners = new Map<string, string>();

    for (let sequence = 1; sequence <= stadBundle.replay.last_sequence; sequence += 1) {
      const state = showcaseStateAtSequence(stadBundle, sequence);
      const scene = sceneFromState(state).entities;
      const positioned = stabilizeGalaxyLayout(occupyFrontierSystems(frontier, layoutScene(scene, seed, "galaxy")).layout, registry);
      for (const system of positioned.filter((entity) => entity.kind === "home" || entity.kind === "node")) {
        const expected = initialSystems.get(system.id);
        expect(system).toMatchObject({ x: expected?.x, y: expected?.y, z: expected?.z });
      }
      for (const claim of showcaseMultiplayerAtState(stadBundle, state).claims ?? []) {
        expect(claim.player_id).toBe(seenOwners.get(claim.node_id) ?? claim.player_id);
        seenOwners.set(claim.node_id, claim.player_id);
      }
    }

    expect(seenOwners.size).toBe(10);
  });

  it("searches the visible projection without a companion request", () => {
    expect(searchPublicShowcase(showcaseStateAtSequence(bundle, 2), "myc")).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: "demo_node_myc", entity_type: "system" }),
      expect.objectContaining({ id: "demo_finding_myc", entity_type: "finding" }),
    ]));
  });
});
