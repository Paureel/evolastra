import { describe, expect, it } from "vitest";
import { layoutScene, stabilizeGalaxyLayout, stableHash } from "./layout";
import { createFrontierField, DEFAULT_UNCLAIMED_SYSTEMS, frontierClaimedBridges, frontierSystemCount, galaxyCameraZoom, stellarProfile, stellarProfilesFor } from "./galaxyFrontier";
import { connectedHyperlanes } from "./mapGraph";
import { semanticLayoutMetrics } from "./semanticLayout";
import { angleDegrees, normalizeAngle, projectLayout3D, projectPoint3D } from "./spatial";
import { STAD_SEMANTIC_FIXTURE } from "./stadSemanticFixture";
import type { SceneEntity } from "./types";

const fixture: SceneEntity[] = [
  { id: "node_home0000", title: "Home", kind: "home", status: "running" },
  { id: "node_branch001", title: "Branch", kind: "node", status: "running", parentId: "node_home0000" },
  { id: "art_artifact01", title: "Chart", kind: "artifact", status: "completed", parentId: "node_branch001" },
];

describe("deterministic layout", () => {
  it("produces equivalent coordinates for the same seed", () => {
    expect(layoutScene(fixture, 42)).toEqual(layoutScene(fixture, 42));
  });

  it("assigns stable depth and projects both maps through a rotatable camera", () => {
    const spatial = layoutScene(fixture, 42);
    expect(spatial.every((entity) => Number.isFinite(entity.z))).toBe(true);
    const front = projectLayout3D(spatial, { yaw: 0, pitch: 0.45, focalLength: 1_400 });
    const rotated = projectLayout3D(spatial, { yaw: 0.7, pitch: 0.8, focalLength: 1_400 });
    expect(rotated.find((entity) => entity.id === "node_branch001")?.x).not.toBe(front.find((entity) => entity.id === "node_branch001")?.x);
    const near = projectPoint3D({ x: 100, y: -120, z: 0 }, { yaw: 0, pitch: 0.5, focalLength: 900 });
    const far = projectPoint3D({ x: 100, y: 120, z: 0 }, { yaw: 0, pitch: 0.5, focalLength: 900 });
    expect(near.scale).toBeGreaterThan(far.scale);
  });

  it("supports complete camera rotations without a pitch horizon clamp", () => {
    const point = { x: 85, y: 140, z: 32 };
    const camera = { yaw: 0.32, pitch: 0.58, focalLength: 1_400 };
    const front = projectPoint3D(point, camera);
    const upsideDown = projectPoint3D(point, { ...camera, pitch: camera.pitch + Math.PI });
    const fullTurn = projectPoint3D(point, { ...camera, pitch: camera.pitch + Math.PI * 2 });
    expect(upsideDown.y).not.toBeCloseTo(front.y);
    expect(fullTurn.x).toBeCloseTo(front.x);
    expect(fullTurn.y).toBeCloseTo(front.y);
    expect(normalizeAngle(Math.PI * 2 + 0.4)).toBeCloseTo(0.4);
    expect(angleDegrees(-Math.PI / 2)).toBe(270);
  });

  it("keeps existing entity coordinates stable when a satellite is added", () => {
    const before = layoutScene(fixture, 42).find((entity) => entity.id === "node_branch001");
    const after = layoutScene([...fixture, { id: "art_artifact02", title: "Table", kind: "artifact", status: "completed", parentId: "node_branch001" }], 42).find((entity) => entity.id === "node_branch001");
    expect(after).toMatchObject({ x: before?.x, y: before?.y });
  });

  it("hashes stably", () => expect(stableHash("evidence", 9)).toBe(stableHash("evidence", 9)));

  it("places claimed research directions by semantic rather than arbitrary distance", () => {
    const semanticEntities: SceneEntity[] = [
      { id: "node_semantic_home", title: "STAD", kind: "home", status: "running" },
      ...STAD_SEMANTIC_FIXTURE.map((system, index) => ({
        id: system.id,
        title: `Hypothesis ${index + 1}`,
        kind: "node" as const,
        status: "running",
        parentId: "node_semantic_home",
        semanticSignature: system.semanticSignature,
      })),
    ];
    const positioned = layoutScene(semanticEntities, 874049);
    const points = new Map(positioned.filter((entity) => entity.semanticSignature).map((entity) => [entity.id, entity]));
    const metrics = semanticLayoutMetrics(STAD_SEMANTIC_FIXTURE, points);
    expect(metrics.spearman).toBeGreaterThanOrEqual(0.8);
    expect(metrics.meanWithinProgram).toBeLessThan(metrics.meanBetweenPrograms);
    expect(metrics.sameProgramNearestNeighbors).toBe(6);
  });

  it("does not move occupied semantic systems when later systems appear", () => {
    const semanticEntities: SceneEntity[] = [
      { id: "node_stable_home", title: "STAD", kind: "home", status: "completed" },
      ...STAD_SEMANTIC_FIXTURE.map((system, index) => ({
        id: system.id,
        title: `Hypothesis ${index + 1}`,
        kind: "node" as const,
        status: "completed",
        parentId: "node_stable_home",
        semanticSignature: system.semanticSignature,
      })),
    ];
    const registry = new Map();
    const earlier = stabilizeGalaxyLayout(
      layoutScene(semanticEntities.slice(0, 3), 874049, "galaxy"),
      registry,
    );
    const later = stabilizeGalaxyLayout(
      layoutScene(semanticEntities, 874049, "galaxy"),
      registry,
    );

    for (const occupied of earlier) {
      expect(later.find((entity) => entity.id === occupied.id)).toMatchObject({
        x: occupied.x,
        y: occupied.y,
        z: occupied.z,
      });
    }

    const laterPoints = new Map(later.filter((entity) => entity.semanticSignature).map((entity) => [entity.id, entity]));
    const metrics = semanticLayoutMetrics(STAD_SEMANTIC_FIXTURE, laterPoints);
    expect(metrics.spearman).toBeGreaterThanOrEqual(0.7);
    expect(metrics.meanWithinProgram).toBeLessThan(metrics.meanBetweenPrograms);
  });

  it("restores exact system locations through showcase rewind and replay", () => {
    const semanticEntities: SceneEntity[] = [
      { id: "node_replay_home", title: "STAD", kind: "home", status: "completed" },
      ...STAD_SEMANTIC_FIXTURE.map((system, index) => ({
        id: system.id,
        title: `Hypothesis ${index + 1}`,
        kind: "node" as const,
        status: "completed",
        parentId: "node_replay_home",
        semanticSignature: system.semanticSignature,
      })),
    ];
    const registry = new Map();
    const initial = stabilizeGalaxyLayout(layoutScene(semanticEntities, 874049, "galaxy"), registry);
    stabilizeGalaxyLayout(layoutScene(semanticEntities.slice(0, 4), 874049, "galaxy"), registry);
    const replayed = stabilizeGalaxyLayout(layoutScene(semanticEntities, 874049, "galaxy"), registry);

    for (const occupied of initial) {
      expect(replayed.find((entity) => entity.id === occupied.id)).toMatchObject({
        x: occupied.x,
        y: occupied.y,
        z: occupied.z,
      });
    }
    const replayedPoints = new Map(replayed.filter((entity) => entity.semanticSignature).map((entity) => [entity.id, entity]));
    expect(semanticLayoutMetrics(STAD_SEMANTIC_FIXTURE, replayedPoints).spearman).toBeGreaterThanOrEqual(0.8);
  });

  it("keeps nested semantic research branches visible on the galaxy map", () => {
    const nested: SceneEntity[] = [
      { id: "node_nested_home", title: "STAD", kind: "home", status: "completed" },
      { id: "node_nested_atlas", title: "Amplified atlas", kind: "node", status: "completed", parentId: "node_nested_home" },
      {
        id: "node_nested_hypothesis",
        title: "MYC to ATR",
        kind: "node",
        status: "completed",
        parentId: "node_nested_atlas",
        semanticSignature: STAD_SEMANTIC_FIXTURE[0].semanticSignature,
      },
    ];

    const positioned = layoutScene(nested, 7319, "galaxy");

    expect(positioned.map((entity) => entity.id)).toEqual(expect.arrayContaining([
      "node_nested_home",
      "node_nested_atlas",
      "node_nested_hypothesis",
    ]));
  });

  it("opens a selected branch as a distinct orbital system", () => {
    const system = layoutScene(fixture, 42, "system", "node_branch001");
    expect(system.find((entity) => entity.id === "node_branch001")).toMatchObject({ x: 0, y: 0, radius: 31 });
    expect(system.find((entity) => entity.id === "art_artifact01")).toBeDefined();
    expect(system.find((entity) => entity.id === "node_home0000")).toBeUndefined();
  });

  it("stations galaxy agents beside their exact assigned system", () => {
    const withAgent: SceneEntity[] = [
      ...fixture,
      { id: "agent_kepler", title: "Kepler", kind: "agent", status: "running", parentId: "node_branch001" },
    ];
    const galaxy = layoutScene(withAgent, 42, "galaxy");
    const system = galaxy.find((entity) => entity.id === "node_branch001")!;
    const agent = galaxy.find((entity) => entity.id === "agent_kepler")!;
    expect(agent.parentId).toBe(system.id);
    expect(Math.hypot(agent.x - system.x, agent.y - system.y)).toBeLessThan(70);
    expect(Math.hypot(agent.x - system.x, agent.y - system.y)).toBeGreaterThan(35);
  });

  it("creates a stable 200-system unclaimed frontier", () => {
    const frontier = createFrontierField(42);
    expect(frontier.systems).toHaveLength(DEFAULT_UNCLAIMED_SYSTEMS);
    expect(frontier.lanes.length).toBeGreaterThan(DEFAULT_UNCLAIMED_SYSTEMS);
    expect(frontier).toEqual(createFrontierField(42));
    const radii = frontier.systems.map((system) => Math.hypot(system.x, system.y / 0.62));
    expect(Math.min(...radii)).toBeGreaterThan(200);
    expect(Math.min(...radii)).toBeLessThan(300);
    expect(radii.filter((radius) => radius < 620).length).toBeGreaterThanOrEqual(12);
    expect(Math.max(...radii)).toBeGreaterThan(1_050);
  });

  it("keeps every frontier system in one connected component", () => {
    const frontier = createFrontierField(42);
    const adjacency = Array.from({ length: frontier.systems.length }, () => new Set<number>());
    frontier.lanes.forEach(({ source, target }) => {
      adjacency[source].add(target);
      adjacency[target].add(source);
    });
    const visited = new Set([0]);
    const queue = [0];
    while (queue.length) {
      const source = queue.shift()!;
      adjacency[source].forEach((target) => {
        if (visited.has(target)) return;
        visited.add(target);
        queue.push(target);
      });
    }
    expect(visited.size).toBe(frontier.systems.length);
  });

  it("bridges the fully connected frontier to a fully connected claimed network", () => {
    const claimed = layoutScene([
      ...fixture,
      { id: "node_branch002", title: "Second branch", kind: "node", status: "running", parentId: "node_home0000" },
      { id: "node_branch003", title: "Third branch", kind: "node", status: "pending", parentId: "node_home0000" },
    ], 42, "galaxy").filter((entity) => entity.kind === "home" || entity.kind === "node");
    const claimedLanes = connectedHyperlanes(claimed, []);
    const frontier = createFrontierField(42);
    const bridges = frontierClaimedBridges(frontier, claimed);
    expect(claimedLanes.filter((lane) => lane.synthetic)).toHaveLength(claimed.length - 1);
    expect(bridges).toHaveLength(claimed.length);

    const adjacency = new Map<string, Set<string>>();
    const connect = (left: string, right: string) => {
      if (!adjacency.has(left)) adjacency.set(left, new Set());
      if (!adjacency.has(right)) adjacency.set(right, new Set());
      adjacency.get(left)!.add(right);
      adjacency.get(right)!.add(left);
    };
    claimed.forEach((system) => adjacency.set(`c:${system.id}`, new Set()));
    frontier.systems.forEach((_, index) => adjacency.set(`f:${index}`, new Set()));
    claimedLanes.forEach((lane) => connect(`c:${lane.sourceId}`, `c:${lane.targetId}`));
    frontier.lanes.forEach((lane) => connect(`f:${lane.source}`, `f:${lane.target}`));
    bridges.forEach((bridge) => connect(`c:${bridge.claimedId}`, `f:${bridge.frontier}`));

    const start = `c:${claimed[0].id}`;
    const visited = new Set([start]);
    const queue = [start];
    while (queue.length) {
      const source = queue.shift()!;
      adjacency.get(source)?.forEach((target) => {
        if (visited.has(target)) return;
        visited.add(target);
        queue.push(target);
      });
    }
    expect(visited.size).toBe(adjacency.size);
  });

  it("adds 100 frontier systems whenever claimed capacity fills", () => {
    expect(frontierSystemCount(0)).toBe(200);
    expect(frontierSystemCount(199)).toBe(200);
    expect(frontierSystemCount(200)).toBe(300);
    expect(frontierSystemCount(299)).toBe(300);
    expect(frontierSystemCount(300)).toBe(400);
    expect(createFrontierField(42, frontierSystemCount(300)).systems).toHaveLength(400);
  });

  it("widens the camera as the frontier expands", () => {
    expect(galaxyCameraZoom(300)).toBeLessThan(galaxyCameraZoom(200));
    expect(galaxyCameraZoom(400)).toBeLessThan(galaxyCameraZoom(300));
  });

  it("supports varied persistent stellar classes including pulsars and black holes", () => {
    const profiles = Array.from({ length: 8 }, (_, index) => stellarProfile(`system-${index}`, 42, index));
    expect(new Set(profiles.map((profile) => profile.body)).size).toBeGreaterThan(2);
    expect(profiles[3].kind).toBe("pulsar");
    expect(profiles[6].kind).toBe("black-hole");
    expect(profiles.some((profile) => profile.kind === "black-hole")).toBe(true);
    const registry = stellarProfilesFor(Array.from({ length: 8 }, (_, index) => `system-${index}`), 42);
    expect(registry.get("system-3")).toEqual(profiles[3]);
    expect(registry.get("system-6")).toEqual(profiles[6]);
  });

});
