import { projectPoint3D, type ProjectedPoint, type SpatialCamera } from "./spatial";
import type { PositionedEntity } from "./types";

export interface PlanarPoint {
  x: number;
  y: number;
}

export interface PlanarTerritorySystem extends PlanarPoint {
  id: string;
  owner: string;
}

export interface TerritoryRegion {
  owner: string;
  systemIds: string[];
  loops: PlanarPoint[][];
}

export interface TerritoryLayer {
  regions: TerritoryRegion[];
  opacity: number;
}

export function territorySystemsForLayout(
  layout: PositionedEntity[],
  claims: Record<string, string>,
  singlePlayerColor: string,
): PlanarTerritorySystem[] {
  const multiplayerActive = Object.keys(claims).length > 0;
  return layout
    .filter((entity) => entity.kind === "home" || entity.kind === "node")
    .flatMap((entity) => {
      const owner = multiplayerActive ? claims[entity.id] : singlePlayerColor;
      return owner ? [{ id: entity.id, owner: owner.toUpperCase(), x: entity.x, y: entity.y }] : [];
    });
}

interface GridPoint {
  column: number;
  row: number;
}

interface GridEdge {
  start: GridPoint;
  end: GridPoint;
}

interface TerritoryNetwork {
  owner: string;
  systems: PlanarTerritorySystem[];
  links: Array<[PlanarTerritorySystem, PlanarTerritorySystem]>;
}

function squaredDistance(left: PlanarPoint, right: PlanarPoint): number {
  return (left.x - right.x) ** 2 + (left.y - right.y) ** 2;
}

function distanceToSegment(point: PlanarPoint, start: PlanarPoint, end: PlanarPoint): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (!lengthSquared) return Math.sqrt(squaredDistance(point, start));
  const progress = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared));
  return Math.hypot(point.x - (start.x + dx * progress), point.y - (start.y + dy * progress));
}

function minimumSpanningLinks(systems: PlanarTerritorySystem[]): Array<[PlanarTerritorySystem, PlanarTerritorySystem]> {
  if (systems.length < 2) return [];
  const ordered = [...systems].sort((left, right) => left.id.localeCompare(right.id));
  const visited = new Set([ordered[0].id]);
  const links: Array<[PlanarTerritorySystem, PlanarTerritorySystem]> = [];
  while (visited.size < ordered.length) {
    let best: { left: PlanarTerritorySystem; right: PlanarTerritorySystem; distance: number; key: string } | null = null;
    for (const left of ordered.filter((system) => visited.has(system.id))) {
      for (const right of ordered.filter((system) => !visited.has(system.id))) {
        const candidate = { left, right, distance: squaredDistance(left, right), key: `${left.id}:${right.id}` };
        if (!best || candidate.distance < best.distance || (candidate.distance === best.distance && candidate.key < best.key)) best = candidate;
      }
    }
    if (!best) break;
    links.push([best.left, best.right]);
    visited.add(best.right.id);
  }
  return links;
}

function territoryNetworks(systems: PlanarTerritorySystem[]): TerritoryNetwork[] {
  const groups = new Map<string, PlanarTerritorySystem[]>();
  for (const system of systems) groups.set(system.owner, [...(groups.get(system.owner) ?? []), system]);
  return [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([owner, owned]) => ({ owner, systems: owned, links: minimumSpanningLinks(owned) }));
}

function networkInfluence(network: TerritoryNetwork, point: PlanarPoint, nodeRadius: number, corridorRadius: number): number {
  let influence = Number.NEGATIVE_INFINITY;
  for (const system of network.systems) influence = Math.max(influence, nodeRadius - Math.sqrt(squaredDistance(point, system)));
  for (const [start, end] of network.links) influence = Math.max(influence, corridorRadius - distanceToSegment(point, start, end));
  return influence;
}

function gridKey(point: GridPoint): string {
  return `${point.column}:${point.row}`;
}

