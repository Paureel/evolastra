import { useEffect, useMemo, useRef, useState } from "react";
import { syncCanvasBackingStore } from "../canvasBackingStore";
import { createFrontierField, frontierClaimedBridges, frontierSystemCount, galaxyCameraZoom, stellarProfilesFor, territoryGrowth, type FrontierBridge, type FrontierField, type StellarProfile } from "../galaxyFrontier";
import { stableHash } from "../layout";
import { connectedHyperlanes, type ConnectedLane } from "../mapGraph";
import { angleDegrees, DEFAULT_ORIENTATION, normalizeAngle, projectFrontier3D, projectLayout3D, projectPoint3D, type SpatialCamera } from "../spatial";
import type { EdgeEntity, PositionedEntity, SceneEntity, SpaceMapMode } from "../types";

interface GalaxyCanvasProps {
  entities: SceneEntity[];
  edges: EdgeEntity[];
  seed: number;
  mode: SpaceMapMode;
  focusSystemId: string;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onOpenSystem: (id: string) => void;
  onOpenShipyard: () => void;
  shipyardEnabled: boolean;
  multiplayerClaims: Record<string, string>;
  onBackToGalaxy: () => void;
  animated: boolean;
  reducedMotion: boolean;
  highContrast: boolean;
}

interface Camera extends SpatialCamera { x: number; y: number; zoom: number }

const COLORS = {
  void: "#02050b",
  text: "#edf7f4",
  muted: "#7899a0",
  gold: "#ffd36a",
  cyan: "#71e6e1",
  teal: "#2d9298",
  violet: "#9c72e8",
  coral: "#ff716c",
};

const PLANET_PALETTES = [
  ["#d9f4ec", "#55bdb7", "#102f42"],
  ["#ffe4a2", "#b46d36", "#321c25"],
  ["#e2dcff", "#8272c5", "#231b45"],
  ["#d8ecc8", "#668b60", "#17242c"],
  ["#d9e7f4", "#668ca8", "#14263b"],
] as const;

function randomUnit(seed: number, index: number, salt: string): number {
  return (stableHash(`${seed}:${salt}:${index}`) % 10_000) / 10_000;
}

