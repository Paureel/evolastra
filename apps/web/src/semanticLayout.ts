import type { SemanticSignature } from "./types";

export interface SemanticSystem {
  id: string;
  semanticSignature: SemanticSignature;
}

export interface SemanticPoint {
  x: number;
  y: number;
  z: number;
}

export interface SemanticLayoutMetrics {
  spearman: number;
  meanWithinProgram: number;
  meanBetweenPrograms: number;
  sameProgramNearestNeighbors: number;
  pairCount: number;
}

const CATEGORY_WEIGHTS = {
  program: 5,
  genes: 5,
  cytobands: 4,
  mechanisms: 4,
  therapeuticModalities: 3,
  alterationDirection: 2,
  validationModalities: 1,
} as const;

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.slice(0, 30).flatMap((item) => {
    const text = stringValue(item);
    return text ? [text.slice(0, 120)] : [];
  });
}

export function parseSemanticSignature(value: unknown): SemanticSignature | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const record = value as Record<string, unknown>;
  const program = stringValue(record.program).slice(0, 120);
  const alterationDirection = stringValue(record.alteration_direction ?? record.alterationDirection).slice(0, 80);
  if (!program || !alterationDirection) return undefined;
  return {
    program,
    alterationDirection,
    genes: stringList(record.genes),
    cytobands: stringList(record.cytobands),
    mechanisms: stringList(record.mechanisms),
    therapeuticModalities: stringList(record.therapeutic_modalities ?? record.therapeuticModalities),
    validationModalities: stringList(record.validation_modalities ?? record.validationModalities),
  };
}

function stableHash(value: string, seed = 0): number {
  let hash = (2166136261 ^ seed) >>> 0;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function normalizedTokens(value: string | string[]): string[] {
  const values = Array.isArray(value) ? value : [value];
  return [...new Set(values.map((item) => item.trim().toLocaleLowerCase()).filter(Boolean))].sort();
}

function fieldDistance(left: string[], right: string[]): number | null {
  const union = new Set([...left, ...right]);
  if (union.size === 0) return null;
  const rightSet = new Set(right);
  const intersection = left.filter((item) => rightSet.has(item)).length;
  return 1 - intersection / union.size;
}

export function semanticDistance(left: SemanticSignature, right: SemanticSignature): number {
  const fields: Array<[number, string[], string[]]> = [
    [CATEGORY_WEIGHTS.program, normalizedTokens(left.program), normalizedTokens(right.program)],
    [CATEGORY_WEIGHTS.genes, normalizedTokens(left.genes), normalizedTokens(right.genes)],
    [CATEGORY_WEIGHTS.cytobands, normalizedTokens(left.cytobands), normalizedTokens(right.cytobands)],
    [CATEGORY_WEIGHTS.mechanisms, normalizedTokens(left.mechanisms), normalizedTokens(right.mechanisms)],
    [CATEGORY_WEIGHTS.therapeuticModalities, normalizedTokens(left.therapeuticModalities), normalizedTokens(right.therapeuticModalities)],
    [CATEGORY_WEIGHTS.alterationDirection, normalizedTokens(left.alterationDirection), normalizedTokens(right.alterationDirection)],
    [CATEGORY_WEIGHTS.validationModalities, normalizedTokens(left.validationModalities), normalizedTokens(right.validationModalities)],
  ];
  let weightedDistance = 0;
  let totalWeight = 0;
  for (const [weight, leftValues, rightValues] of fields) {
    const distance = fieldDistance(leftValues, rightValues);
    if (distance === null) continue;
    weightedDistance += weight * distance;
    totalWeight += weight;
  }
  return totalWeight ? weightedDistance / totalWeight : 0;
}

function initialCoordinate(id: string, axis: string, seed: number): number {
  return ((stableHash(`${id}:semantic:${axis}`, seed) % 100_000) / 99_999 - 0.5) * 600;
}

function recenter(points: SemanticPoint[]): void {
  if (!points.length) return;
  const center = points.reduce((sum, point) => ({ x: sum.x + point.x, y: sum.y + point.y, z: sum.z + point.z }), { x: 0, y: 0, z: 0 });
  center.x /= points.length;
  center.y /= points.length;
  center.z /= points.length;
  points.forEach((point) => {
    point.x -= center.x;
    point.y -= center.y;
    point.z -= center.z;
  });
}

export function semanticCoordinates(systems: SemanticSystem[], seed: number): Map<string, SemanticPoint> {
  if (systems.length === 0) return new Map();
  if (systems.length === 1) return new Map([[systems[0].id, { x: 300, y: 0, z: 0 }]]);
  const ordered = [...systems].sort((left, right) => left.id.localeCompare(right.id));
  const points = ordered.map((system) => ({
    x: initialCoordinate(system.id, "x", seed),
    y: initialCoordinate(system.id, "y", seed),
    z: initialCoordinate(system.id, "z", seed),
  }));
  recenter(points);

  const iterations = 1_200;
  for (let iteration = 0; iteration < iterations; iteration += 1) {
    const gradients = points.map(() => ({ x: 0, y: 0, z: 0 }));
    for (let leftIndex = 0; leftIndex < ordered.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < ordered.length; rightIndex += 1) {
        const left = points[leftIndex];
        const right = points[rightIndex];
        const dx = left.x - right.x;
        const dy = left.y - right.y;
        const dz = left.z - right.z;
        const current = Math.max(0.0001, Math.hypot(dx, dy, dz));
        const target = 120 + 560 * semanticDistance(ordered[leftIndex].semanticSignature, ordered[rightIndex].semanticSignature);
        const scale = (current - target) / current;
        gradients[leftIndex].x += scale * dx;
        gradients[leftIndex].y += scale * dy;
        gradients[leftIndex].z += scale * dz;
        gradients[rightIndex].x -= scale * dx;
        gradients[rightIndex].y -= scale * dy;
        gradients[rightIndex].z -= scale * dz;
      }
    }
    const learningRate = 0.018 * (1 - iteration / iterations);
    points.forEach((point, index) => {
      point.x -= learningRate * gradients[index].x;
      point.y -= learningRate * gradients[index].y;
      point.z -= learningRate * gradients[index].z;
    });
    recenter(points);
  }

  const maxRadius = Math.max(...points.map((point) => Math.hypot(point.x, point.y, point.z)), 1);
  const scale = 520 / maxRadius;
  return new Map(ordered.map((system, index) => [system.id, {
    x: points[index].x * scale,
    y: points[index].y * scale,
    z: points[index].z * scale,
  }]));
}