function direction(edge: GridEdge): number {
  if (edge.end.column > edge.start.column) return 0;
  if (edge.end.row > edge.start.row) return 1;
  if (edge.end.column < edge.start.column) return 2;
  return 3;
}

function distanceToLine(point: PlanarPoint, start: PlanarPoint, end: PlanarPoint): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (!lengthSquared) return Math.sqrt(squaredDistance(point, start));
  const progress = ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared;
  return Math.hypot(point.x - (start.x + dx * progress), point.y - (start.y + dy * progress));
}

function simplifyOpenLine(points: PlanarPoint[], tolerance: number): PlanarPoint[] {
  if (points.length <= 2) return points;
  let furthestIndex = 0;
  let furthestDistance = 0;
  for (let index = 1; index < points.length - 1; index += 1) {
    const distance = distanceToLine(points[index], points[0], points.at(-1)!);
    if (distance > furthestDistance) {
      furthestDistance = distance;
      furthestIndex = index;
    }
  }
  if (furthestDistance <= tolerance) return [points[0], points.at(-1)!];
  return [
    ...simplifyOpenLine(points.slice(0, furthestIndex + 1), tolerance).slice(0, -1),
    ...simplifyOpenLine(points.slice(furthestIndex), tolerance),
  ];
}

function simplifyClosedLoop(points: PlanarPoint[], tolerance: number): PlanarPoint[] {
  if (points.length < 8) return points;
  let split = 1;
  for (let index = 2; index < points.length; index += 1) {
    if (squaredDistance(points[0], points[index]) > squaredDistance(points[0], points[split])) split = index;
  }
  const firstArc = points.slice(0, split + 1);
  const secondArc = [...points.slice(split), points[0]];
  return [
    ...simplifyOpenLine(firstArc, tolerance).slice(0, -1),
    ...simplifyOpenLine(secondArc, tolerance).slice(0, -1),
  ];
}

function chainEdges(edges: GridEdge[], origin: PlanarPoint, cellSize: number): PlanarPoint[][] {
  const outgoing = new Map<string, number[]>();
  edges.forEach((edge, index) => outgoing.set(gridKey(edge.start), [...(outgoing.get(gridKey(edge.start)) ?? []), index]));
  const unused = new Set(edges.map((_, index) => index));
  const loops: PlanarPoint[][] = [];
  while (unused.size) {
    const firstIndex = Math.min(...unused);
    const first = edges[firstIndex];
    const chained: GridPoint[] = [first.start];
    let currentIndex = firstIndex;
    while (unused.has(currentIndex)) {
      const current = edges[currentIndex];
      unused.delete(currentIndex);
      chained.push(current.end);
      if (gridKey(current.end) === gridKey(first.start)) break;
      const currentDirection = direction(current);
      const candidates = (outgoing.get(gridKey(current.end)) ?? []).filter((index) => unused.has(index));
      if (!candidates.length) break;
      const turnRank = (candidate: number): number => {
        const turn = (direction(edges[candidate]) - currentDirection + 4) % 4;
        return turn === 1 ? 0 : turn === 0 ? 1 : turn === 3 ? 2 : 3;
      };
      currentIndex = candidates.sort((left, right) => turnRank(left) - turnRank(right) || left - right)[0];
    }
    if (chained.length < 4 || gridKey(chained.at(-1)!) !== gridKey(chained[0])) continue;
    const points = chained.slice(0, -1).filter((point, index, all) => {
      const previous = all[(index - 1 + all.length) % all.length];
      const next = all[(index + 1) % all.length];
      return (point.column - previous.column) * (next.row - point.row) !== (point.row - previous.row) * (next.column - point.column);
    }).map((point) => ({ x: origin.x + point.column * cellSize, y: origin.y + point.row * cellSize }));
    if (points.length >= 4) {
      let smoothed = simplifyClosedLoop(points, cellSize * 1.35);
      for (let pass = 0; pass < 2; pass += 1) {
        smoothed = smoothed.flatMap((point, index) => {
          const next = smoothed[(index + 1) % smoothed.length];
          return [
            { x: point.x * 0.75 + next.x * 0.25, y: point.y * 0.75 + next.y * 0.25 },
            { x: point.x * 0.25 + next.x * 0.75, y: point.y * 0.25 + next.y * 0.75 },
          ];
        });
      }
      loops.push(smoothed);
    }
  }
  return loops;
}

