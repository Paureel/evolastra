import type { PositionedEntity, SceneEntity, SpaceMapMode } from "./types";

export function stableHash(value: string, seed = 0): number {
  let hash = (2166136261 ^ seed) >>> 0;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export interface StableGalaxyPosition {
  x: number;
  y: number;
  z: number;
  angle: number;
}

export type GalaxyPositionRegistry = Map<string, StableGalaxyPosition>;

function isGalaxySystem(entity: PositionedEntity): boolean {
  return entity.kind === "home" || entity.kind === "node";
}

/**
 * Keeps coordinates already issued to galaxy systems immutable for the life of
 * a run projection. New systems inherit the best-fit coordinate frame of the
 * visible anchors, so semantic layout can expand without moving prior systems.
 */
export function stabilizeGalaxyLayout(
  nextLayout: PositionedEntity[],
  registry: GalaxyPositionRegistry,
): PositionedEntity[] {
  const rawSystems = new Map(
    nextLayout.filter(isGalaxySystem).map((entity) => [entity.id, entity]),
  );
  const anchors = [...rawSystems.values()].flatMap((entity) => {
    const stable = registry.get(entity.id);
    return stable ? [{ raw: entity, stable }] : [];
  });

  const rawCenter = anchors.length
    ? anchors.reduce((center, anchor) => ({
        x: center.x + anchor.raw.x / anchors.length,
        y: center.y + anchor.raw.y / anchors.length,
        z: center.z + anchor.raw.z / anchors.length,
      }), { x: 0, y: 0, z: 0 })
    : { x: 0, y: 0, z: 0 };
  const stableCenter = anchors.length
    ? anchors.reduce((center, anchor) => ({
        x: center.x + anchor.stable.x / anchors.length,
        y: center.y + anchor.stable.y / anchors.length,
        z: center.z + anchor.stable.z / anchors.length,
      }), { x: 0, y: 0, z: 0 })
    : { x: 0, y: 0, z: 0 };

  let scaleCos = 1;
  let scaleSin = 0;
  if (anchors.length > 1) {
    let dot = 0;
    let cross = 0;
    let rawMagnitude = 0;
    for (const anchor of anchors) {
      const rawX = anchor.raw.x - rawCenter.x;
      const rawY = anchor.raw.y - rawCenter.y;
      const stableX = anchor.stable.x - stableCenter.x;
      const stableY = anchor.stable.y - stableCenter.y;
      dot += rawX * stableX + rawY * stableY;
      cross += rawX * stableY - rawY * stableX;
      rawMagnitude += rawX * rawX + rawY * rawY;
    }
    if (rawMagnitude > 1e-6) {
      scaleCos = dot / rawMagnitude;
      scaleSin = cross / rawMagnitude;
    }
  }

  const align = (entity: PositionedEntity): StableGalaxyPosition => {
    if (!anchors.length) {
      return { x: entity.x, y: entity.y, z: entity.z, angle: entity.angle };
    }
    const rawX = entity.x - rawCenter.x;
    const rawY = entity.y - rawCenter.y;
    const x = stableCenter.x + scaleCos * rawX - scaleSin * rawY;
    const y = stableCenter.y + scaleSin * rawX + scaleCos * rawY;
    return {
      x,
      y,
      z: stableCenter.z + entity.z - rawCenter.z,
      angle: Math.atan2(y, x),
    };
  };

  const stableSystems = new Map<string, PositionedEntity>();
  for (const entity of rawSystems.values()) {
    const position = registry.get(entity.id) ?? align(entity);
    if (!registry.has(entity.id)) registry.set(entity.id, position);
    stableSystems.set(entity.id, { ...entity, ...position });
  }

  return nextLayout.map((entity) => {
    const stableSystem = stableSystems.get(entity.id);
    if (stableSystem) return stableSystem;
    if (entity.kind !== "agent" || !entity.parentId) return entity;
    const rawParent = rawSystems.get(entity.parentId);
    const stableParent = stableSystems.get(entity.parentId);
    if (!rawParent || !stableParent) return entity;
    const x = stableParent.x + entity.x - rawParent.x;
    const y = stableParent.y + entity.y - rawParent.y;
    return {
      ...entity,
      x,
      y,
      z: stableParent.z + entity.z - rawParent.z,
      angle: Math.atan2(stableParent.y - y, stableParent.x - x),
    };
  });
}

function layoutGalaxy(entities: SceneEntity[], seed: number): PositionedEntity[] {
  const positions = new Map<string, PositionedEntity>();
  const home = entities.find((entity) => entity.kind === "home");
  if (home) {
    positions.set(home.id, { ...home, x: -18, y: 12, z: 0, radius: 17, angle: 0 });
  }
  const nodes = entities.filter((entity) => entity.kind === "node");

  nodes.forEach((entity) => {
    const parent = entity.parentId ? positions.get(entity.parentId) : undefined;
    if (parent) {
      const slot = stableHash(entity.id, seed) % 360;
      const angle = (slot / 180) * Math.PI;
      const distance = 64 + stableHash(`${entity.id}:branch`, seed) % 38;
      positions.set(entity.id, {
        ...entity,
        x: parent.x + Math.cos(angle) * distance,
        y: parent.y + Math.sin(angle) * distance * 0.72,
        z: parent.z + ((stableHash(`${entity.id}:depth`, seed) % 10_000) / 10_000 - 0.5) * 36,
        radius: 8 + Math.min(4, (entity.progress ?? 0) * 4),
        angle,
      });
      return;
    }
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
