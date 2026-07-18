# Renderer comparison

Status: **qualitative benchmark design; no browser performance measurements yet**
Reviewed: 2026-07-17

No common benchmark harness or candidate adapters existed when this comparison was prepared. A custom Canvas 2D vertical-slice component appeared during the concurrent implementation, but it has not been run against the common fixture or measured here. Consequently, this document contains no claimed render times, frame rates, latency, or memory results. The package versions below are registry observations, not installed dependencies. The executable protocol and pass thresholds are pre-registered here so a later run cannot silently favor the selected implementation.

## Decision question

Which 2D/2.5D renderer best preserves evidence navigation and the original procedural visual language at 1,000 semantic systems, 5,000 artifact/dataset objects, 20,000 typed edges, and 50 moving agents while leaving React responsible for the accessible application shell?

The renderer is only a projection. It must not own semantic records, layout truth, event replay, or the accessible text alternative.

## Common fixture

Every candidate must consume [renderer-fixture.v1.json](./renderer-fixture.v1.json). The full scene contains 6,000 graph objects, 20,000 typed edges, 50 agents, and 48 territory polygons. The incremental scenario begins at 90% of that scene and reaches the full target over 30 seconds while 1,000 metric samples/second are coalesced to 20 renderer updates/second.

The fixture generator must emit one canonical JSON projection plus packed typed-array forms derived from it. It must use the recorded seed and stable IDs. All candidates receive:

- the same precomputed node positions, camera keyframes, label priorities, territory meshes, sprite atlas, and update batches;
- the same viewport sizes and device-pixel-ratio variants;
- animation disabled for load tests and the same causal animation clock for interaction tests;
- the same semantic-zoom visibility decisions, made outside the renderer;
- the same parallel DOM tree for keyboard and screen-reader access.

Layout is deliberately excluded from renderer timing. A separate layout benchmark can consume the same semantic graph. Reagraph's or Sigma's built-in layout must be disabled for this comparison.

## Candidates and primary evidence

Versions observed with `npm view` on 2026-07-17:

