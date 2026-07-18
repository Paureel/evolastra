import type { NodeEntity } from "./types";

export type TechState = "completed" | "researching" | "available" | "locked";

export interface TechTier {
  id: string;
  label: string;
  glyph: string;
  nodes: Array<NodeEntity & { techState: TechState }>;
}

const PHASES = [
  { id: "foundation", label: "Data foundation", glyph: "◈", types: ["data"] },
  { id: "signals", label: "Signal research", glyph: "⌁", types: ["exploration"] },
  { id: "models", label: "Modeling", glyph: "⬡", types: ["modeling"] },
  { id: "validation", label: "Validation", glyph: "◇", types: ["validation"] },
  { id: "synthesis", label: "Synthesis", glyph: "✦", types: ["synthesis"] },
  { id: "frontier", label: "Frontier research", glyph: "◎", types: ["unexplored"] },
] as const;

const COMPLETE = new Set(["completed", "validated", "promoted", "resolved", "approved"]);

export function buildTechTiers(nodes: NodeEntity[]): TechTier[] {
  let prerequisitesComplete = true;
  return PHASES.map((phase) => {
    const phaseNodes = nodes.filter((node) => phase.types.includes(String(node.node_type) as never));
    const decorated = phaseNodes.map((node) => {
      const status = String(node.status ?? "created");
      let techState: TechState;
      if (COMPLETE.has(status) || Number(node.progress ?? 0) >= 1) techState = "completed";
      else if (status === "running" || Number(node.progress ?? 0) > 0) techState = "researching";
      else techState = prerequisitesComplete ? "available" : "locked";
      return { ...node, techState };
    });
    const tier: TechTier = { id: phase.id, label: phase.label, glyph: phase.glyph, nodes: decorated };
    if (phaseNodes.length > 0) prerequisitesComplete = decorated.every((node) => node.techState === "completed");
    return tier;
  }).filter((tier) => tier.nodes.length > 0);
}
