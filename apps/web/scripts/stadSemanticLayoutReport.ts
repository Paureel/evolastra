import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { parseSemanticSignature, semanticCoordinates, semanticDistance, semanticLayoutMetrics, type SemanticSystem } from "../src/semanticLayout";

const target = resolve(process.argv[2] ?? "data/live-test/stad_multiplayer_simulation.json");
const report = JSON.parse(readFileSync(target, "utf8")) as Record<string, unknown>;
const hypotheses = Array.isArray(report.hypotheses) ? report.hypotheses as Array<Record<string, unknown>> : [];
const systems: SemanticSystem[] = hypotheses.flatMap((hypothesis) => {
  const signature = parseSemanticSignature(hypothesis.semantic_signature);
  const id = typeof hypothesis.node_id === "string" ? hypothesis.node_id : "";
  return signature && id ? [{ id, semanticSignature: signature }] : [];
});
if (systems.length !== 6) throw new Error(`Expected six semantic systems, received ${systems.length}`);
const points = semanticCoordinates(systems, Number(report.seed ?? 874049));
const metrics = semanticLayoutMetrics(systems, points);
const pairs = [];
for (let left = 0; left < systems.length; left += 1) {
  for (let right = left + 1; right < systems.length; right += 1) {
    const leftPoint = points.get(systems[left].id)!;
    const rightPoint = points.get(systems[right].id)!;
    pairs.push({
      source_id: systems[left].id,
      target_id: systems[right].id,
      semantic_distance: semanticDistance(systems[left].semanticSignature, systems[right].semanticSignature),
      map_distance: Math.hypot(leftPoint.x - rightPoint.x, leftPoint.y - rightPoint.y, leftPoint.z - rightPoint.z),
    });
  }
}
report.layout_validation = {
  method: "weighted-jaccard-plus-deterministic-3d-stress-minimization",
  exploratory_product_revision: true,
  iterations: 1200,
  ...metrics,
  pass: metrics.spearman >= 0.8 && metrics.meanWithinProgram < metrics.meanBetweenPrograms && metrics.sameProgramNearestNeighbors === systems.length,
  coordinates: Object.fromEntries(points),
  pairs,
};
writeFileSync(target, `${JSON.stringify(report, null, 2)}\n`, "utf8");
process.stdout.write(JSON.stringify(report.layout_validation, null, 2));