| Candidate | Observed package version | License | Primary evidence |
|---|---:|---|---|
| PixiJS + Graphology | `pixi.js` 8.19.0; `graphology` 0.26.0 | MIT; MIT | [PixiJS renderers](https://pixijs.com/8.x/guides/components/renderers), [PixiJS events](https://pixijs.com/8.x/guides/components/events), [Graphology](https://graphology.github.io/) |
| Sigma.js + Graphology | `sigma` 3.0.3; `graphology` 0.26.0; optional `@react-sigma/core` 5.0.6 | MIT | [Sigma documentation](https://www.sigmajs.org/docs/), [customization](https://www.sigmajs.org/docs/advanced/customization), [renderers](https://www.sigmajs.org/docs/advanced/renderers) |
| Reagraph | `reagraph` 4.32.0 | Apache-2.0 | [Reagraph primary repository and documentation](https://github.com/reaviz/reagraph) |
| Custom Canvas 2D / custom WebGL | Browser platform APIs | Platform API | [Canvas 2D](https://html.spec.whatwg.org/multipage/canvas.html#the-canvas-element), [WebGL 2](https://registry.khronos.org/webgl/specs/latest/2.0/) |

These are software licenses, not entries in the visual-asset ledger. A production lockfile and software-notice review remain separate release tasks.

## Qualitative comparison

`Strong`, `mixed`, and `weak` below describe documented capability and architecture fit. They are not performance measurements.

| Criterion | PixiJS + Graphology | Sigma.js + Graphology | Reagraph | Custom Canvas 2D / WebGL |
|---|---|---|---|---|
| Original sprites, planets, probes, and layered effects | **Strong.** General 2D scene renderer; application owns the visual grammar. | **Mixed.** Custom node/edge programs and layers exist, but the default abstraction is a node-link graph. | **Mixed.** Customizable nodes are documented, but the React/Three abstraction must be proven for the full visual grammar. | **Strong.** Full control; every primitive and atlas path is application-owned. |
| Incremental graph model | **Strong.** Graphology provides mutation events; adapter work is required. | **Strong.** Sigma is designed around Graphology. | **Mixed.** Graphology is a dependency, but the public React data/update path must be stress-tested. | **Mixed.** Exact behavior is controllable, but the graph index, dirty sets, and batching are application work. |
| Labels and picking | **Mixed.** Pixi events exist; label priority/collision remain application work. | **Strong on documented graph use cases.** Labels, camera, and graph events are core concerns. | **Strong on documented graph use cases.** Advanced label placement and interaction are advertised. | **Mixed.** Can be exact, but spatial indices, collision, hit testing, and text quality are application work. |
| Semantic zoom | **Strong potential.** Scene graph visibility and atlas swaps are flexible; policy remains external. | **Mixed-to-strong.** Reducers/customization can change graph appearance; nested system scenes need a spike. | **Mixed.** Camera and layouts are available; deterministic multi-tier detail needs a spike. | **Strong potential.** Complete control, with substantial implementation and test burden. |
| Territory rendering | **Strong potential.** Polygon meshes can share the scene. | **Mixed.** Custom canvas/WebGL layers can carry contours, but synchronization must be proven. | **Unknown.** No primary documentation reviewed here establishes the required stable territory layer. | **Strong potential.** Canvas paths or WebGL meshes are direct, but triangulation/caching are application work. |
| Contract fit: renderer state isolated from React | **Strong.** A thin imperative adapter can own the scene. | **Strong.** Sigma can be mounted imperatively; React wrapper is optional. | **Mixed.** It is intentionally a React graph component, so high-frequency updates must be shown not to become React render volume. | **Strong.** This is the accepted vertical-slice architecture. |
| Accessibility | **Requires parallel DOM.** Canvas/WebGL objects are not the only interaction surface. | **Requires parallel DOM.** Treat graph canvas as a visual projection. | **Requires verification.** No complete screen-reader-equivalent surface was established from the reviewed primary documentation. | **Requires parallel DOM.** The synchronized text tree, search, and inspector are mandatory. |
| Browser/fallback strategy | WebGL is the practical baseline; WebGPU must be feature-detected. A non-GPU fallback still needs design. | WebGL baseline; fallback renderer needs design. | WebGL baseline through Three.js; fallback needs design. | Canvas 2D has broad baseline utility. A custom WebGL path needs a Canvas 2D fallback or explicit degraded mode. |
| Engineering complexity for this product | **Medium-high.** Rendering is supplied; graph-specific LOD, territories, and accessibility are not. | **Medium.** Best graph defaults, with extra work for orbital artifacts and fleets. | **Medium initially, uncertain later.** Quick graph composition; dependency and abstraction fit require measurement. | **High.** Canvas 2D starts small; a production custom WebGL engine is the highest-maintenance option. |
| Current repository fit | Challenger; not installed. | Challenger; not installed. | Challenger; not installed. | Incumbent in the accepted shared contract; an unmeasured vertical-slice component now exists. |

## Executable harness contract

Each candidate adapter must implement the same interface:

```ts
interface RendererBenchAdapter {
  mount(host: HTMLElement, options: BenchOptions): Promise<void>;
  load(snapshot: BenchSnapshot): Promise<void>;
  applyBatch(batch: ProjectionDelta): void;
  setCamera(camera: CameraState): void;
  pick(clientX: number, clientY: number): Promise<string | null>;
  settle(): Promise<void>;
  stats(): RendererStats;
  destroy(): Promise<void>;
}
```

The harness should be a production Vite build controlled by Playwright. It must record the exact OS, browser build, CPU, logical cores, RAM, GPU/driver, power mode, display scale, viewport, device-pixel ratio, and commit. Run on AC power with background load noted. Do not mix results from materially different machines in one ranking.

For each browser/candidate/viewport combination:

1. Perform five unreported warm-up runs.
2. Perform ten measured runs with candidate order randomized.
3. Measure cold route-to-first-useful-render separately from scene `load()` to first complete frame.
4. Run the deterministic 30-second pan/zoom/pick script after settling.
5. Run the 30-second incremental insertion and coalesced metric scenario.
6. Repeat with reduced motion and high contrast.
7. Destroy and remount the scene ten times for retained-memory checks.
8. Save raw JSON, Chrome trace where available, console logs, and screenshots. Report median, p95, p99, sample count, and failures; never report only an average.

Instrumentation:

- `performance.mark`/`measure` for route, load, update-to-paint, and pick latency;
- `requestAnimationFrame` deltas for frame time;
- `PerformanceObserver` for long tasks and Long Animation Frames where supported;
- Playwright traces and Chromium DevTools Protocol for CPU/main-thread evidence;
- `performance.measureUserAgentSpecificMemory()` or an explicitly documented substitute where available;
- `EXT_disjoint_timer_query_webgl2` only where supported for GPU timing; otherwise record `not measurable`;
- deterministic screenshot and semantic assertions for label tiers, selection, territory alignment, and reduced-motion behavior.

GPU memory is not reliably exposed by ordinary browser APIs. It must be reported as `not measurable` unless a repeatable platform-specific method and its limitations are recorded.

## Pre-registered pass thresholds

These are product acceptance gates for the recorded modern-laptop environment, not observed results. If the benchmark machine is materially below the documented support floor, record that fact and run a second reference environment; do not loosen thresholds after seeing a favored candidate's results.

| Area | Hard pass threshold |
|---|---|
| First useful render, cold production navigation | p95 <= 2,500 ms for the full fixture at distant LOD |
| Scene load after modules are ready | p95 <= 1,500 ms to a correct distant-LOD frame |
| Interaction frame time | p95 <= 18.2 ms and p99 <= 33.3 ms during the scripted 30 seconds |
| Severe stalls | No post-settle frame > 200 ms; time in tasks >= 50 ms is <= 1% of scenario duration |
| Pick latency | p95 <= 50 ms and p99 <= 100 ms, with 100% correct IDs for scripted targets |
| Coalesced update-to-paint | p95 <= 100 ms and p99 <= 250 ms while ingest receives 1,000 metric samples/second |
| Incremental correctness | Final counts and visible state exactly match the canonical projection; no dropped semantic update |
| Labels | 100% of required priority labels present at each zoom tier; no stale label after a state change |
| Memory | Stabilized JS heap delta <= 250 MiB and browser working-set delta <= 750 MiB; retained growth after ten destroy/remount cycles <= 5% |
| Browser support | Pass in current stable Chromium and Firefox; WebKit smoke pass where the test host is available; unsupported GPU features degrade deliberately |
| Accessibility | Every entity remains reachable through synchronized search/text tree; canvas is not the sole control surface; reduced-motion run contains no ambient motion |
| Visual correctness | No missing sprites, territory drift, picking offset, or context-loss crash at DPR 1 and 2 |

A metric that cannot be measured is `not measured`, never a pass. Missing memory evidence does not block a functional spike, but it blocks a final production-performance claim.

## Winner rule

1. Disqualify a candidate that fails correctness, accessibility, browser fallback, or any hard latency/frame threshold.
2. Among passing candidates, compare p95 frame time, update-to-paint, pick latency, memory, bundle cost, and implementation complexity with confidence intervals or run dispersion visible.
3. If two candidates are within 10% on performance and both pass, prefer the one with lower lifecycle complexity and higher visual-language flexibility.
4. Do not replace the Canvas 2D incumbent for a marginal result. Migrate only when it fails a hard gate or a challenger improves a material bottleneck by at least 20% while matching correctness, accessibility, and visual fidelity.
5. A custom WebGL renderer is justified only if both Canvas 2D and PixiJS fail a documented hard requirement that a focused custom spike passes. The cost of shaders, text, atlases, picking, context recovery, and browser testing must be included.

## Current evidence and gap

The initial repository audit found an empty workspace. A custom Canvas 2D component and web package were added concurrently after that audit, but there is still no generated common fixture, candidate adapter set, benchmark route, or raw browser result. This workstream therefore did not execute a renderer comparison. The qualitative evidence supports a bounded implementation recommendation, but final renderer performance selection remains open.

Commands run:

```powershell
rg --files
npm view pixi.js version license homepage repository.url engines peerDependencies --json
npm view graphology version license homepage repository.url engines peerDependencies --json
npm view sigma version license homepage repository.url engines peerDependencies --json
npm view @react-sigma/core version license homepage repository.url engines peerDependencies --json
npm view reagraph version license homepage repository.url engines peerDependencies --json
```
