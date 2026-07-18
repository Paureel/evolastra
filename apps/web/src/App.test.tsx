import { describe, expect, it } from "vitest";
import { sceneFromState } from "./App";
import type { GraphState } from "./types";

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
});
