import { describe, expect, it } from "vitest";
import { buildMapBrief } from "./mapBrief";
import type { GraphState, SceneEntity } from "./types";

const scene: SceneEntity[] = [
  { id: "node_home", title: "Research Nexus", kind: "home", status: "running", progress: 0.75 },
  { id: "node_signal", title: "Signal Analysis", kind: "node", status: "running", parentId: "node_home", progress: 0.4 },
  { id: "agent_kepler", title: "Kepler", kind: "agent", status: "running", parentId: "node_signal" },
  { id: "art_chart", title: "Signal chart", kind: "artifact", status: "created", parentId: "node_signal" },
  { id: "tool_shell", title: "Shell", kind: "tool", status: "completed", parentId: "node_signal" },
];

const state: GraphState = {
  schema_version: 1,
  run: { id: "run_demo", run_seed: 42, title: "Demo" },
  nodes: [
    { id: "node_home", title: "Research Nexus", status: "running", progress: 0.75, parent_node_id: null },
    { id: "node_signal", title: "Signal Analysis", status: "running", progress: 0.4, parent_node_id: "node_home", description: "compare the strongest candidate signals" },
  ],
  agents: [{ id: "agent_kepler", name: "Kepler", status: "running", current_node_id: "node_signal", role: "signal specialist", framework: "local", capabilities: "analysis validation" }],
  artifacts: [{ id: "art_chart", title: "Signal chart", status: "created", node_id: "node_signal", description: "A compact evidence chart.", artifact_type: "vega_lite", preview_status: "ready", provenance: { agent_id: "agent_kepler" } }],
  tool_calls: [{ id: "tool_shell", tool_name: "Shell", status: "completed", node_id: "node_signal" }], datasets: [], dataset_versions: [], transformations: [], claims: [], evidence: [], findings: [], decisions: [], anomalies: [], approvals: [], annotations: [], metrics: [], edges: [], unknown_events: [], last_sequence: 1, event_count: 1,
};

describe("map object brief", () => {
  it("states what an agent is doing and names its exact star system", () => {
    const brief = buildMapBrief(state, scene, "agent_kepler", 42)!;
    expect(brief.kindLabel).toBe("Agent vessel");
    expect(brief.assignmentValue).toBe("Signal Analysis");
    expect(brief.summary).toContain("Compare the strongest candidate signals");
    expect(brief.facts).toContainEqual({ label: "Role", value: "signal specialist" });
  });

  it("summarizes a planet-like artifact without exposing dense provenance", () => {
    const brief = buildMapBrief(state, scene, "art_chart", 42)!;
    expect(brief.kindLabel).toBe("Evidence planet");
    expect(brief.assignmentValue).toBe("Signal Analysis");
    expect(brief.facts).toContainEqual({ label: "Produced by", value: "Kepler" });
    expect(brief.facts).toHaveLength(3);
  });

  it("counts and describes redacted tool activity in a system", () => {
    const system = buildMapBrief(state, scene, "node_signal", 42)!;
    const tool = buildMapBrief(state, scene, "tool_shell", 42)!;
    expect(system.facts).toContainEqual({ label: "Tracked objects", value: "2" });
    expect(tool.kindLabel).toBe("Tool operation");
    expect(tool.facts).toContainEqual({ label: "Content", value: "Redacted by default" });
  });
});
