# ADR — Renderer selection

Status: accepted for the vertical slice; production-scale decision remains provisional.

## Decision

Use an isolated Canvas 2D scene for the initial end-to-end implementation. React owns accessible controls and panels; a worker computes deterministic positions; `requestAnimationFrame` owns scene drawing. The text tree is a synchronized, complete alternative.

## Evidence

The repository began empty, so no renderer was retained by inertia. The common comparison in `docs/benchmarks/renderer-comparison.md` evaluates Canvas 2D, PixiJS + Graphology, Sigma.js + Graphology, and Reagraph against the same 6,000-object / 20,000-edge target. No comparable browser benchmark has yet been executed, so the evidence is qualitative and this ADR does not claim target-scale performance.

Canvas minimizes vertical-slice complexity, supports the required original marks and semantic edge patterns, and keeps render state outside React. PixiJS + Graphology is the first challenger for the executable benchmark because it offers GPU batching and flexible custom marks without forcing full 3D.

## Exit criterion

Replace Canvas only when a common browser harness demonstrates a measurable usability or performance benefit while preserving picking, semantic zoom, deterministic mental-map stability, reduced motion, and accessible synchronized navigation.
