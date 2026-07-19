import { describe, expect, it } from "vitest";
import { sceneFromState, userVisibleRuns } from "./App";
import type { GraphState, RunSummary } from "./types";

describe("scene projection", () => {
  it("places projected tool calls under their Codex turn", () => {
    const state = {
      schema_version: 1,
      run: { id: "run_live", title: "Codex live" },
      nodes: [{ id: "node_turn", title: "Codex turn", parent_node_id: null }],
      tool_calls: [{ id: "tool_shell", tool_name: "Shell", status: "completed", node_id: "node_turn" }],
      agents: [], datasets: [], dataset_versions: [], transformations: [], artifacts: [], claims: [], evidence: [], findings: [], decisions: [], anomalies: [], approvals: [], annotations: [], metrics: [], edges: [], unknown_events: [], last_sequence: 2, event_count: 2,
    } as GraphState;

    const scene = sceneFromState(state);

    expect(scene.entities).toContainEqual(expect.objectContaining({
      id: "tool_shell",
      kind: "tool",
      parentId: "node_turn",
      status: "completed",
    }));
  });

  it("hides seeded development demos from production run selection", () => {
    const summary = (id: string, tags: string[]): RunSummary => ({
      id, tags, title: id, objective: id, status: "completed", seed: 1,
      privacy_class: "internal", last_sequence: 1, created_at: "2026-07-19T00:00:00Z",
      updated_at: "2026-07-19T00:00:00Z", counts: {},
    });
    const real = summary("real-analysis", []);
    const seeded = summary("churn-fixture", ["seeded-demo", "churn"]);

    expect(userVisibleRuns([seeded, real])).toEqual([real]);
    expect(userVisibleRuns([seeded, real], true)).toEqual([seeded, real]);
  });
});
