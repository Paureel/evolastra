import type { FrontierField } from "./galaxyFrontier";
import type { PositionedEntity } from "./types";

export interface SpatialPoint {
  x: number;
  y: number;
  z: number;
}

export interface SpatialCamera {
  yaw: number;
  pitch: number;
  focalLength: number;
}

export interface ProjectedPoint {
  x: number;
  y: number;
  depth: number;
  scale: number;
}

export const DEFAULT_ORIENTATION = {
  galaxy: { yaw: -0.34, pitch: 0.58, focalLength: 1_850 },
  system: { yaw: -0.22, pitch: 0.48, focalLength: 950 },
} as const;

export function normalizeAngle(angle: number): number {
  const turn = Math.PI * 2;
  return ((angle + Math.PI) % turn + turn) % turn - Math.PI;
}

export function angleDegrees(angle: number): number {
  return Math.round(((normalizeAngle(angle) * 180) / Math.PI + 360) % 360);
}

export function projectPoint3D(point: SpatialPoint, camera: SpatialCamera): ProjectedPoint {
  const yawCos = Math.cos(camera.yaw);
  const yawSin = Math.sin(camera.yaw);
  const pitchCos = Math.cos(camera.pitch);
  const pitchSin = Math.sin(camera.pitch);
  const yawX = point.x * yawCos - point.y * yawSin;
  const yawY = point.x * yawSin + point.y * yawCos;
  const screenY = yawY * pitchCos - point.z * pitchSin;
  const depth = yawY * pitchSin + point.z * pitchCos;
  const denominator = Math.max(camera.focalLength * 0.32, camera.focalLength + depth);
  const scale = Math.max(0.42, Math.min(2.1, camera.focalLength / denominator));
  return { x: yawX * scale, y: screenY * scale, depth, scale };
}

export function projectLayout3D(layout: PositionedEntity[], camera: SpatialCamera): PositionedEntity[] {
  return layout
    .map((entity) => {
      const projected = projectPoint3D(entity, camera);
      return {
        ...entity,
        x: projected.x,
        y: projected.y,
        radius: Math.max(2.2, entity.radius * projected.scale),
        depth: projected.depth,
      };
    })
    .sort((left, right) => (right.depth ?? 0) - (left.depth ?? 0));
}

export function projectFrontier3D(frontier: FrontierField, camera: SpatialCamera): FrontierField {
  return {
    lanes: frontier.lanes,
    systems: frontier.systems.map((system) => {
      const projected = projectPoint3D(system, camera);
      return {
        ...system,
        x: projected.x,
        y: projected.y,
        radius: Math.max(0.9, system.radius * projected.scale),
        depth: projected.depth,
      };
    }),
  };
}
