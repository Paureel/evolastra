import type { PositionedEntity, SceneEntity, SpaceMapMode } from "./types";

export function stableHash(value: string, seed = 0): number {
  let hash = (2166136261 ^ seed) >>> 0;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function layoutGalaxy(entities: SceneEntity[], seed: number): PositionedEntity[] {
  const positions = new Map<string, PositionedEntity>();
  const home = entities.find((entity) => entity.kind === "home");
  if (home) {
    positions.set(home.id, { ...home, x: -18, y: 12, z: 0, radius: 17, angle: 0 });
  }
  const nodes = entities.filter((entity) => entity.kind === "node");
  const topLevel = nodes.filter((entity) => !entity.parentId || entity.parentId === home?.id);

  topLevel.forEach((entity) => {
    const slot = stableHash(entity.id, seed) % 360;
    const angle = (slot / 180) * Math.PI;
    const radialUnit = (stableHash(`${entity.id}:ring`, seed) % 10_000) / 10_000;
    const ring = 185 + Math.sqrt(radialUnit) * 315;
    const flatten = 0.68 + (stableHash(`${entity.id}:plane`, seed) % 17) / 100;
    positions.set(entity.id, {
      ...entity,
      x: Math.cos(angle) * ring,
      y: Math.sin(angle) * ring * flatten,
      z: ((stableHash(`${entity.id}:depth`, seed) % 10_000) / 10_000 - 0.5) * 130,
      radius: 8 + Math.min(4, (entity.progress ?? 0) * 4),
      angle,
    });
  });

  const agentsBySystem = new Map<string, SceneEntity[]>();
  for (const agent of entities.filter((entity) => entity.kind === "agent")) {
    const systemId = agent.parentId && positions.has(agent.parentId) ? agent.parentId : home?.id;
    if (!systemId) continue;
    const stationed = agentsBySystem.get(systemId) ?? [];
    stationed.push(agent);
    agentsBySystem.set(systemId, stationed);
  }
  for (const [systemId, stationed] of agentsBySystem) {
    const system = positions.get(systemId);
    if (!system) continue;
    stationed
      .sort((left, right) => stableHash(left.id, seed) - stableHash(right.id, seed))
      .forEach((agent, index) => {
        const centeredIndex = index - (stationed.length - 1) / 2;
        const outwardAngle = Math.atan2(system.y, system.x || 1) + Math.PI * 0.44 + centeredIndex * 0.48;
        const distance = system.radius + 42 + Math.floor(index / 3) * 17;
        const x = system.x + Math.cos(outwardAngle) * distance;
        const y = system.y + Math.sin(outwardAngle) * distance;
        positions.set(agent.id, {
          ...agent,
          x,
          y,
          z: system.z + ((stableHash(`${agent.id}:depth`, seed) % 10_000) / 10_000 - 0.5) * 32,
          radius: 6.5,
          angle: Math.atan2(system.y - y, system.x - x),
        });
      });
  }
  return entities.flatMap((entity) => {
    const position = positions.get(entity.id);
    return position ? [position] : [];
  });
}

function layoutSystem(entities: SceneEntity[], seed: number, focusSystemId?: string): PositionedEntity[] {
  const fallback = entities.find((entity) => entity.kind === "home");
  const focus = entities.find((entity) => entity.id === focusSystemId && ["home", "node"].includes(entity.kind)) ?? fallback;
  if (!focus) return [];
  const positions: PositionedEntity[] = [{ ...focus, x: 0, y: 0, z: 0, radius: 31, angle: 0 }];
  const satellites = entities
    .filter((entity) => entity.id !== focus.id && entity.parentId === focus.id)
    .sort((left, right) => stableHash(left.id, seed) - stableHash(right.id, seed));
  satellites.forEach((entity, index) => {
    const slot = stableHash(entity.id, seed) % 360;
    const angle = (slot / 180) * Math.PI;
    const kindRing = entity.kind === "agent" ? 92 : entity.kind === "artifact" ? 150 : entity.kind === "finding" ? 220 : entity.kind === "anomaly" ? 285 : 125 + (index % 3) * 82;
    const ring = kindRing + (stableHash(`${entity.id}:orbit`, seed) % 17) - 8;
    const inclination = 0.1 + (stableHash(`${entity.id}:inclination`, seed) % 1_800) / 10_000;
    const phase = ((stableHash(`${entity.id}:phase`, seed) % 360) / 180) * Math.PI;
    const radius = entity.kind === "node" ? 11 : entity.kind === "artifact" ? 10 : entity.kind === "finding" ? 9 : entity.kind === "anomaly" ? 8 : 6;
    positions.push({ ...entity, x: Math.cos(angle) * ring, y: Math.sin(angle) * ring * 0.78, z: Math.sin(angle + phase) * ring * inclination, radius, angle });
  });
  return positions;
}

export function layoutScene(entities: SceneEntity[], seed: number, mode: SpaceMapMode = "galaxy", focusSystemId?: string): PositionedEntity[] {
  return mode === "system" ? layoutSystem(entities, seed, focusSystemId) : layoutGalaxy(entities, seed);
}
