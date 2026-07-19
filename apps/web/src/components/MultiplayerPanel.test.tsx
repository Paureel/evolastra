import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  claimMultiplayerSystem,
  fetchMultiplayerReadiness,
  hostMultiplayer,
  joinMultiplayer,
  leaveMultiplayer,
  publishMultiplayerFinding,
  releaseMultiplayerSystem,
  renewMultiplayerInvite,
} from "../api";
import type { MultiplayerState } from "../types";
import { MultiplayerPanel } from "./MultiplayerPanel";

vi.mock("../api", () => ({
  claimMultiplayerSystem: vi.fn(),
  fetchMultiplayerReadiness: vi.fn(),
  hostMultiplayer: vi.fn(),
  joinMultiplayer: vi.fn(),
  leaveMultiplayer: vi.fn(),
  publishMultiplayerFinding: vi.fn(),
  releaseMultiplayerSystem: vi.fn(),
  renewMultiplayerInvite: vi.fn(),
}));

const activeState: MultiplayerState = {
  enabled: true,
  session: {
    id: "session_test",
    run_id: "run_test",
    mode: "host",
    status: "active",
    revision: 3,
    host_url: "https://host.example.ts.net",
    project_fingerprint: "a".repeat(64),
    local_player_id: "player_host",
    title: "Shared analysis",
  },
  players: [{ id: "player_host", display_name: "Aurel", color: "#71E6E1", role: "host", online: true, last_seen_at: "2026-07-18T12:00:00Z" }],
  claims: [],
  publications: [],
};

describe("MultiplayerPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchMultiplayerReadiness).mockResolvedValue({
      tailscale_installed: true,
      tailnet_ready: true,
      suggested_share_url: "https://host.example.ts.net",
      serve_command: "tailscale serve --bg --set-path /api/v1/federation http://127.0.0.1:8000/api/v1/federation",
      stores_project_data: false,
    });
    vi.mocked(hostMultiplayer).mockResolvedValue({ state: activeState, invite_code: "EVO1.invite" });
    vi.mocked(joinMultiplayer).mockResolvedValue(activeState);
    vi.mocked(claimMultiplayerSystem).mockResolvedValue(activeState);
    vi.mocked(releaseMultiplayerSystem).mockResolvedValue(activeState);
    vi.mocked(publishMultiplayerFinding).mockResolvedValue(activeState);
    vi.mocked(renewMultiplayerInvite).mockResolvedValue({ invite_code: "EVO1.rotated" });
    vi.mocked(leaveMultiplayer).mockResolvedValue({ closed: true });
  });

  it("hosts the current local project without uploading it", async () => {
    const changed = vi.fn();
    render(<MultiplayerPanel open runId="run_test" state={{ enabled: false }} selectedSystem={null} findings={[]} onClose={vi.fn()} onChanged={changed} />);

    expect(screen.getByRole("dialog", { name: "Research federation" })).toBeVisible();
    expect(screen.getByText("THIS DEVICE")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Player name"), { target: { value: "Aurel" } });
    await screen.findByDisplayValue("https://host.example.ts.net");
    fireEvent.click(screen.getByRole("button", { name: "Host this project" }));

    await waitFor(() => expect(hostMultiplayer).toHaveBeenCalledWith("run_test", "Aurel", "#71E6E1", "https://host.example.ts.net"));
    expect(changed).toHaveBeenCalledWith(activeState);
  });

  it("claims a selected system and publishes only a finding summary", async () => {
    const changed = vi.fn();
    render(<MultiplayerPanel
      open
      runId="run_test"
      state={activeState}
      selectedSystem={{ id: "node_frontier", title: "Alternative mechanism" }}
      findings={[{ id: "finding_local", title: "Local result" }]}
      onClose={vi.fn()}
      onChanged={changed}
    />);

    expect(screen.getByText("Federation online")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Claim system" }));
    await waitFor(() => expect(claimMultiplayerSystem).toHaveBeenCalledWith("run_test", "node_frontier"));

    fireEvent.change(screen.getByLabelText("Publish a local finding"), { target: { value: "finding_local" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish summary" }));
    await waitFor(() => expect(publishMultiplayerFinding).toHaveBeenCalledWith("run_test", "finding_local"));
    expect(screen.getByText("Only the bounded title and summary cross the tailnet.")).toBeVisible();
    expect(changed).toHaveBeenCalled();
  });

  it("presents a public federation showcase without mutation controls or readiness calls", () => {
    render(<MultiplayerPanel
      open
      readOnly
      runId="demo_run_stad_three_empires"
      state={{ ...activeState, session: { ...activeState.session!, simulation_active: true } }}
      selectedSystem={{ id: "demo_node_myc", title: "MYC amplification → ATR dependence" }}
      findings={[]}
      onClose={vi.fn()}
      onChanged={vi.fn()}
    />);

    const dialog = screen.getAllByRole("dialog").at(-1)!;
    expect(within(dialog).getByRole("heading", { name: "Three-empire expedition" })).toBeVisible();
    expect(within(dialog).getByText("CURATED PUBLIC RESULTS")).toBeVisible();
    expect(within(dialog).queryByRole("button", { name: "Claim system" })).not.toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Close federation" })).not.toBeInTheDocument();
    expect(fetchMultiplayerReadiness).not.toHaveBeenCalled();
  });
});
