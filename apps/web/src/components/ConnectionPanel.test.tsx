import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { currentEndpoint, pairCompanion } from "../api";
import { ConnectionPanel } from "./ConnectionPanel";

vi.mock("../api", () => ({
  currentEndpoint: vi.fn(() => "http://127.0.0.1:8000"),
  pairCompanion: vi.fn(),
}));

describe("ConnectionPanel", () => {
  it("offers the public showcase without entering a pairing code", async () => {
    const explore = vi.fn().mockResolvedValue(undefined);
    render(<ConnectionPanel open required onClose={vi.fn()} onConnected={vi.fn()} onExploreDemo={explore} />);

    fireEvent.click(screen.getByRole("button", { name: "Explore public demo" }));

    await waitFor(() => expect(explore).toHaveBeenCalledOnce());
    expect(pairCompanion).not.toHaveBeenCalled();
    expect(currentEndpoint).toHaveBeenCalled();
  });
});
