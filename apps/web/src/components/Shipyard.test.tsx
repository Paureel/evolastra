import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { buildShip, dispatchShip, fetchShipyard } from "../api";
import type { Entity, ShipyardState } from "../types";
import { Shipyard } from "./Shipyard";

vi.mock("../api", () => ({
  buildShip: vi.fn(),
  dispatchShip: vi.fn(),
  fetchShipyard: vi.fn(),
}));

const frigate = {
  id: "frigate",
  name: "Frigate",
  hull: "frigate" as const,
  role: "Focused Codex agent",
  description: "A fast generalist.",
  capabilities: ["focused execution"],
};

const baseYard: ShipyardState = {
  blueprints: [
    frigate,
    { ...frigate, id: "mothership", name: "Mothership", hull: "mothership" },
    { ...frigate, id: "colony", name: "Colony ship", hull: "colony" },
  ],
  ships: [],
  dispatch_enabled: true,
  codex_available: true,
  safety: {
    transport: "local-stdio",
    sandbox: "workspace-write",
    approval_policy: "never",
    workspace_fixed: true,
    network_access: false,
    web_search: "disabled",
    environment_filtered: true,
    context_isolated: true,
  },
};

const builtShip: Entity = {
  id: "agent_ship",
  name: "Frigate 01",
  status: "created",
  ship_blueprint_id: "frigate",
};

describe("Shipyard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchShipyard).mockResolvedValue(baseYard);
    vi.mocked(buildShip).mockResolvedValue({ ship: builtShip });
    vi.mocked(dispatchShip).mockResolvedValue({
      accepted: true,
      ship_id: builtShip.id,
      thread_id: "thr_launched",
      turn_id: "turn_launched",
      status: "running",
    });
  });

  it("builds a core hull and launches its mission through Codex", async () => {
    vi.mocked(fetchShipyard)
      .mockResolvedValueOnce(baseYard)
      .mockResolvedValue({ ...baseYard, ships: [builtShip] });
    const changed = vi.fn();
    render(<Shipyard open runId="run_test" preferredBlueprintId="frigate" onClose={vi.fn()} onChanged={changed} />);

    expect(await screen.findByRole("dialog", { name: "Build a Codex vessel" })).toBeVisible();
    expect(screen.getByRole("button", { name: /Mothership/ })).toBeVisible();
    expect(screen.getByRole("button", { name: /Colony ship/ })).toBeVisible();
    expect(screen.getByText("Network off")).toBeVisible();
    expect(screen.getByText(/trusted safety rules separately/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Build Frigate" }));
    await waitFor(() => expect(buildShip).toHaveBeenCalledWith("run_test", "frigate"));
    await screen.findByRole("option", { name: /Frigate 01/ });

    fireEvent.change(screen.getByLabelText("Mission order"), { target: { value: "Inspect the active hypothesis" } });
    fireEvent.click(screen.getByRole("button", { name: /Launch mission/ }));

    await waitFor(() => expect(dispatchShip).toHaveBeenCalledWith("run_test", builtShip.id, "Inspect the active hypothesis"));
    expect(await screen.findByText("Mission launched")).toBeVisible();
    expect(screen.getByText("Codex task thr_launched")).toBeVisible();
    expect(changed).toHaveBeenCalled();
  });
});
