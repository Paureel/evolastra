import { stableHash } from "./layout";

export const DEFAULT_UNCLAIMED_SYSTEMS = 200;
export const FRONTIER_EXPANSION_SIZE = 100;

export interface FrontierSystem {
  id: string;
  x: number;
  y: number;
  z: number;
  radius: number;
  singularity: boolean;
  depth?: number;
}

export interface FrontierLane {
  source: number;
  target: number;
}

export interface FrontierField {
  systems: FrontierSystem[];
  lanes: FrontierLane[];
}

export interface FrontierBridge {
  claimedId: string;
  frontier: number;
}

export interface StellarProfile {
  kind: "star" | "pulsar" | "black-hole";
  core: string;
  body: string;
  halo: string;
  label: string;
}

export function frontierSystemCount(claimedCount: number): number {
  const claimed = Math.max(0, Math.floor(claimedCount));
  if (claimed < DEFAULT_UNCLAIMED_SYSTEMS) return DEFAULT_UNCLAIMED_SYSTEMS;
  return DEFAULT_UNCLAIMED_SYSTEMS + FRONTIER_EXPANSION_SIZE * (Math.floor((claimed - DEFAULT_UNCLAIMED_SYSTEMS) / FRONTIER_EXPANSION_SIZE) + 1);
}

export function galaxyCameraZoom(frontierCount: number): number {
  const expansionRatio = Math.max(DEFAULT_UNCLAIMED_SYSTEMS, frontierCount) / DEFAULT_UNCLAIMED_SYSTEMS;
  return Math.max(0.48, 0.68 / expansionRatio ** 0.08);
}

const SPECTRAL_PROFILES: StellarProfile[] = [
  { kind: "star", core: "#f5fbff", body: "#8fc8ff", halo: "#3f78e8", label: "blue giant" },
  { kind: "star", core: "#ffffff", body: "#d8ecff", halo: "#83aadb", label: "white star" },
  { kind: "star", core: "#fffde8", body: "#ffd86f", halo: "#d88b31", label: "yellow star" },
  { kind: "star", core: "#fff2d7", body: "#ff9d55", halo: "#bb4c30", label: "orange star" },
  { kind: "star", core: "#ffe8e2", body: "#f26d61", halo: "#8d3045", label: "red dwarf" },
];

function unit(value: string, seed: number): number {
  return stableHash(value, seed) / 0xffffffff;
}

export function stellarProfile(id: string, seed: number, ordinal: number): StellarProfile {
  const hash = stableHash(id, seed);
  if (ordinal > 0 && (ordinal === 6 || hash % 23 === 0)) {
    return { kind: "black-hole", core: "#020208", body: "#d6e7ff", halo: "#9a67ed", label: "black hole" };
  }
  if (ordinal > 0 && (ordinal === 3 || hash % 19 === 0)) {
    return { kind: "pulsar", core: "#ffffff", body: "#9deeff", halo: "#4d72ff", label: "pulsar" };
  }
  return SPECTRAL_PROFILES[hash % SPECTRAL_PROFILES.length];
}

export function stellarProfilesFor(systemIds: string[], seed: number): Map<string, StellarProfile> {
  return new Map(systemIds.map((id, ordinal) => [id, stellarProfile(id, seed, ordinal)]));
}

