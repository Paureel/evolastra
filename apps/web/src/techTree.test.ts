import { describe, expect, it } from "vitest";
import { buildTechTiers } from "./techTree";
import type { NodeEntity } from "./types";

const node = (id: string, node_type: string, status: string, progress: number): NodeEntity => ({ id, title: id, node_type, status, progress });

describe("research tech tree", () => {
  it("groups technologies into meaningful progression tiers", () => {
    const tiers = buildTechTiers([
      node("ingress", "data", "completed", 1),
      node("signal", "exploration", "completed", 1),
      node("model", "modeling", "running", 0.5),
    ]);
    expect(tiers.map((tier) => tier.label)).toEqual(["Data foundation", "Signal research", "Modeling"]);
  });

  it("locks research whose prerequisite tier is unfinished", () => {
    const tiers = buildTechTiers([
      node("ingress", "data", "running", 0.4),
      node("signal", "exploration", "unexplored", 0),
    ]);
    expect(tiers[0].nodes[0].techState).toBe("researching");
    expect(tiers[1].nodes[0].techState).toBe("locked");
  });

  it("makes frontier research available when prior research is complete", () => {
    const tiers = buildTechTiers([
      node("synthesis", "synthesis", "completed", 1),
      node("frontier", "unexplored", "unexplored", 0),
    ]);
    expect(tiers.at(-1)?.nodes[0].techState).toBe("available");
  });
});