export function buildTerritoryRegions(
  systems: PlanarTerritorySystem[],
  options: { nodeRadius?: number; corridorRadius?: number; cellSize?: number } = {},
): TerritoryRegion[] {
  if (!systems.length) return [];
  const networks = territoryNetworks(systems);
  const nodeRadius = options.nodeRadius ?? 76;
  const corridorRadius = options.corridorRadius ?? 34;
  const minX = Math.min(...systems.map((system) => system.x)) - nodeRadius - 12;
  const maxX = Math.max(...systems.map((system) => system.x)) + nodeRadius + 12;
  const minY = Math.min(...systems.map((system) => system.y)) - nodeRadius - 12;
  const maxY = Math.max(...systems.map((system) => system.y)) + nodeRadius + 12;
  const extent = Math.max(maxX - minX, maxY - minY);
  const cellSize = options.cellSize ?? Math.max(8, Math.min(16, extent / 100));
  const columns = Math.ceil((maxX - minX) / cellSize);
  const rows = Math.ceil((maxY - minY) / cellSize);
  const owners = Array<string | null>(columns * rows).fill(null);
  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const point = { x: minX + (column + 0.5) * cellSize, y: minY + (row + 0.5) * cellSize };
      let best: { owner: string; influence: number } | null = null;
      for (const network of networks) {
        const influence = networkInfluence(network, point, nodeRadius, corridorRadius);
        if (influence >= 0 && (!best || influence > best.influence || (influence === best.influence && network.owner < best.owner))) best = { owner: network.owner, influence };
      }
      owners[row * columns + column] = best?.owner ?? null;
    }
  }

  const ownerAt = (column: number, row: number): string | null => column < 0 || row < 0 || column >= columns || row >= rows ? null : owners[row * columns + column];
  return networks.map((network) => {
    const edges: GridEdge[] = [];
    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns; column += 1) {
        if (ownerAt(column, row) !== network.owner) continue;
        if (ownerAt(column, row - 1) !== network.owner) edges.push({ start: { column, row }, end: { column: column + 1, row } });
        if (ownerAt(column + 1, row) !== network.owner) edges.push({ start: { column: column + 1, row }, end: { column: column + 1, row: row + 1 } });
        if (ownerAt(column, row + 1) !== network.owner) edges.push({ start: { column: column + 1, row: row + 1 }, end: { column, row: row + 1 } });
        if (ownerAt(column - 1, row) !== network.owner) edges.push({ start: { column, row: row + 1 }, end: { column, row } });
      }
    }
    return {
      owner: network.owner,
      systemIds: network.systems.map((system) => system.id).sort(),
      loops: chainEdges(edges, { x: minX, y: minY }, cellSize),
    };
  });
}

export function projectTerritoryPoint(point: PlanarPoint, camera: SpatialCamera): ProjectedPoint {
  return projectPoint3D({ ...point, z: 0 }, camera);
}

export function territoryTransitionLayers(previous: TerritoryRegion[], current: TerritoryRegion[], progress: number): TerritoryLayer[] {
  const bounded = Math.max(0, Math.min(1, progress));
  if (bounded <= 0) return previous.length ? [{ regions: previous, opacity: 1 }] : [{ regions: current, opacity: 1 }];
  if (bounded >= 1 || !previous.length) return [{ regions: current, opacity: 1 }];
  return [
    { regions: previous, opacity: 1 - bounded },
    { regions: current, opacity: bounded },
  ];
}
