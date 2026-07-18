import type { EdgeEntity, PositionedEntity } from "./types";

export interface ConnectedLane {
  sourceId: string;
  targetId: string;
  type: string;
  key: string;
  synthetic: boolean;
}

function distance(left: PositionedEntity, right: PositionedEntity): number {
  return Math.hypot(left.x - right.x, left.y - right.y, left.z - right.z);
}

export function connectedHyperlanes(layout: PositionedEntity[], edges: EdgeEntity[]): ConnectedLane[] {
  const lookup = new Map(layout.map((entity) => [entity.id, entity]));
  const systems = layout.filter((entity) => entity.kind === "home" || entity.kind === "node");
  const systemIds = new Set(systems.map((entity) => entity.id));
  const parent = new Map(systems.map((entity) => [entity.id, entity.id]));
  const find = (id: string): string => {
    const current = parent.get(id) ?? id;
    if (current === id) return id;
    const root = find(current);
    parent.set(id, root);
    return root;
  };
  const union = (left: string, right: string): void => {
    const leftRoot = find(left);
    const rightRoot = find(right);
    if (leftRoot !== rightRoot) parent.set(rightRoot, leftRoot);
  };

  const seen = new Set<string>();
  const lanes: ConnectedLane[] = [];
  for (const edge of edges) {
    if (!lookup.has(edge.source_id) || !lookup.has(edge.target_id) || edge.source_id === edge.target_id) continue;
    const pair = [edge.source_id, edge.target_id].sort().join(":");
    if (seen.has(pair)) continue;
    seen.add(pair);
    lanes.push({
      sourceId: edge.source_id,
      targetId: edge.target_id,
      type: String(edge.edge_type ?? "related"),
      key: `${edge.source_id}:${edge.target_id}`,
      synthetic: false,
    });
    if (systemIds.has(edge.source_id) && systemIds.has(edge.target_id)) union(edge.source_id, edge.target_id);
  }

  while (new Set(systems.map((system) => find(system.id))).size > 1) {
    let nearest: { left: PositionedEntity; right: PositionedEntity; distance: number } | null = null;
    systems.forEach((left, leftIndex) => {
      systems.slice(leftIndex + 1).forEach((right) => {
        if (find(left.id) === find(right.id)) return;
        const candidateDistance = distance(left, right);
        if (!nearest || candidateDistance < nearest.distance || (candidateDistance === nearest.distance && `${left.id}:${right.id}` < `${nearest.left.id}:${nearest.right.id}`)) {
          nearest = { left, right, distance: candidateDistance };
        }
      });
    });
    if (!nearest) break;
    const bridge = nearest as { left: PositionedEntity; right: PositionedEntity; distance: number };
    const pair = [bridge.left.id, bridge.right.id].sort().join(":");
    if (!seen.has(pair)) {
      seen.add(pair);
      lanes.push({
        sourceId: bridge.left.id,
        targetId: bridge.right.id,
        type: "charted",
        key: `charted:${pair}`,
        synthetic: true,
      });
    }
    union(bridge.left.id, bridge.right.id);
  }

  return lanes;
}