function averageRanks(values: number[]): number[] {
  const indexed = values.map((value, index) => ({ value, index })).sort((left, right) => left.value - right.value);
  const ranks = Array(values.length).fill(0) as number[];
  let cursor = 0;
  while (cursor < indexed.length) {
    let end = cursor + 1;
    while (end < indexed.length && Math.abs(indexed[end].value - indexed[cursor].value) < 1e-12) end += 1;
    const rank = (cursor + 1 + end) / 2;
    for (let item = cursor; item < end; item += 1) ranks[indexed[item].index] = rank;
    cursor = end;
  }
  return ranks;
}

function correlation(left: number[], right: number[]): number {
  if (!left.length || left.length !== right.length) return 0;
  const leftMean = left.reduce((sum, value) => sum + value, 0) / left.length;
  const rightMean = right.reduce((sum, value) => sum + value, 0) / right.length;
  let numerator = 0;
  let leftSquares = 0;
  let rightSquares = 0;
  left.forEach((value, index) => {
    const leftDelta = value - leftMean;
    const rightDelta = right[index] - rightMean;
    numerator += leftDelta * rightDelta;
    leftSquares += leftDelta ** 2;
    rightSquares += rightDelta ** 2;
  });
  const denominator = Math.sqrt(leftSquares * rightSquares);
  return denominator ? numerator / denominator : 0;
}

export function semanticLayoutMetrics(systems: SemanticSystem[], points: Map<string, SemanticPoint>): SemanticLayoutMetrics {
  const semanticDistances: number[] = [];
  const mapDistances: number[] = [];
  const within: number[] = [];
  const between: number[] = [];
  let sameProgramNearestNeighbors = 0;
  let maxMapDistance = 0;

  for (let leftIndex = 0; leftIndex < systems.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < systems.length; rightIndex += 1) {
      const leftPoint = points.get(systems[leftIndex].id);
      const rightPoint = points.get(systems[rightIndex].id);
      if (!leftPoint || !rightPoint) continue;
      const mapDistance = Math.hypot(leftPoint.x - rightPoint.x, leftPoint.y - rightPoint.y, leftPoint.z - rightPoint.z);
      maxMapDistance = Math.max(maxMapDistance, mapDistance);
      semanticDistances.push(semanticDistance(systems[leftIndex].semanticSignature, systems[rightIndex].semanticSignature));
      mapDistances.push(mapDistance);
      const sameProgram = normalizedTokens(systems[leftIndex].semanticSignature.program)[0] === normalizedTokens(systems[rightIndex].semanticSignature.program)[0];
      (sameProgram ? within : between).push(mapDistance);
    }
  }

  for (const system of systems) {
    const point = points.get(system.id);
    if (!point) continue;
    const nearest = systems
      .filter((candidate) => candidate.id !== system.id && points.has(candidate.id))
      .map((candidate) => {
        const candidatePoint = points.get(candidate.id)!;
        return { candidate, distance: Math.hypot(point.x - candidatePoint.x, point.y - candidatePoint.y, point.z - candidatePoint.z) };
      })
      .sort((left, right) => left.distance - right.distance || left.candidate.id.localeCompare(right.candidate.id))[0]?.candidate;
    if (nearest && normalizedTokens(nearest.semanticSignature.program)[0] === normalizedTokens(system.semanticSignature.program)[0]) sameProgramNearestNeighbors += 1;
  }

  const normalizedMap = mapDistances.map((distance) => maxMapDistance ? distance / maxMapDistance : 0);
  return {
    spearman: correlation(averageRanks(semanticDistances), averageRanks(normalizedMap)),
    meanWithinProgram: within.length ? within.reduce((sum, value) => sum + value, 0) / within.length : 0,
    meanBetweenPrograms: between.length ? between.reduce((sum, value) => sum + value, 0) / between.length : 0,
    sameProgramNearestNeighbors,
    pairCount: mapDistances.length,
  };
}
