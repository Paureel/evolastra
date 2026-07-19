import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { currentEndpoint, pairCompanion } from "../api";
import { AGENT_SETUP_PROMPT, ConnectionPanel, HUMAN_INSTALL_COMMAND } from "./ConnectionPanel";

vi.mock("../api", () => ({
  currentEndpoint: vi.fn(() => "http://127.0.0.1:8000"),
  pairCompanion: vi.fn(),
}));

describe("ConnectionPanel", () => {
  const writeText = vi.fn().mockResolvedValue(undefined);

  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  afterEach(() => cleanup());

  it("offers the public showcase without entering a pairing code", async () => {
    const explore = vi.fn().mockResolvedValue(undefined);
    render(<ConnectionPanel open required onClose={vi.fn()} onConnected={vi.fn()} onExploreDemo={explore} />);

    expect(screen.getByText(/STAD: Stomach Adenocarcinoma/i)).toBeInTheDocument();
    expect(screen.getByText(/Copy Number Alteration \(CNA\) analysis/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Explore public demo" }));

    await waitFor(() => expect(explore).toHaveBeenCalledOnce());
    expect(pairCompanion).not.toHaveBeenCalled();
    expect(currentEndpoint).toHaveBeenCalled();
  });

  it("gives humans and Codex agents complete first-time connection instructions", async () => {
    render(<ConnectionPanel open required onClose={vi.fn()} onConnected={vi.fn()} onExploreDemo={vi.fn()} />);

    expect(screen.getByText(/first-time setup installs a small local companion and Codex hooks/i)).toBeVisible();
    const humanPanel = screen.getByRole("tabpanel", { name: "For humans" });
    expect(humanPanel).toHaveTextContent("Windows 10+");
    expect(humanPanel).toHaveTextContent("git clone https://github.com/Paureel/evolastra.git");
    expect(humanPanel).toHaveTextContent("-Origin https://evolastra.netlify.app");
    expect(screen.getByText(/Seeing .*Failed to fetch/i)).toBeVisible();
    expect(screen.getByRole("link", { name: /Open the clean-profile fix/i })).toHaveAttribute(
      "href",
      "https://github.com/Paureel/evolastra/blob/main/docs/getting-started.md#hosted-viewer-says-failed-to-fetch",
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy install commands" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(HUMAN_INSTALL_COMMAND));

    fireEvent.click(screen.getByRole("tab", { name: "For Codex agents" }));
    expect(screen.getByRole("tabpanel", { name: "For Codex agents" })).toHaveTextContent("pauses for your hook approval");
    expect(screen.getByRole("link", { name: "Agent setup file ↗" })).toHaveAttribute("href", "/agent-setup.md");
    expect(screen.getByRole("link", { name: "llms.txt ↗" })).toHaveAttribute("href", "/llms.txt");
    fireEvent.click(screen.getByRole("button", { name: "Copy agent setup prompt" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(AGENT_SETUP_PROMPT));
  });

  it("contacts the companion only after an explicit connect action", async () => {
    vi.mocked(pairCompanion).mockResolvedValueOnce({ profile: "local-private", local_data: true });
    const connected = vi.fn();
    render(<ConnectionPanel open required onClose={vi.fn()} onConnected={connected} onExploreDemo={vi.fn()} />);

    expect(pairCompanion).not.toHaveBeenCalled();
    fireEvent.change(screen.getByPlaceholderText("A1B2-C3D4-E5F6"), {
      target: { value: "A1B2-C3D4-E5F6" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Connect observatory" }));

    await waitFor(() => expect(pairCompanion).toHaveBeenCalledWith("http://127.0.0.1:8000", "A1B2-C3D4-E5F6"));
    expect(connected).toHaveBeenCalledOnce();
  });
});
