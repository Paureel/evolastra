import { describe, expect, it } from "vitest";
import { DEFAULT_ORIENTATION, projectGalaxyPlaneLayout, projectPoint3D } from "./spatial";
import {
  buildTerritoryRegions,
  projectTerritoryPoint,
  territorySystemsForLayout,
  territoryTransitionLayers,
  type PlanarTerritorySystem,
} from "./territoryProjection";

const systems: PlanarTerritorySystem[] = [
  { id: "gold-a", owner: "#FFD36A", x: -180, y: -20 },
  { id: "gold-b", owner: "#FFD36A", x: 20, y: 20 },
  { id: "cyan-a", owner: "#71E6E1", x: 210, y: -10 },
];

describe("planar territory projection", () => {
  it("includes the command capital and claimed systems but no orbital objects", () => {
    const layout = [
      { id: "capital", title: "Capital", kind: "home", status: "running", x: 0, y: 0, z: 50, radius: 8, angle: 0 },
      { id: "system", title: "System", kind: "node", status: "running", x: 80, y: 0, z: -50, radius: 8, angle: 0 },
      { id: "agent", title: "Agent", kind: "agent", status: "running", x: 10, y: 10, z: 10, radius: 4, angle: 0 },
    ] as const;
    expect(territorySystemsForLayout([...layout], { capital: "#FFD36A", system: "#71E6E1" }, "#B98BEA"))
      .toEqual([
        { id: "capital", owner: "#FFD36A", x: 0, y: 0 },
        { id: "system", owner: "#71E6E1", x: 80, y: 0 },
      ]);
  });

  it("creates one connected enclosing region for linked systems", () => {
    const regions = buildTerritoryRegions(systems);
    const gold = regions.find((region) => region.owner === "#FFD36A");
    expect(gold?.systemIds).toEqual(["gold-a", "gold-b"]);
    expect(gold?.loops).toHaveLength(1);

    for (const system of systems.slice(0, 2)) {
      const points = gold!.loops[0];
      expect(Math.min(...points.map((point) => point.x))).toBeLessThan(system.x);
      expect(Math.max(...points.map((point) => point.x))).toBeGreaterThan(system.x);
      expect(Math.min(...points.map((point) => point.y))).toBeLessThan(system.y);
      expect(Math.max(...points.map((point) => point.y))).toBeGreaterThan(system.y);
    }
  });

  it("projects every border point from the galaxy plane regardless of star height", () => {
    const point = { x: 140, y: -75 };
    const projected = projectTerritoryPoint(point, DEFAULT_ORIENTATION.galaxy);
    expect(projected).toEqual(projectPoint3D({ ...point, z: 0 }, DEFAULT_ORIENTATION.galaxy));
    expect(projected).not.toEqual(projectPoint3D({ ...point, z: 400 }, DEFAULT_ORIENTATION.galaxy));
    const projectedSystem = projectGalaxyPlaneLayout([{
      id: "elevated", title: "Elevated", kind: "node", status: "running",
      x: point.x, y: point.y, z: 400, radius: 8, angle: 0,
    }], DEFAULT_ORIENTATION.galaxy)[0];
    expect({ x: projectedSystem.x, y: projectedSystem.y }).toEqual({ x: projected.x, y: projected.y });
  });

  it("crossfades stable planar snapshots as territory evolves", () => {
    const previous = buildTerritoryRegions(systems.slice(0, 1));
    const current = buildTerritoryRegions(systems.slice(0, 2));
    expect(territoryTransitionLayers(previous, current, 0)).toEqual([{ regions: previous, opacity: 1 }]);
    expect(territoryTransitionLayers(previous, current, 0.5)).toEqual([
      { regions: previous, opacity: 0.5 },
      { regions: current, opacity: 0.5 },
    ]);
    expect(territoryTransitionLayers(previous, current, 1)).toEqual([{ regions: current, opacity: 1 }]);
  });
});
