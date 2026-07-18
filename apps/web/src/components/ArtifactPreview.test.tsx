import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ArtifactPreview } from "./ArtifactPreview";

const cnaArtifact = {
  id: "art_cna",
  title: "Candidate amplified STAD drivers",
  mime_type: "application/json",
  hash: "sha256:test",
  preview: {
    kind: "table",
    row_count: 2,
    values: [
      { gene: "MYC", cytoband: "8q24.21", gain_pct: 57.8, high_gain_pct: 17.6, loss_pct: 0.2, deep_loss_pct: 0 },
      { gene: "ERBB2", cytoband: "17q12", gain_pct: 23.5, high_gain_pct: 14.6, loss_pct: 2.1, deep_loss_pct: 0 },
    ],
  },
};

afterEach(cleanup);

describe("ArtifactPreview", () => {
  it("renders scientific CNA table rows as a visible diverging figure", () => {
    render(<ArtifactPreview artifact={cnaArtifact} onClose={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Candidate amplified STAD drivers" })).toBeVisible();
    expect(screen.getByText("Copy-number event frequency")).toBeVisible();
    expect(screen.getByText("MYC")).toBeVisible();
    expect(screen.getByLabelText("MYC gain 57.8 percent, high gain 17.6 percent")).toBeVisible();
    expect(screen.getByText("Complete · 2 rows")).toBeVisible();
  });

  it("shows a directed empty state instead of a blank dark preview", () => {
    render(<ArtifactPreview artifact={{ id: "art_empty", title: "Metadata only", preview: {} }} onClose={vi.fn()} />);
    expect(screen.getByText("No bounded preview data")).toBeVisible();
    expect(screen.getByText(/does not contain a safe text, table, or numeric figure payload/i)).toBeVisible();
  });

  it("closes from the labeled control", () => {
    const onClose = vi.fn();
    render(<ArtifactPreview artifact={cnaArtifact} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Close preview" }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