function rgba(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red},${green},${blue},${alpha})`;
}

function wrap(value: number, limit: number): number {
  return ((value % limit) + limit) % limit;
}

function statusColor(status: string, contrast: boolean): string {
  if (status === "failed" || status === "disputed") return contrast ? "#ffaaa0" : COLORS.coral;
  if (["completed", "validated", "promoted", "resolved", "approved"].includes(status)) return contrast ? "#b9ffff" : COLORS.cyan;
  if (status === "running") return contrast ? "#ffeaa0" : COLORS.gold;
  return contrast ? "#dfd0ff" : COLORS.violet;
}

function drawBackdrop(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  seed: number,
  mode: SpaceMapMode,
  highContrast: boolean,
  time: number,
  camera: Camera,
): void {
  const base = context.createRadialGradient(width * 0.52, height * 0.48, 0, width * 0.52, height * 0.48, Math.max(width, height) * 0.82);
  base.addColorStop(0, highContrast ? "#061019" : mode === "galaxy" ? "#071722" : "#0b1019");
  base.addColorStop(0.55, COLORS.void);
  base.addColorStop(1, "#010207");
  context.fillStyle = base;
  context.fillRect(0, 0, width, height);

  if (!highContrast) {
    context.save();
    context.globalCompositeOperation = "screen";
    const nebulaColors = mode === "galaxy"
      ? ["#155f6e", "#593a83", "#234d66", "#6b3f72"]
      : ["#7f5722", "#155b66", "#40346f", "#7a4927"];
    for (let index = 0; index < 18; index += 1) {
      const drift = time ? Math.sin(time * 0.000035 + index * 1.7) * 18 : 0;
      const x = randomUnit(seed, index, `${mode}:nebula-x`) * width * 1.25 - width * 0.12 + drift;
      const y = randomUnit(seed, index, `${mode}:nebula-y`) * height * 1.2 - height * 0.1 + Math.cos(time * 0.000024 + index) * 10;
      const radius = Math.max(width, height) * (0.13 + randomUnit(seed, index, "nebula-radius") * 0.2);
      const color = nebulaColors[index % nebulaColors.length];
      context.save();
      context.translate(x, y);
      context.rotate(randomUnit(seed, index, "nebula-rotation") * Math.PI);
      context.scale(1.7, 0.58 + randomUnit(seed, index, "nebula-scale") * 0.34);
      const mist = context.createRadialGradient(0, 0, 0, 0, 0, radius);
      mist.addColorStop(0, rgba(color, 0.11));
      mist.addColorStop(0.38, rgba(color, 0.06));
      mist.addColorStop(0.72, rgba(color, 0.022));
      mist.addColorStop(1, "rgba(0,0,0,0)");
      context.fillStyle = mist;
      context.fillRect(-radius, -radius, radius * 2, radius * 2);
      context.restore();
    }
    context.restore();
  }

  const fieldWidth = width + 160;
  const fieldHeight = height + 160;
  const layers = [
    { count: 130, parallax: 0.025, size: 0.55, alpha: 0.36 },
    { count: 105, parallax: 0.055, size: 0.9, alpha: 0.56 },
    { count: 52, parallax: 0.11, size: 1.35, alpha: 0.78 },
  ];
  layers.forEach((layer, layerIndex) => {
    for (let index = 0; index < layer.count; index += 1) {
      const x = wrap(randomUnit(seed + layerIndex * 97, index, `${mode}:star-x`) * fieldWidth + camera.x * layer.parallax + time * layer.parallax * 0.002, fieldWidth) - 80;
      const y = wrap(randomUnit(seed + layerIndex * 131, index, `${mode}:star-y`) * fieldHeight + camera.y * layer.parallax, fieldHeight) - 80;
      const pulse = time ? Math.sin(time * (0.00045 + layerIndex * 0.00015) + index * 2.19) * 0.18 : 0;
      const alpha = Math.max(0.16, layer.alpha + pulse);
      const warm = index % 19 === 0;
      const color = warm ? `rgba(255,218,139,${alpha})` : `rgba(210,239,244,${alpha})`;
      const size = layer.size + randomUnit(seed, index, `star-size-${layerIndex}`) * layer.size;
      context.fillStyle = color;
      context.fillRect(x, y, size, size);
      if (layerIndex === 2 && index % 13 === 0) {
        context.strokeStyle = rgba(warm ? COLORS.gold : COLORS.cyan, alpha * 0.45);
        context.lineWidth = 0.55;
        context.beginPath();
        context.moveTo(x - size * 3, y + size * 0.5);
        context.lineTo(x + size * 4, y + size * 0.5);
        context.moveTo(x + size * 0.5, y - size * 3);
        context.lineTo(x + size * 0.5, y + size * 4);
        context.stroke();
      }
    }
  });

  if (time > 0 && !highContrast) {
    const cycle = time % 13_000;
    if (cycle < 1_100) {
      const progress = cycle / 1_100;
      const startX = width * (0.12 + randomUnit(seed, 0, "meteor-x") * 0.35);
      const startY = height * (0.08 + randomUnit(seed, 0, "meteor-y") * 0.26);
      const x = startX + progress * width * 0.42;
      const y = startY + progress * height * 0.24;
      const trail = context.createLinearGradient(x - 92, y - 48, x, y);
      trail.addColorStop(0, "rgba(113,230,225,0)");
      trail.addColorStop(0.8, "rgba(113,230,225,.28)");
      trail.addColorStop(1, "rgba(255,255,255,.9)");
      context.strokeStyle = trail;
      context.lineWidth = 1.2;
      context.beginPath();
      context.moveTo(x - 92, y - 48);
      context.lineTo(x, y);
      context.stroke();
    }
  }
}

function drawGalaxyField(context: CanvasRenderingContext2D, seed: number, zoom: number, time: number, highContrast: boolean, camera: SpatialCamera): void {
  context.save();
  context.globalCompositeOperation = "screen";
  context.scale(1, 0.68);
  const core = context.createRadialGradient(0, 0, 5, 0, 0, 980);
  core.addColorStop(0, highContrast ? "rgba(255,255,255,.08)" : "rgba(255,211,106,.11)");
  core.addColorStop(0.18, highContrast ? "rgba(185,255,255,.035)" : "rgba(113,230,225,.055)");
  core.addColorStop(0.6, highContrast ? "rgba(255,255,255,.012)" : "rgba(115,77,177,.04)");
  core.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = core;
  context.beginPath();
  context.arc(0, 0, 980, 0, Math.PI * 2);
  context.fill();
  context.restore();

  const rotation = time * 0.0000035;
  context.save();
  context.globalCompositeOperation = "screen";
  for (let index = 0; index < 760; index += 1) {
    const arm = index % 4;
    const radial = 75 + Math.sqrt(randomUnit(seed, index, "spiral-radius")) * 860;
    const jitter = (randomUnit(seed, index, "spiral-jitter") - 0.5) * (0.26 + radial / 1800);
    const angle = arm * (Math.PI / 2) + radial * 0.0092 + jitter + rotation;
    const projected = projectPoint3D({
      x: Math.cos(angle) * radial,
      y: Math.sin(angle) * radial * 0.67,
      z: (randomUnit(seed, index, "spiral-depth") - 0.5) * 120,
    }, camera);
    const size = (0.34 + randomUnit(seed, index, "spiral-size") * 1.05) / zoom;
    const alpha = 0.1 + randomUnit(seed, index, "spiral-alpha") * 0.32;
    const color = index % 29 === 0 ? COLORS.gold : index % 5 === 0 ? COLORS.violet : COLORS.cyan;
    context.fillStyle = rgba(color, highContrast ? alpha * 0.38 : alpha);
    context.fillRect(projected.x, projected.y, size * projected.scale, size * projected.scale);
  }
  context.restore();
}

function traceProjectedRing(
  context: CanvasRenderingContext2D,
  radius: number,
  camera: SpatialCamera,
  yScale: number,
  inclination = 0,
  phase = 0,
  start = 0,
  end = Math.PI * 2,
): void {
  const steps = Math.max(8, Math.ceil(((end - start) / (Math.PI * 2)) * 96));
  context.beginPath();
  for (let index = 0; index <= steps; index += 1) {
    const angle = start + ((end - start) * index) / steps;
    const projected = projectPoint3D({
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius * yScale,
      z: Math.sin(angle + phase) * radius * inclination,
    }, camera);
    if (index === 0) context.moveTo(projected.x, projected.y);
    else context.lineTo(projected.x, projected.y);
  }
}

function drawGalaxyPlane(context: CanvasRenderingContext2D, camera: SpatialCamera, zoom: number): void {
  context.save();
  context.strokeStyle = "rgba(91,154,161,.10)";
  context.lineWidth = 0.65 / zoom;
  [240, 480, 720, 960, 1_180].forEach((radius, index) => {
    traceProjectedRing(context, radius, camera, 0.67);
    context.setLineDash(index % 2 ? [3 / zoom, 8 / zoom] : []);
    context.stroke();
  });
  context.setLineDash([]);
  for (let index = 0; index < 12; index += 1) {
    const angle = (index / 12) * Math.PI * 2;
    const inner = projectPoint3D({ x: Math.cos(angle) * 120, y: Math.sin(angle) * 120 * 0.67, z: 0 }, camera);
    const outer = projectPoint3D({ x: Math.cos(angle) * 1_180, y: Math.sin(angle) * 1_180 * 0.67, z: 0 }, camera);
    context.beginPath();
    context.moveTo(inner.x, inner.y);
    context.lineTo(outer.x, outer.y);
    context.stroke();
  }
  context.restore();
}

function drawFrontierNetwork(
  context: CanvasRenderingContext2D,
  frontier: FrontierField,
  claimed: PositionedEntity[],
  bridges: FrontierBridge[],
  zoom: number,
  time: number,
  highContrast: boolean,
): void {
  context.save();
  context.lineWidth = 0.6 / zoom;
  context.strokeStyle = highContrast ? "rgba(184,201,207,.24)" : "rgba(126,145,151,.13)";
  context.beginPath();
  frontier.lanes.forEach((lane) => {
    const source = frontier.systems[lane.source];
    const target = frontier.systems[lane.target];
    context.moveTo(source.x, source.y);
    context.lineTo(target.x, target.y);
  });
  context.stroke();

  const claimedSystems = new Map(claimed.filter((entity) => entity.kind === "home" || entity.kind === "node").map((entity) => [entity.id, entity]));
  context.strokeStyle = highContrast ? "rgba(205,218,221,.32)" : "rgba(145,164,169,.22)";
  context.lineWidth = 0.95 / zoom;
  bridges.forEach((bridge) => {
    const system = claimedSystems.get(bridge.claimedId);
    const nearest = frontier.systems[bridge.frontier];
    if (!system || !nearest) return;
    context.beginPath();
    context.moveTo(system.x, system.y);
    context.lineTo(nearest.x, nearest.y);
    context.stroke();
  });

  context.globalCompositeOperation = "screen";
  frontier.systems.forEach((system, index) => {
    const pulse = time ? Math.sin(time * 0.0011 + index * 1.73) * 0.12 : 0;
    if (system.singularity) {
      context.strokeStyle = highContrast ? "rgba(210,218,224,.72)" : "rgba(139,147,156,.52)";
      context.lineWidth = 0.75 / zoom;
      context.beginPath();
      context.ellipse(system.x, system.y, (system.radius + 2.6) / zoom, (system.radius + 0.7) / zoom, index * 0.31, 0, Math.PI * 2);
      context.stroke();
      context.globalCompositeOperation = "source-over";
      context.fillStyle = "rgba(0,0,0,.94)";
      context.beginPath();
      context.arc(system.x, system.y, Math.max(1.4, system.radius * 0.72) / zoom, 0, Math.PI * 2);
      context.fill();
      context.globalCompositeOperation = "screen";
      return;
    }
    const haloRadius = (system.radius * 3.2) / zoom;
    const halo = context.createRadialGradient(system.x, system.y, 0, system.x, system.y, haloRadius);
    halo.addColorStop(0, highContrast ? "rgba(241,246,247,.86)" : "rgba(181,194,197,.64)");
    halo.addColorStop(0.28, highContrast ? "rgba(185,201,205,.28)" : "rgba(129,145,150,.18)");
    halo.addColorStop(1, "rgba(0,0,0,0)");
    context.fillStyle = halo;
    context.beginPath();
    context.arc(system.x, system.y, haloRadius, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = highContrast ? `rgba(241,246,247,${0.84 + pulse})` : `rgba(164,177,181,${0.64 + pulse})`;
    context.beginPath();
    context.arc(system.x, system.y, system.radius / zoom, 0, Math.PI * 2);
    context.fill();
  });
  context.restore();
}

function drawSystemField(context: CanvasRenderingContext2D, seed: number, zoom: number, time: number, highContrast: boolean, camera: SpatialCamera): void {
  if (!highContrast) {
    const stellarFog = context.createRadialGradient(0, 0, 0, 0, 0, 460);
    stellarFog.addColorStop(0, "rgba(255,203,85,.09)");
    stellarFog.addColorStop(0.3, "rgba(38,100,102,.035)");
    stellarFog.addColorStop(0.72, "rgba(86,55,120,.025)");
    stellarFog.addColorStop(1, "rgba(0,0,0,0)");
    context.fillStyle = stellarFog;
    context.beginPath();
    context.arc(0, 0, 460, 0, Math.PI * 2);
    context.fill();
  }
  context.save();
  context.globalCompositeOperation = "screen";
  const rotation = time * 0.000006;
  for (let index = 0; index < 390; index += 1) {
    const angle = randomUnit(seed, index, "system-dust-angle") * Math.PI * 2 + rotation;
    const radius = 75 + Math.sqrt(randomUnit(seed, index, "system-dust-radius")) * 370;
    const spread = (randomUnit(seed, index, "system-dust-spread") - 0.5) * 34;
    const projected = projectPoint3D({
      x: Math.cos(angle) * (radius + spread),
      y: Math.sin(angle) * (radius + spread) * 0.78,
      z: (randomUnit(seed, index, "system-dust-depth") - 0.5) * 54,
    }, camera);
    const alpha = 0.08 + randomUnit(seed, index, "system-dust-alpha") * 0.3;
    context.fillStyle = index % 11 === 0 ? rgba(COLORS.gold, alpha) : rgba("#b5c9c5", alpha * 0.7);
    const size = (0.35 + randomUnit(seed, index, "system-dust-size") * 0.85) / zoom;
    context.fillRect(projected.x, projected.y, size * projected.scale, size * projected.scale);
  }
  context.restore();
}

function traceTerritory(context: CanvasRenderingContext2D, points: Array<{ x: number; y: number }>): void {
  const midpoint = (left: { x: number; y: number }, right: { x: number; y: number }) => ({ x: (left.x + right.x) / 2, y: (left.y + right.y) / 2 });
  const first = midpoint(points.at(-1)!, points[0]);
  context.beginPath();
  context.moveTo(first.x, first.y);
  points.forEach((point, index) => {
    const next = points[(index + 1) % points.length];
    const middle = midpoint(point, next);
    context.quadraticCurveTo(point.x, point.y, middle.x, middle.y);
  });
  context.closePath();
}

function drawTerritory(context: CanvasRenderingContext2D, layout: PositionedEntity[], zoom: number, time: number): void {
  const systems = layout.filter((entity) => entity.kind === "node").sort((left, right) => Math.atan2(left.y, left.x) - Math.atan2(right.y, right.x));
  if (systems.length < 3) return;
  const { scale: growth, padding: influencePadding } = territoryGrowth(systems.length);
  const points = systems.map((entity) => {
    const angle = Math.atan2(entity.y, entity.x);
    return {
      x: entity.x * growth + Math.cos(angle) * influencePadding,
      y: entity.y * growth + Math.sin(angle) * influencePadding,
    };
  });
  context.save();
  traceTerritory(context, points);
  const territory = context.createLinearGradient(-360, -240, 370, 260);
  territory.addColorStop(0, "rgba(45,146,152,.08)");
  territory.addColorStop(0.48, "rgba(79,58,125,.15)");
  territory.addColorStop(1, "rgba(156,114,232,.07)");
  context.fillStyle = territory;
  context.fill();
  context.save();
  context.clip();
  systems.forEach((system) => {
    const influence = context.createRadialGradient(system.x, system.y, 0, system.x, system.y, 118);
    influence.addColorStop(0, rgba(statusColor(String(system.status), false), 0.085));
    influence.addColorStop(1, "rgba(0,0,0,0)");
    context.fillStyle = influence;
    context.fillRect(system.x - 120, system.y - 120, 240, 240);
  });
  context.restore();
  traceTerritory(context, points);
  context.strokeStyle = "rgba(156,114,232,.24)";
  context.lineWidth = 9 / zoom;
  context.shadowColor = COLORS.violet;
  context.shadowBlur = 18 / zoom;
  context.stroke();
  traceTerritory(context, points);
  context.strokeStyle = "rgba(184,137,255,.88)";
  context.lineWidth = 1.25 / zoom;
  context.setLineDash([8 / zoom, 5 / zoom]);
  context.lineDashOffset = -(time * 0.012) / zoom;
  context.stroke();
  traceTerritory(context, points);
  context.strokeStyle = "rgba(113,230,225,.13)";
  context.lineWidth = 0.7 / zoom;
  context.setLineDash([]);
  context.save();
  context.translate(Math.sin(time * 0.0002) * 1.5, Math.cos(time * 0.0002) * 1.5);
  context.stroke();
  context.restore();
  context.restore();
}

function claimColor(color: string, alpha: string): string {
  return /^#[0-9a-f]{6}$/i.test(color) ? `${color}${alpha}` : color;
}

function drawMultiplayerTerritories(
  context: CanvasRenderingContext2D,
  layout: PositionedEntity[],
  claims: Record<string, string>,
  zoom: number,
  time: number,
): void {
  const groups = new Map<string, PositionedEntity[]>();
  layout.filter((entity) => entity.kind === "node" && claims[entity.id]).forEach((entity) => {
    const color = claims[entity.id].toUpperCase();
    groups.set(color, [...(groups.get(color) ?? []), entity]);
  });
  groups.forEach((systems, color) => {
    if (!systems.length) return;
    const center = systems.reduce((sum, system) => ({ x: sum.x + system.x, y: sum.y + system.y }), { x: 0, y: 0 });
    center.x /= systems.length;
    center.y /= systems.length;
    systems.sort((left, right) => Math.atan2(left.y - center.y, left.x - center.x) - Math.atan2(right.y - center.y, right.x - center.x));
    context.save();
    context.lineCap = "round";
    context.lineJoin = "round";
    if (systems.length === 1) {
      context.beginPath();
      context.arc(systems[0].x, systems[0].y, 58 / zoom, 0, Math.PI * 2);
      context.fillStyle = claimColor(color, "19");
      context.fill();
    } else {
      context.beginPath();
      context.moveTo(systems[0].x, systems[0].y);
      systems.slice(1).forEach((system) => context.lineTo(system.x, system.y));
      if (systems.length > 2) context.closePath();
      context.strokeStyle = claimColor(color, "18");
      context.lineWidth = 86 / zoom;
      context.stroke();
      context.strokeStyle = claimColor(color, "D0");
      context.lineWidth = 1.4 / zoom;
      context.setLineDash([10 / zoom, 7 / zoom]);
      context.lineDashOffset = -(time * 0.009) / zoom;
      context.shadowColor = color;
      context.shadowBlur = 13 / zoom;
      context.stroke();
    }
    systems.forEach((system) => {
      const influence = context.createRadialGradient(system.x, system.y, 0, system.x, system.y, 72 / zoom);
      influence.addColorStop(0, claimColor(color, "24"));
      influence.addColorStop(1, claimColor(color, "00"));
      context.fillStyle = influence;
      context.fillRect(system.x - 74 / zoom, system.y - 74 / zoom, 148 / zoom, 148 / zoom);
    });
    context.restore();
  });
}

function drawOrbits(context: CanvasRenderingContext2D, seed: number, zoom: number, time: number, camera: SpatialCamera): void {
  context.save();
  const radii = [92, 150, 220, 285, 350];
  radii.forEach((radius, index) => {
    const inclination = 0.1 + index * 0.035;
    const phase = index * 1.17;
    traceProjectedRing(context, radius, camera, 0.78, inclination, phase);
    context.strokeStyle = index === 3 ? "rgba(113,230,225,.20)" : "rgba(126,166,174,.13)";
    context.lineWidth = (index === 3 ? 1.05 : 0.72) / zoom;
    context.setLineDash(index % 2 ? [2 / zoom, 5 / zoom] : []);
    context.stroke();
    const head = time * (0.000018 + index * 0.000002) + index * 1.18;
    traceProjectedRing(context, radius, camera, 0.78, inclination, phase, head, head + 0.34);
    context.strokeStyle = index === 3 ? "rgba(113,230,225,.58)" : "rgba(255,211,106,.28)";
    context.lineWidth = 1.2 / zoom;
    context.setLineDash([]);
    context.shadowColor = index === 3 ? COLORS.cyan : COLORS.gold;
    context.shadowBlur = 5 / zoom;
    context.stroke();
  });
  context.shadowBlur = 0;
  const beltRotation = time * 0.000009;
  for (let index = 0; index < 420; index += 1) {
    const angle = randomUnit(seed, index, "belt-angle") * Math.PI * 2 + beltRotation;
    const radius = 318 + (randomUnit(seed, index, "belt-radius") - 0.5) * 34;
    const projected = projectPoint3D({
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius * 0.78,
      z: Math.sin(angle + 1.8) * radius * 0.16 + (randomUnit(seed, index, "belt-depth") - 0.5) * 12,
    }, camera);
    const twinkle = 0.42 + Math.sin(time * 0.001 + index) * 0.13;
    const size = 0.4 + randomUnit(seed, index, "belt-size") * 1.1;
    context.fillStyle = index % 13 === 0 ? `rgba(255,211,106,${twinkle})` : "rgba(190,205,197,.28)";
    context.fillRect(projected.x, projected.y, (size * projected.scale) / zoom, (size * projected.scale) / zoom);
  }
  context.restore();
}

function quadraticPoint(source: PositionedEntity, target: PositionedEntity, bend: number, t: number): { x: number; y: number } {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const controlX = (source.x + target.x) / 2 - (dy / length) * bend;
  const controlY = (source.y + target.y) / 2 + (dx / length) * bend;
  const inverse = 1 - t;
  return {
    x: inverse * inverse * source.x + 2 * inverse * t * controlX + t * t * target.x,
    y: inverse * inverse * source.y + 2 * inverse * t * controlY + t * t * target.y,
  };
}

function traceLane(context: CanvasRenderingContext2D, source: PositionedEntity, target: PositionedEntity, bend: number): void {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  context.beginPath();
  context.moveTo(source.x, source.y);
  context.quadraticCurveTo((source.x + target.x) / 2 - (dy / length) * bend, (source.y + target.y) / 2 + (dx / length) * bend, target.x, target.y);
}

function drawHyperlanes(context: CanvasRenderingContext2D, layout: PositionedEntity[], topology: ConnectedLane[], zoom: number, time: number): void {
  const lookup = new Map(layout.map((entity) => [entity.id, entity]));
  const lanes = topology.flatMap((lane) => {
    const source = lookup.get(lane.sourceId);
    const target = lookup.get(lane.targetId);
    return source && target ? [{ ...lane, source, target }] : [];
  });
  context.save();
  for (const lane of lanes) {
    const keyHash = stableHash(lane.key);
    const bend = ((keyHash % 31) - 15) * 0.42;
    const laneColor = lane.type === "contradicts" ? COLORS.coral : lane.type === "supports" ? COLORS.cyan : "#70bfc3";
    traceLane(context, lane.source, lane.target, bend);
    context.strokeStyle = rgba(laneColor, 0.09);
    context.lineWidth = (lane.type === "supports" ? 7 : 5) / zoom;
    context.shadowColor = laneColor;
    context.shadowBlur = 8 / zoom;
    context.stroke();
    traceLane(context, lane.source, lane.target, bend);
    context.strokeStyle = rgba(laneColor, lane.type === "contradicts" ? 0.72 : 0.44);
    context.lineWidth = (lane.type === "supports" ? 1.55 : 0.85) / zoom;
    context.setLineDash(lane.synthetic ? [] : lane.type === "produced" ? [4 / zoom, 5 / zoom] : [1 / zoom, 3 / zoom]);
    context.lineDashOffset = -(time * (0.018 + (keyHash % 5) * 0.002)) / zoom;
    context.stroke();
    context.setLineDash([]);
    const packetProgress = wrap(time * (0.000075 + (keyHash % 7) * 0.000005) + (keyHash % 100) / 100, 1);
    const packet = quadraticPoint(lane.source, lane.target, bend, packetProgress);
    context.fillStyle = "#eaffff";
    context.shadowColor = laneColor;
    context.shadowBlur = 10 / zoom;
    context.beginPath();
    context.arc(packet.x, packet.y, 1.5 / zoom, 0, Math.PI * 2);
    context.fill();
  }
  context.restore();
}

function drawAgentAssignments(context: CanvasRenderingContext2D, layout: PositionedEntity[], zoom: number, time: number): void {
  const lookup = new Map(layout.map((entity) => [entity.id, entity]));
  const agents = layout.filter((entity) => entity.kind === "agent" && entity.parentId && lookup.has(entity.parentId));
  context.save();
  for (const agent of agents) {
    const system = lookup.get(agent.parentId!);
    if (!system) continue;
    const active = String(agent.status) === "running";
    const color = active ? COLORS.gold : COLORS.cyan;
    const dx = agent.x - system.x;
    const dy = agent.y - system.y;
    const length = Math.max(1, Math.hypot(dx, dy));
    const startX = system.x + (dx / length) * (system.radius + 6 / zoom);
    const startY = system.y + (dy / length) * (system.radius + 6 / zoom);
    const endX = agent.x - (dx / length) * (agent.radius + 5 / zoom);
    const endY = agent.y - (dy / length) * (agent.radius + 5 / zoom);

    context.beginPath();
    context.moveTo(startX, startY);
    context.lineTo(endX, endY);
    context.strokeStyle = rgba(color, active ? 0.78 : 0.42);
    context.lineWidth = (active ? 1.4 : 0.9) / zoom;
    context.setLineDash([3 / zoom, 4 / zoom]);
    context.lineDashOffset = active ? -time * 0.02 / zoom : 0;
    context.shadowColor = color;
    context.shadowBlur = active ? 7 / zoom : 3 / zoom;
    context.stroke();
    context.setLineDash([]);

    const packetProgress = active ? wrap(time * 0.00018 + (stableHash(agent.id) % 100) / 100, 1) : 0.72;
    const packetX = startX + (endX - startX) * packetProgress;
    const packetY = startY + (endY - startY) * packetProgress;
    context.fillStyle = color;
    context.beginPath();
    context.arc(packetX, packetY, (active ? 1.8 : 1.2) / zoom, 0, Math.PI * 2);
    context.fill();

    context.beginPath();
    context.arc(system.x, system.y, system.radius + 8 / zoom, agent.angle - 0.42, agent.angle + 0.42);
    context.strokeStyle = rgba(color, active ? 0.72 : 0.34);
    context.lineWidth = 1.3 / zoom;
    context.stroke();
  }
  context.restore();
}

function drawGalaxySystemStar(
  context: CanvasRenderingContext2D,
  entity: PositionedEntity,
  status: string,
  profile: StellarProfile,
  ordinal: number,
  pulse: number,
  zoom: number,
  time: number,
): void {
  const radius = entity.radius * (entity.kind === "home" ? 0.86 : 0.92);
  const statusAccent = statusColor(status, false);
  context.save();

  if (profile.kind === "black-hole") {
    const rotation = entity.angle * 0.22 + time * 0.000055;
    context.translate(entity.x, entity.y);
    context.rotate(rotation);
    const accretion = context.createLinearGradient(-radius * 3.2, 0, radius * 3.2, 0);
    accretion.addColorStop(0, "rgba(83,121,255,0)");
    accretion.addColorStop(0.22, "rgba(105,147,255,.58)");
    accretion.addColorStop(0.48, "rgba(255,244,210,.96)");
    accretion.addColorStop(0.66, "rgba(219,116,255,.72)");
    accretion.addColorStop(1, "rgba(106,56,190,0)");
    context.strokeStyle = accretion;
    context.lineWidth = (3.2 + pulse * 2) / zoom;
    context.shadowColor = profile.halo;
    context.shadowBlur = 15 / zoom;
    context.beginPath();
    context.ellipse(0, 0, radius * 2.8, radius * 0.72, 0, 0, Math.PI * 2);
    context.stroke();
    context.strokeStyle = "rgba(214,232,255,.58)";
    context.lineWidth = 0.9 / zoom;
    context.beginPath();
    context.ellipse(0, 0, radius * 1.45, radius * 1.2, 0, 0, Math.PI * 2);
    context.stroke();
    context.globalCompositeOperation = "source-over";
    context.fillStyle = "#000006";
    context.shadowColor = "rgba(0,0,0,.95)";
    context.shadowBlur = 10 / zoom;
    context.beginPath();
    context.arc(0, 0, radius * 0.98, 0, Math.PI * 2);
    context.fill();
    context.shadowBlur = 0;
    context.strokeStyle = "rgba(226,238,255,.9)";
    context.lineWidth = 0.75 / zoom;
    context.beginPath();
    context.arc(0, 0, radius * 1.1, 0, Math.PI * 2);
    context.stroke();
    context.rotate(-rotation);
    context.translate(-entity.x, -entity.y);
  } else if (profile.kind === "pulsar") {
    const rotation = time * 0.0002 + entity.angle * 0.16;
    const beamLength = radius * 6.8;
    context.translate(entity.x, entity.y);
    context.rotate(rotation);
    context.globalCompositeOperation = "screen";
    const beam = context.createLinearGradient(-beamLength, 0, beamLength, 0);
    beam.addColorStop(0, "rgba(77,114,255,0)");
    beam.addColorStop(0.35, rgba(profile.halo, 0.24));
    beam.addColorStop(0.49, rgba(profile.core, 0.9));
    beam.addColorStop(0.51, rgba(profile.core, 0.9));
    beam.addColorStop(0.65, rgba(profile.halo, 0.24));
    beam.addColorStop(1, "rgba(77,114,255,0)");
    context.strokeStyle = beam;
    context.lineWidth = (2.2 + pulse * 2) / zoom;
    context.shadowColor = profile.body;
    context.shadowBlur = 12 / zoom;
    context.beginPath();
    context.moveTo(-beamLength, 0);
    context.lineTo(beamLength, 0);
    context.stroke();
    context.strokeStyle = rgba(profile.core, 0.55);
    context.lineWidth = 0.7 / zoom;
    context.beginPath();
    context.moveTo(-beamLength * 0.75, 0);
    context.lineTo(beamLength * 0.75, 0);
    context.stroke();
    const pulsarHalo = context.createRadialGradient(0, 0, 0, 0, 0, radius * (4.5 + pulse));
    pulsarHalo.addColorStop(0, rgba(profile.core, 1));
    pulsarHalo.addColorStop(0.18, rgba(profile.body, 0.82));
    pulsarHalo.addColorStop(0.5, rgba(profile.halo, 0.2));
    pulsarHalo.addColorStop(1, "rgba(0,0,0,0)");
    context.fillStyle = pulsarHalo;
    context.beginPath();
    context.arc(0, 0, radius * (4.5 + pulse), 0, Math.PI * 2);
    context.fill();
    context.globalCompositeOperation = "source-over";
    context.fillStyle = profile.core;
    context.shadowColor = profile.body;
    context.shadowBlur = 16 / zoom;
    context.beginPath();
    context.arc(0, 0, radius * 0.7, 0, Math.PI * 2);
    context.fill();
    context.shadowBlur = 0;
    context.strokeStyle = rgba(profile.body, 0.75);
    context.lineWidth = 0.8 / zoom;
    context.beginPath();
    context.ellipse(0, 0, radius * 1.6, radius * 0.65, -rotation * 1.8, 0, Math.PI * 2);
    context.stroke();
    context.rotate(-rotation);
    context.translate(-entity.x, -entity.y);
  } else {
    const haloRadius = radius * (4.2 + pulse);
    context.globalCompositeOperation = "screen";
    const halo = context.createRadialGradient(entity.x, entity.y, 0, entity.x, entity.y, haloRadius);
    halo.addColorStop(0, rgba(profile.core, 1));
    halo.addColorStop(0.12, rgba(profile.body, 0.94));
    halo.addColorStop(0.38, rgba(profile.halo, 0.34));
    halo.addColorStop(0.72, rgba(profile.halo, 0.08));
    halo.addColorStop(1, "rgba(0,0,0,0)");
    context.fillStyle = halo;
    context.beginPath();
    context.arc(entity.x, entity.y, haloRadius, 0, Math.PI * 2);
    context.fill();
    const rayLength = radius * (2.5 + pulse);
    context.strokeStyle = rgba(profile.body, 0.34);
    context.lineWidth = 0.7 / zoom;
    context.beginPath();
    context.moveTo(entity.x - rayLength, entity.y);
    context.lineTo(entity.x + rayLength, entity.y);
    context.moveTo(entity.x, entity.y - rayLength);
    context.lineTo(entity.x, entity.y + rayLength);
    context.stroke();
    const body = context.createRadialGradient(entity.x - radius * 0.18, entity.y - radius * 0.2, 0, entity.x, entity.y, radius * 1.08);
    body.addColorStop(0, profile.core);
    body.addColorStop(0.48, profile.body);
    body.addColorStop(1, profile.halo);
    context.fillStyle = body;
    context.shadowColor = profile.body;
    context.shadowBlur = 13 / zoom;
    context.beginPath();
    context.arc(entity.x, entity.y, radius, 0, Math.PI * 2);
    context.fill();
    context.shadowBlur = 0;
    context.strokeStyle = rgba(profile.core, 0.64);
    context.lineWidth = 0.7 / zoom;
    for (let arc = 0; arc < 2; arc += 1) {
      const start = time * (0.00011 + arc * 0.000025) + ordinal * 0.8 + arc * Math.PI;
      context.beginPath();
      context.arc(entity.x, entity.y, radius + (3 + arc * 3) / zoom, start, start + 1.1);
      context.stroke();
    }
  }

  context.globalCompositeOperation = "source-over";
  context.strokeStyle = rgba(statusAccent, 0.72);
  context.lineWidth = 0.85 / zoom;
  context.setLineDash([2 / zoom, 3 / zoom]);
  context.beginPath();
  context.arc(entity.x, entity.y, radius + 8 / zoom, time * 0.0002, time * 0.0002 + Math.PI * 1.55);
  context.stroke();
  context.restore();
}

function drawStar(context: CanvasRenderingContext2D, entity: PositionedEntity, color: string, pulse: number, zoom: number, time: number): void {
  const outerRadius = entity.radius * (4.9 + pulse);
  context.save();
  context.globalCompositeOperation = "screen";
  const halo = context.createRadialGradient(entity.x, entity.y, 0, entity.x, entity.y, outerRadius);
  halo.addColorStop(0, "rgba(255,255,232,1)");
  halo.addColorStop(0.1, rgba(COLORS.gold, 0.96));
  halo.addColorStop(0.34, rgba(color, 0.32));
  halo.addColorStop(0.7, rgba(color, 0.08));
  halo.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = halo;
  context.beginPath();
  context.arc(entity.x, entity.y, outerRadius, 0, Math.PI * 2);
  context.fill();
  const rayLength = entity.radius * (3.1 + pulse);
  context.strokeStyle = rgba(COLORS.gold, 0.24);
  context.lineWidth = 0.8 / zoom;
  context.beginPath();
  context.moveTo(entity.x - rayLength, entity.y);
  context.lineTo(entity.x + rayLength, entity.y);
  context.moveTo(entity.x, entity.y - rayLength);
  context.lineTo(entity.x, entity.y + rayLength);
  context.stroke();
  context.globalCompositeOperation = "source-over";
  const surface = context.createRadialGradient(entity.x - entity.radius * 0.32, entity.y - entity.radius * 0.38, 0, entity.x, entity.y, entity.radius * 1.15);
  surface.addColorStop(0, "#fffce0");
  surface.addColorStop(0.36, "#ffe58d");
  surface.addColorStop(0.78, "#e69b32");
  surface.addColorStop(1, "#8f4f1c");
  context.fillStyle = surface;
  context.shadowColor = COLORS.gold;
  context.shadowBlur = 15 / zoom;
  context.beginPath();
  context.arc(entity.x, entity.y, entity.radius, 0, Math.PI * 2);
  context.fill();
  context.shadowBlur = 0;
  context.strokeStyle = "rgba(255,246,184,.72)";
  context.lineWidth = 1 / zoom;
  for (let index = 0; index < 3; index += 1) {
    const rotation = time * (0.0001 + index * 0.000015) + index * 2.1;
    context.beginPath();
    context.arc(entity.x, entity.y, entity.radius + (4 + index * 4) / zoom, rotation, rotation + 1.05 + index * 0.12);
    context.stroke();
  }
  context.restore();
}

function drawPlanet(context: CanvasRenderingContext2D, entity: PositionedEntity, color: string, zoom: number, time: number, seed: number): void {
  const variant = stableHash(entity.id, seed) % PLANET_PALETTES.length;
  const [highlight, midtone, shadow] = PLANET_PALETTES[variant];
  const ringed = entity.kind === "artifact" || stableHash(`${entity.id}:ring`, seed) % 5 === 0;
  context.save();
  const atmosphere = context.createRadialGradient(entity.x, entity.y, entity.radius * 0.7, entity.x, entity.y, entity.radius * 1.65);
  atmosphere.addColorStop(0, rgba(color, 0.16));
  atmosphere.addColorStop(0.58, rgba(color, 0.1));
  atmosphere.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = atmosphere;
  context.beginPath();
  context.arc(entity.x, entity.y, entity.radius * 1.7, 0, Math.PI * 2);
  context.fill();
  if (ringed) {
    context.strokeStyle = rgba(highlight, 0.52);
    context.lineWidth = 2.1 / zoom;
    context.beginPath();
    context.ellipse(entity.x, entity.y, entity.radius * 1.72, entity.radius * 0.52, entity.angle * 0.18 - 0.2, 0, Math.PI * 2);
    context.stroke();
    context.strokeStyle = rgba(midtone, 0.46);
    context.lineWidth = 0.8 / zoom;
    context.beginPath();
    context.ellipse(entity.x, entity.y, entity.radius * 2.02, entity.radius * 0.64, entity.angle * 0.18 - 0.2, 0, Math.PI * 2);
    context.stroke();
  }
  const body = context.createRadialGradient(entity.x - entity.radius * 0.42, entity.y - entity.radius * 0.46, 0, entity.x, entity.y, entity.radius * 1.18);
  body.addColorStop(0, highlight);
  body.addColorStop(0.28, midtone);
  body.addColorStop(0.76, shadow);
  body.addColorStop(1, "#030812");
  context.fillStyle = body;
  context.beginPath();
  context.arc(entity.x, entity.y, entity.radius, 0, Math.PI * 2);
  context.fill();
  context.save();
  context.beginPath();
  context.arc(entity.x, entity.y, entity.radius * 0.96, 0, Math.PI * 2);
  context.clip();
  const surfaceOffset = Math.sin(time * 0.00008 + variant) * entity.radius * 0.15;
  if (variant === 1 || variant === 2) {
    context.strokeStyle = rgba(highlight, 0.18);
    context.lineWidth = Math.max(1, entity.radius * 0.12);
    for (let stripe = -2; stripe <= 2; stripe += 1) {
      context.beginPath();
      context.ellipse(entity.x + surfaceOffset, entity.y + stripe * entity.radius * 0.31, entity.radius * 1.2, entity.radius * 0.12, 0, 0, Math.PI * 2);
      context.stroke();
    }
  } else {
    for (let patch = 0; patch < 5; patch += 1) {
      const angle = randomUnit(seed + variant, patch, entity.id) * Math.PI * 2 + time * 0.000025;
      const distance = randomUnit(seed, patch, `${entity.id}:patch`) * entity.radius * 0.62;
      context.fillStyle = rgba(patch % 2 ? highlight : shadow, 0.16);
      context.beginPath();
      context.ellipse(entity.x + Math.cos(angle) * distance + surfaceOffset, entity.y + Math.sin(angle) * distance, entity.radius * (0.16 + patch * 0.025), entity.radius * 0.1, angle, 0, Math.PI * 2);
      context.fill();
    }
  }
  context.restore();
  context.strokeStyle = rgba(color, 0.8);
  context.lineWidth = 0.75 / zoom;
  context.beginPath();
  context.arc(entity.x, entity.y, entity.radius + 0.4 / zoom, 0, Math.PI * 2);
  context.stroke();
  context.fillStyle = "rgba(255,255,255,.74)";
  context.beginPath();
  context.arc(entity.x - entity.radius * 0.34, entity.y - entity.radius * 0.36, Math.max(0.65, entity.radius * 0.1), 0, Math.PI * 2);
  context.fill();
  if (variant === 4) {
    const moonAngle = time * 0.00025 + entity.angle;
    const moonRadius = entity.radius * 1.8;
    const moonX = entity.x + Math.cos(moonAngle) * moonRadius;
    const moonY = entity.y + Math.sin(moonAngle) * moonRadius * 0.48;
    context.fillStyle = "#b9c6c8";
    context.beginPath();
    context.arc(moonX, moonY, Math.max(1.2 / zoom, entity.radius * 0.16), 0, Math.PI * 2);
    context.fill();
  }
  context.restore();
}

function drawMarker(context: CanvasRenderingContext2D, entity: PositionedEntity, color: string, zoom: number, time: number): void {
  const { x, y, radius } = entity;
  context.save();
  context.translate(x, y);
  const markerGlow = context.createRadialGradient(0, 0, 0, 0, 0, radius * 2.8);
  markerGlow.addColorStop(0, rgba(color, 0.24));
  markerGlow.addColorStop(1, "rgba(0,0,0,0)");
  context.fillStyle = markerGlow;
  context.beginPath();
  context.arc(0, 0, radius * 2.8, 0, Math.PI * 2);
  context.fill();
  context.strokeStyle = color;
  context.fillStyle = rgba(color, 0.92);
  context.lineWidth = 1.35 / zoom;
  context.shadowColor = color;
  context.shadowBlur = 8 / zoom;
  if (entity.kind === "agent") {
    context.rotate(entity.angle + Math.sin(time * 0.0005) * 0.04);
    context.beginPath();
    context.moveTo(radius + 4, 0);
    context.lineTo(-radius, -radius * 0.72);
    context.lineTo(-radius * 0.25, 0);
    context.lineTo(-radius, radius * 0.72);
    context.closePath();
    context.stroke();
    context.strokeStyle = rgba(color, 0.35);
    context.beginPath();
    context.moveTo(-radius * 0.5, 0);
    context.lineTo(-radius * 2.5, 0);
    context.stroke();
  } else if (entity.kind === "finding") {
    context.rotate(Math.PI / 4);
    context.strokeRect(-radius, -radius, radius * 2, radius * 2);
    context.fillRect(-2 / zoom, -2 / zoom, 4 / zoom, 4 / zoom);
  } else {
    context.rotate(time * 0.00015);
    context.beginPath();
    for (let point = 0; point < 10; point += 1) {
      const pointRadius = point % 2 === 0 ? radius + 3 : radius * 0.52;
      const angle = (point / 10) * Math.PI * 2 - Math.PI / 2;
      point === 0 ? context.moveTo(Math.cos(angle) * pointRadius, Math.sin(angle) * pointRadius) : context.lineTo(Math.cos(angle) * pointRadius, Math.sin(angle) * pointRadius);
    }
    context.closePath();
    context.fill();
  }
  context.restore();
}

function drawLabel(context: CanvasRenderingContext2D, entity: PositionedEntity, mode: SpaceMapMode, zoom: number, selected: boolean): void {
  const fontSize = (mode === "galaxy" ? 10.5 : 10) / zoom;
  const title = entity.title.slice(0, mode === "galaxy" ? 29 : 32);
  const label = mode === "galaxy" && entity.kind === "agent" ? `AGENT · ${title}` : title;
  context.font = `600 ${fontSize}px "Bahnschrift SemiCondensed", "Arial Narrow", sans-serif`;
  const width = context.measureText(label).width;
  const x = mode === "galaxy" ? entity.x + entity.radius + 8 / zoom : entity.x - width / 2;
  const y = mode === "galaxy" ? entity.y - 8 / zoom : entity.y + entity.radius + 16 / zoom;
  const padX = 6 / zoom;
  const padY = 4 / zoom;
  context.save();
  context.fillStyle = selected ? "rgba(20,40,50,.96)" : "rgba(2,8,14,.8)";
  context.shadowColor = "rgba(0,0,0,.8)";
  context.shadowBlur = 8 / zoom;
  context.beginPath();
  context.moveTo(x - padX, y - fontSize - padY);
  context.lineTo(x + width + padX + 4 / zoom, y - fontSize - padY);
  context.lineTo(x + width + padX, y + padY);
  context.lineTo(x - padX, y + padY);
  context.closePath();
  context.fill();
  context.shadowBlur = 0;
  context.fillStyle = selected ? "#ffffff" : COLORS.text;
  context.fillText(label, x, y);
  const accent = statusColor(String(entity.status), false);
  context.fillStyle = accent;
  context.shadowColor = accent;
  context.shadowBlur = selected ? 7 / zoom : 0;
  context.fillRect(x - padX, y - fontSize - padY, 2 / zoom, fontSize + padY * 2);
  context.restore();
}

function drawSelection(context: CanvasRenderingContext2D, entity: PositionedEntity, zoom: number, time: number): void {
  const aperture = entity.radius + (11 + Math.sin(time * 0.003) * 2) / zoom;
  const cut = 7 / zoom;
  context.save();
  context.strokeStyle = "#ffffff";
  context.lineWidth = 1.35 / zoom;
  context.shadowColor = COLORS.cyan;
  context.shadowBlur = 7 / zoom;
  for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]] as const) {
    context.beginPath();
    context.moveTo(entity.x + sx * aperture, entity.y + sy * (aperture - cut));
    context.lineTo(entity.x + sx * aperture, entity.y + sy * aperture);
    context.lineTo(entity.x + sx * (aperture - cut), entity.y + sy * aperture);
    context.stroke();
  }
  context.strokeStyle = rgba(COLORS.cyan, 0.6);
  context.lineWidth = 1 / zoom;
  const rotation = time * 0.0008;
  context.beginPath();
  context.arc(entity.x, entity.y, aperture + 6 / zoom, rotation, rotation + 1.1);
  context.arc(entity.x, entity.y, aperture + 6 / zoom, rotation + Math.PI, rotation + Math.PI + 1.1);
  context.stroke();
  context.restore();
}

function drawMultiplayerClaim(context: CanvasRenderingContext2D, entity: PositionedEntity, color: string, zoom: number, time: number): void {
  const radius = entity.radius + 13 / zoom;
  context.save();
  context.strokeStyle = rgba(color, 0.18);
  context.lineWidth = 7 / zoom;
  context.shadowColor = color;
  context.shadowBlur = 12 / zoom;
  context.beginPath();
  context.arc(entity.x, entity.y, radius, 0, Math.PI * 2);
  context.stroke();
  context.strokeStyle = color;
  context.lineWidth = 1.6 / zoom;
  context.setLineDash([7 / zoom, 3 / zoom]);
  context.lineDashOffset = -time * 0.008 / zoom;
  context.beginPath();
  context.arc(entity.x, entity.y, radius, 0, Math.PI * 2);
  context.stroke();
  context.setLineDash([]);
  context.fillStyle = color;
  context.beginPath();
  context.arc(entity.x + radius * 0.72, entity.y - radius * 0.72, 2.8 / zoom, 0, Math.PI * 2);
  context.fill();
  context.restore();
}

function animateSystemLayout(layout: PositionedEntity[], time: number, enabled: boolean, seed: number): PositionedEntity[] {
  if (!enabled || time === 0) return layout;
  return layout.map((entity) => {
    if (Math.abs(entity.x) < 1 && Math.abs(entity.y) < 1 && Math.abs(entity.z) < 1) return entity;
    const ring = Math.hypot(entity.x, entity.y / 0.78);
    const hash = stableHash(entity.id);
    const direction = hash % 2 === 0 ? 1 : -1;
    const speed = 0.000012 + (hash % 7) * 0.0000015;
    const angle = entity.angle + time * speed * direction;
    const inclination = 0.1 + (stableHash(`${entity.id}:inclination`, seed) % 1_800) / 10_000;
    const phase = ((stableHash(`${entity.id}:phase`, seed) % 360) / 180) * Math.PI;
    return { ...entity, x: Math.cos(angle) * ring, y: Math.sin(angle) * ring * 0.78, z: Math.sin(angle + phase) * ring * inclination, angle };
  });
}

export function GalaxyCanvas({ entities, edges, seed, mode, focusSystemId, selectedId, onSelect, onOpenSystem, onOpenShipyard, shipyardEnabled, multiplayerClaims, onBackToGalaxy, animated, reducedMotion, highContrast }: GalaxyCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [layout, setLayout] = useState<PositionedEntity[]>([]);
  const [orientation, setOrientation] = useState<{ yaw: number; pitch: number }>(() => ({ yaw: DEFAULT_ORIENTATION[mode].yaw, pitch: DEFAULT_ORIENTATION[mode].pitch }));
  const [zoomLevel, setZoomLevel] = useState(1);
  const layoutRef = useRef<PositionedEntity[]>([]);
  const renderedLayoutRef = useRef<PositionedEntity[]>([]);
  const camera = useRef<Camera>({ x: 0, y: 0, zoom: 1, ...DEFAULT_ORIENTATION[mode] });
  const drag = useRef<{ x: number; y: number; cameraX: number; cameraY: number; yaw: number; pitch: number; mode: "rotate" | "pan" } | null>(null);
  const keyboardIndex = useRef(0);
  const stellarSystemIds = useMemo(() => entities.filter((entity) => entity.kind === "home" || entity.kind === "node").map((entity) => entity.id), [entities]);
  const claimedSystemCount = stellarSystemIds.length;
  const stellarProfiles = useMemo(() => stellarProfilesFor(stellarSystemIds, seed), [stellarSystemIds, seed]);
  const stellarOrdinals = useMemo(() => new Map(stellarSystemIds.map((id, ordinal) => [id, ordinal])), [stellarSystemIds]);
  const unclaimedSystemCount = frontierSystemCount(claimedSystemCount);
  const defaultGalaxyZoom = galaxyCameraZoom(unclaimedSystemCount);
  const defaultCameraZoom = mode === "galaxy" ? defaultGalaxyZoom : 1.08;
  const zoomPercent = Math.round((zoomLevel / defaultCameraZoom) * 100);
  const minZoomPercent = Math.ceil((0.26 / defaultCameraZoom) * 100);
  const maxZoomPercent = Math.floor((3.4 / defaultCameraZoom) * 100);
  const cameraScope = mode === "system" ? focusSystemId : "galaxy";
  const frontier = useMemo(() => createFrontierField(seed, unclaimedSystemCount), [seed, unclaimedSystemCount]);
  const connectedLanes = useMemo(() => connectedHyperlanes(layout, edges), [layout, edges]);
  const frontierBridges = useMemo(
    () => frontierClaimedBridges(frontier, layout.filter((entity) => entity.kind === "home" || entity.kind === "node")),
    [frontier, layout],
  );

  useEffect(() => {
    const view = DEFAULT_ORIENTATION[mode];
    camera.current = { x: 0, y: 0, zoom: defaultCameraZoom, ...view };
    setZoomLevel(defaultCameraZoom);
    setOrientation({ yaw: view.yaw, pitch: view.pitch });
  }, [cameraScope, defaultCameraZoom, mode]);

  useEffect(() => {
    const worker = new Worker(new URL("../layout.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent<PositionedEntity[]>) => {
      layoutRef.current = event.data;
      renderedLayoutRef.current = event.data;
      setLayout(event.data);
    };
    worker.postMessage({ entities, seed, mode, focusSystemId });
    return () => worker.terminate();
  }, [entities, seed, mode, focusSystemId]);

  const focusTitle = useMemo(() => entities.find((entity) => entity.id === focusSystemId)?.title ?? "Run nexus", [entities, focusSystemId]);
  const focusProfile = stellarProfiles.get(focusSystemId);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) return;
    let frame = 0;
    let last = 0;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      syncCanvasBackingStore(canvas, context, rect.width, rect.height, dpr);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();

    const draw = (time: number) => {
      if (time - last < 1000 / 50) { frame = requestAnimationFrame(draw); return; }
      last = time;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const motionTime = animated && !reducedMotion ? time : 0;
      const current = camera.current;
      drawBackdrop(context, width, height, seed, mode, highContrast, motionTime, current);
      context.save();
      context.translate(width / 2 + current.x, height / 2 + current.y);
      context.scale(current.zoom, current.zoom);

      const spatialLayout = mode === "system" ? animateSystemLayout(layoutRef.current, motionTime, animated && !reducedMotion, seed) : layoutRef.current;
      const frameLayout = projectLayout3D(spatialLayout, current);
      renderedLayoutRef.current = frameLayout;
      if (mode === "galaxy") {
        drawGalaxyField(context, seed, current.zoom, motionTime, highContrast, current);
        drawGalaxyPlane(context, current, current.zoom);
        drawFrontierNetwork(context, projectFrontier3D(frontier, current), frameLayout, frontierBridges, current.zoom, motionTime, highContrast);
        drawTerritory(context, frameLayout, current.zoom, motionTime);
        drawMultiplayerTerritories(context, frameLayout, multiplayerClaims, current.zoom, motionTime);
      } else {
        drawSystemField(context, seed, current.zoom, motionTime, highContrast, current);
        drawOrbits(context, seed, current.zoom, motionTime, current);
      }
      drawHyperlanes(context, frameLayout, connectedLanes, current.zoom, motionTime);
      if (mode === "galaxy") drawAgentAssignments(context, frameLayout, current.zoom, motionTime);

      for (const entity of frameLayout) {
        const color = statusColor(String(entity.status), highContrast);
        const isCentral = Math.abs(entity.x) < 1 && Math.abs(entity.y) < 1;
        const pulse = animated && !reducedMotion ? (Math.sin(motionTime * 0.0017) + 1) * 0.16 : 0;
        const stellarProfile = stellarProfiles.get(entity.id);
        if (((mode === "galaxy" && ["home", "node"].includes(entity.kind)) || (mode === "system" && isCentral)) && stellarProfile) {
          drawGalaxySystemStar(context, entity, String(entity.status), stellarProfile, stellarOrdinals.get(entity.id) ?? 0, pulse, current.zoom, motionTime);
        } else if (isCentral || (mode === "galaxy" && ["home", "node"].includes(entity.kind))) drawStar(context, entity, color, pulse, current.zoom, motionTime);
        else if (["node", "artifact", "home"].includes(entity.kind)) drawPlanet(context, entity, color, current.zoom, motionTime, seed);
        else drawMarker(context, entity, color, current.zoom, motionTime);
        const claimColor = multiplayerClaims[entity.id];
        if (claimColor && ["home", "node"].includes(entity.kind)) drawMultiplayerClaim(context, entity, claimColor, current.zoom, motionTime);
        drawLabel(context, entity, mode, current.zoom, entity.id === selectedId);
        if (entity.id === selectedId) drawSelection(context, entity, current.zoom, motionTime);
      }
      context.restore();
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(frame); observer.disconnect(); };
  }, [animated, reducedMotion, highContrast, seed, mode, selectedId, layout, frontier, frontierBridges, connectedLanes, stellarProfiles, stellarOrdinals, multiplayerClaims]);

  const screenToWorld = (clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const current = camera.current;
    return { x: (clientX - rect.left - rect.width / 2 - current.x) / current.zoom, y: (clientY - rect.top - rect.height / 2 - current.y) / current.zoom };
  };

  const hitAt = (clientX: number, clientY: number) => {
    const world = screenToWorld(clientX, clientY);
    return renderedLayoutRef.current
      .map((entity) => ({ entity, distance: Math.hypot(entity.x - world.x, entity.y - world.y) }))
      .filter(({ entity, distance }) => distance <= Math.max(15, entity.radius + 7))
      .sort((left, right) => left.distance - right.distance)[0]?.entity;
  };

  const adjustZoom = (factor: number) => {
    const next = Math.max(0.26, Math.min(3.4, camera.current.zoom * factor));
    camera.current.zoom = next;
    setZoomLevel(next);
  };

  const setZoomPercent = (percent: number) => {
    const next = Math.max(0.26, Math.min(3.4, defaultCameraZoom * percent / 100));
    camera.current.zoom = next;
    setZoomLevel(next);
  };

  const rotateCamera = (yawDelta: number, pitchDelta: number) => {
    camera.current.yaw = normalizeAngle(camera.current.yaw + yawDelta);
    camera.current.pitch = normalizeAngle(camera.current.pitch + pitchDelta);
    setOrientation({ yaw: camera.current.yaw, pitch: camera.current.pitch });
  };

  const resetCamera = () => {
    const view = DEFAULT_ORIENTATION[mode];
    camera.current = { x: 0, y: 0, zoom: defaultCameraZoom, ...view };
    setZoomLevel(defaultCameraZoom);
    setOrientation({ yaw: view.yaw, pitch: view.pitch });
  };

  return (
    <div className={`galaxy-stage map-${mode}`}>
      <canvas
        ref={canvasRef}
        className="galaxy-canvas"
        role="img"
        aria-label={mode === "galaxy" ? `Rotatable 3D Evolastra galaxy map with ${claimedSystemCount} claimed analysis systems and ${unclaimedSystemCount} connected unclaimed frontier systems.` : `Rotatable 3D Evolastra system view for ${focusTitle}, a ${focusProfile?.label ?? "star"}, with ${Math.max(0, layout.length - 1)} orbital objects.`}
        tabIndex={0}
        onDoubleClick={(event) => {
          if (mode !== "galaxy") return;
          const hit = hitAt(event.clientX, event.clientY);
          const systemId = hit && ["home", "node"].includes(hit.kind) ? hit.id : hit?.kind === "agent" ? hit.parentId : null;
          if (systemId) onOpenSystem(systemId);
        }}
        onPointerDown={(event) => {
          const dragMode = event.shiftKey || event.button === 1 || event.button === 2 ? "pan" : "rotate";
          drag.current = {
            x: event.clientX,
            y: event.clientY,
            cameraX: camera.current.x,
            cameraY: camera.current.y,
            yaw: camera.current.yaw,
            pitch: camera.current.pitch,
            mode: dragMode,
          };
          event.currentTarget.style.cursor = dragMode === "rotate" ? "grabbing" : "move";
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!drag.current) return;
          const deltaX = event.clientX - drag.current.x;
          const deltaY = event.clientY - drag.current.y;
          if (drag.current.mode === "pan") {
            camera.current.x = drag.current.cameraX + deltaX;
            camera.current.y = drag.current.cameraY + deltaY;
          } else {
            camera.current.yaw = normalizeAngle(drag.current.yaw + deltaX * 0.006);
            camera.current.pitch = normalizeAngle(drag.current.pitch + deltaY * 0.006);
            setOrientation({ yaw: camera.current.yaw, pitch: camera.current.pitch });
          }
        }}
        onPointerUp={(event) => {
          if (!drag.current) return;
          const moved = Math.hypot(event.clientX - drag.current.x, event.clientY - drag.current.y);
          drag.current = null;
          event.currentTarget.style.cursor = "";
          if (moved < 5) {
            const hit = hitAt(event.clientX, event.clientY);
            if (hit && mode === "system" && shipyardEnabled && hit.id === focusSystemId) onOpenShipyard();
            else if (hit) onSelect(hit.id);
          }
          event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onPointerCancel={(event) => {
          drag.current = null;
          event.currentTarget.style.cursor = "";
        }}
        onContextMenu={(event) => event.preventDefault()}
        onWheel={(event) => {
          event.preventDefault();
          adjustZoom(Math.exp(-event.deltaY * 0.001));
        }}
        onKeyDown={(event) => {
          if (["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"].includes(event.key)) {
            event.preventDefault();
            const direction = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
            keyboardIndex.current = (keyboardIndex.current + direction + renderedLayoutRef.current.length) % Math.max(1, renderedLayoutRef.current.length);
            const entity = renderedLayoutRef.current[keyboardIndex.current];
            if (entity) onSelect(entity.id);
          }
          if (event.key === "Enter" && mode === "galaxy" && selectedId) {
            const selected = renderedLayoutRef.current.find((entity) => entity.id === selectedId);
            const systemId = selected && ["home", "node"].includes(selected.kind) ? selected.id : selected?.kind === "agent" ? selected.parentId : null;
            if (systemId) onOpenSystem(systemId);
          }
          if (event.key === "Enter" && mode === "system" && shipyardEnabled && selectedId === focusSystemId) onOpenShipyard();
          const key = event.key.toLowerCase();
          if (["a", "d", "w", "s", "+", "=", "-", "_"].includes(key)) event.preventDefault();
          if (key === "a") rotateCamera(-0.12, 0);
          if (key === "d") rotateCamera(0.12, 0);
          if (key === "w") rotateCamera(0, -0.08);
          if (key === "s") rotateCamera(0, 0.08);
          if (key === "+" || key === "=") adjustZoom(1.14);
          if (key === "-" || key === "_") adjustZoom(1 / 1.14);
          if (event.key === "Home") resetCamera();
        }}
      />
      <div className="map-sweep" aria-hidden="true" />
      <div className="map-frame" aria-hidden="true"><i /><i /><i /><i /></div>
      <div className="map-readout">
        <span>{mode === "galaxy" ? "STRATEGIC DEEP FIELD" : "LOCAL ORBITAL ARRAY"}</span>
        <strong>{mode === "galaxy" ? "Galaxy map" : focusTitle}</strong>
        {mode === "galaxy" && <small className="frontier-count">{claimedSystemCount} claimed · {unclaimedSystemCount} unclaimed</small>}
        <small>{mode === "galaxy" ? `${claimedSystemCount} charted systems · ${entities.filter((entity) => entity.kind === "agent").length} agent vessels` : `${focusProfile?.label ?? "star"} · ${Math.max(0, layout.length - 1)} tracked bodies`}</small>
      </div>
      {mode === "system" && <button className="map-back" onClick={onBackToGalaxy}><span aria-hidden="true">←</span> Galaxy map</button>}
      <output className="map-orientation" aria-label={`3D camera yaw ${angleDegrees(orientation.yaw)} degrees, tilt ${angleDegrees(orientation.pitch)} degrees; full orbit enabled`}>
        <span>3D NAV · FULL ORBIT</span><b>YAW {angleDegrees(orientation.yaw)}°</b><b>TILT {angleDegrees(orientation.pitch)}°</b>
      </output>
      <div className="map-zoom" aria-label="Map zoom controls">
        <span>ZOOM</span>
        <button onClick={() => adjustZoom(1 / 1.18)} aria-label="Zoom out">−</button>
        <input
          type="range"
          min={minZoomPercent}
          max={maxZoomPercent}
          step="1"
          value={Math.max(minZoomPercent, Math.min(maxZoomPercent, zoomPercent))}
          onChange={(event) => setZoomPercent(Number(event.target.value))}
          aria-label="Map zoom level"
        />
        <output aria-live="polite">{zoomPercent}%</output>
        <button onClick={() => adjustZoom(1.18)} aria-label="Zoom in">+</button>
      </div>
      <div className="map-camera" aria-label="3D map rotation controls">
        <button onClick={() => rotateCamera(-0.14, 0)} aria-label="Rotate left">↶</button>
        <button onClick={() => rotateCamera(0.14, 0)} aria-label="Rotate right">↷</button>
        <button onClick={() => rotateCamera(0, -0.09)} aria-label="Tilt up">↑</button>
        <button onClick={() => rotateCamera(0, 0.09)} aria-label="Tilt down">↓</button>
        <button onClick={resetCamera} aria-label="Reset 3D map view">⌾</button>
      </div>
      <div className="map-telemetry" aria-hidden="true">
        <span className="radar-glyph"><i /></span>
        <div><b>{mode === "galaxy" ? "EXPANDING DEEP FIELD" : "ORBITAL LOCK"}</b><small>{mode === "galaxy" ? `${unclaimedSystemCount} FRONTIER SYSTEMS · AUTO EXPAND` : "TRAJECTORIES LIVE · GRAVITY LOCK"}</small></div>
      </div>
      {mode === "galaxy" ? (
        <div className="map-legend" aria-hidden="true"><i className="legend-claimed" /> claimed <i className="legend-agent" /> agent <i className="legend-unclaimed" /> unclaimed <i className="legend-pulsar" /> pulsar <i className="legend-singularity" /> black hole</div>
      ) : (
        <div className="map-legend" aria-hidden="true"><i className="legend-complete" /> complete <i className="legend-active" /> active <i className="legend-disputed" /> disputed</div>
      )}
      {mode === "galaxy" && layout.some((entity) => Boolean(entity.semanticSignature)) && <aside className="semantic-proximity-key" aria-label="Semantic map distance">
        <span>SEMANTIC GEOGRAPHY</span><strong>Nearby systems share research meaning</strong><small>Program · genes · cytobands · mechanisms · therapy · validation</small>
      </aside>}
      {mode === "galaxy" && <div className="canvas-hint map-frontier-hint">Drag to rotate · Shift-drag to pan · scroll to zoom · double-click to enter</div>}
      <div className="canvas-hint">{mode === "galaxy" ? "Drag to rotate · Shift-drag to pan · scroll to zoom" : shipyardEnabled ? "Click command star for shipyard · W/A/S/D camera · Home resets" : "Drag to rotate · Shift-drag to pan · W/A/S/D camera · Home resets"}</div>
    </div>
  );
}
