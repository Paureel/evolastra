# Renderer recommendation for ADR conversion

Status: **provisional implementation recommendation; performance sign-off blocked on the browser benchmark**
Date: 2026-07-17

## Recommendation

Retain the shared contract's isolated **custom Canvas 2D renderer for the vertical slice**, behind a small renderer adapter. Make **PixiJS + Graphology the first mandatory challenger** in the common benchmark. Keep Sigma.js + Graphology as the graph-centric comparison, keep Reagraph as the React-centric comparison, and do not authorize a custom WebGL engine yet.

This is not a claim that Canvas 2D meets the production-scale target. It is the lowest-regret implementation order while the new vertical-slice component has no common-fixture performance data:

- Canvas 2D matches the accepted architecture, has no renderer dependency migration cost, supports the procedural instrument-like visual language, and provides a useful fallback.
- PixiJS is the strongest qualitative challenger when GPU batching, atlas-heavy sprites, and territory meshes become necessary without surrendering visual control.
- Sigma.js is attractive if the delivered scene remains mostly a large node-link graph, but orbital artifacts, causal fleet motion, and system-local scenes require a representative spike.
- Reagraph offers a broad ready-made React graph surface, but its high-frequency update path must prove compatibility with the rule that renderer frequency is isolated from React.
- A custom WebGL path has the largest ownership burden and lacks a demonstrated requirement that PixiJS cannot satisfy.

## Decision conditions

The lead can convert this into an ADR with state `provisional` now. Change it to `accepted for production` only after the protocol in [renderer-comparison.md](./renderer-comparison.md) is executed against [renderer-fixture.v1.json](./renderer-fixture.v1.json).

Migration from Canvas 2D to PixiJS is recommended when either condition holds:

1. Canvas 2D fails a hard correctness, latency, frame-time, or memory threshold and PixiJS passes it; or
2. PixiJS improves the material bottleneck by at least 20% across repeated runs while preserving screenshots, picking, semantic zoom, reduced motion, high contrast, and the synchronized text alternative.

If Canvas 2D passes all gates and PixiJS's advantage is within benchmark noise or less than 10%, retain Canvas 2D. If neither passes, investigate scene aggregation and atlas/label policy before authorizing custom WebGL; renderer replacement must not compensate for an avoidably overdrawn projection.

## Required architectural seam

The semantic projection should provide stable IDs, precomputed positions, LOD/label decisions, typed edges, territory geometry, and coalesced deltas. The renderer adapter owns draw resources, picking, viewport culling, and camera transforms. React owns panels, search, inspector, text tree, and focus semantics. This seam makes the benchmark challengers replaceable without changing canonical semantic payloads.

## Known gap

No browser comparison result exists yet because there is no realistic generated fixture, benchmark route, challenger adapter, or raw result set. The recommendation is defensible as an implementation order, not as production performance evidence.