export function createFrontierField(seed: number, count = DEFAULT_UNCLAIMED_SYSTEMS): FrontierField {
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const fieldScale = Math.sqrt(Math.max(DEFAULT_UNCLAIMED_SYSTEMS, count) / DEFAULT_UNCLAIMED_SYSTEMS);
  const innerRadius = 680 * fieldScale;
  const outerRadius = 1120 * fieldScale;
  const approachCount = Math.min(count, Math.max(14, Math.round(count * 0.1)));
  const outerCount = Math.max(1, count - approachCount);
  const systems = Array.from({ length: count }, (_, index): FrontierSystem => {
    const angle = index * goldenAngle + unit(`frontier-angle:${index}`, seed) * 0.58;
    const approach = index < approachCount;
    const progress = approach
      ? (index + 0.45) / approachCount
      : (index - approachCount + 0.5) / outerCount;
    const radius = approach
      ? 220 + progress ** 0.82 * (innerRadius - 250) + (unit(`frontier-radius:${index}`, seed) - 0.5) * 34
      : Math.sqrt(innerRadius ** 2 + progress * (outerRadius ** 2 - innerRadius ** 2)) + (unit(`frontier-radius:${index}`, seed) - 0.5) * 76;
    return {
      id: `uncharted-${index.toString().padStart(3, "0")}`,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius * 0.62 + (unit(`frontier-plane:${index}`, seed) - 0.5) * 48,
      z: (unit(`frontier-depth:${index}`, seed) - 0.5) * 150,
      radius: 1.6 + unit(`frontier-size:${index}`, seed) * 1.7,
      singularity: stableHash(`frontier-kind:${index}`, seed) % 41 === 0,
    };
  });

  const laneKeys = new Set<string>();
  const lanes: FrontierLane[] = [];
  const addLane = (source: number, target: number): void => {
    const low = Math.min(source, target);
    const high = Math.max(source, target);
    const key = `${low}:${high}`;
    if (laneKeys.has(key)) return;
    laneKeys.add(key);
    lanes.push({ source: low, target: high });
  };

  // Prim's minimum-spanning tree guarantees one component without the long
  // core-crossing links produced by generation-order connections.
  if (systems.length > 1) {
    const inTree = Array.from({ length: systems.length }, () => false);
    const nearestDistance = Array.from({ length: systems.length }, (_, index) => index === 0 ? 0 : Number.POSITIVE_INFINITY);
    const nearestParent = Array.from({ length: systems.length }, () => -1);
    for (let iteration = 0; iteration < systems.length; iteration += 1) {
      let source = -1;
      for (let index = 0; index < systems.length; index += 1) {
        if (inTree[index]) continue;
        if (source === -1 || nearestDistance[index] < nearestDistance[source] || (nearestDistance[index] === nearestDistance[source] && index < source)) source = index;
      }
      if (source === -1) break;
      inTree[source] = true;
      if (nearestParent[source] >= 0) addLane(source, nearestParent[source]);
      systems.forEach((candidate, target) => {
        if (inTree[target]) return;
        const system = systems[source];
        const candidateDistance = Math.hypot(candidate.x - system.x, candidate.y - system.y, candidate.z - system.z);
        if (candidateDistance < nearestDistance[target] || (candidateDistance === nearestDistance[target] && source < nearestParent[target])) {
          nearestDistance[target] = candidateDistance;
          nearestParent[target] = source;
        }
      });
    }
  }

  systems.forEach((system, source) => {
    const nearest = systems
      .map((candidate, target) => ({ target, distance: target === source ? Number.POSITIVE_INFINITY : Math.hypot(candidate.x - system.x, candidate.y - system.y, candidate.z - system.z) }))
      .sort((left, right) => left.distance - right.distance)
      .slice(0, 2);
    nearest.forEach(({ target }) => {
      addLane(source, target);
    });
  });

  return { systems, lanes };
}

export function frontierClaimedBridges(frontier: FrontierField, claimed: Array<{ id: string; x: number; y: number; z: number }>): FrontierBridge[] {
  if (frontier.systems.length === 0) return [];
  return claimed.map((system) => {
    let frontierIndex = 0;
    let nearestDistance = Number.POSITIVE_INFINITY;
    frontier.systems.forEach((candidate, index) => {
      const candidateDistance = Math.hypot(candidate.x - system.x, candidate.y - system.y, candidate.z - system.z);
      if (candidateDistance < nearestDistance) {
        frontierIndex = index;
        nearestDistance = candidateDistance;
      }
    });
    return { claimedId: system.id, frontier: frontierIndex };
  });
}
