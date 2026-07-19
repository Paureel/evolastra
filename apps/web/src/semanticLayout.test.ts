import { describe, expect, it } from "vitest";
import { semanticCoordinates, semanticDistance, semanticLayoutMetrics } from "./semanticLayout";
import { STAD_SEMANTIC_FIXTURE } from "./stadSemanticFixture";

describe("semantic research geography", () => {
  it("computes bounded symmetric weighted-Jaccard distance", () => {
    const left = STAD_SEMANTIC_FIXTURE[0].semanticSignature;
    const related = STAD_SEMANTIC_FIXTURE[1].semanticSignature;
    const orthogonal = STAD_SEMANTIC_FIXTURE[3].semanticSignature;
    expect(semanticDistance(left, left)).toBe(0);
    expect(semanticDistance(left, related)).toBe(semanticDistance(related, left));
    expect(semanticDistance(left, related)).toBeGreaterThanOrEqual(0);
    expect(semanticDistance(left, orthogonal)).toBeLessThanOrEqual(1);
    expect(semanticDistance(left, related)).toBeLessThan(semanticDistance(left, orthogonal));
  });

  it("deterministically preserves the registered six-system distance contract", () => {
    const first = semanticCoordinates(STAD_SEMANTIC_FIXTURE, 874049);
    const second = semanticCoordinates(STAD_SEMANTIC_FIXTURE, 874049);
    expect(first).toEqual(second);
    expect([...first.values()].every((point) => [point.x, point.y, point.z].every(Number.isFinite))).toBe(true);
    const metrics = semanticLayoutMetrics(STAD_SEMANTIC_FIXTURE, first);
    expect(metrics.pairCount).toBe(15);
    expect(metrics.spearman).toBeGreaterThanOrEqual(0.8);
    expect(metrics.meanWithinProgram).toBeLessThan(metrics.meanBetweenPrograms);
    expect(metrics.sameProgramNearestNeighbors).toBe(6);
  });
});
