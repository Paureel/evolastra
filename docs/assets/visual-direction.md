# Evolastra Observatory visual direction

Status: direction v1, approved for implementation review
Date: 2026-07-17

## Subject, audience, and job

Evolastra Observatory is a cinematic analytical command interface for researchers and engineers supervising complex multi-agent investigations. Its main screen makes the current state, provenance, and next evidence-bearing action understandable through two explicitly different spatial scales.

- **Galaxy Map:** analytical branches become charted star systems connected by semantic hyperlanes and enclosed by a translucent investigation territory.
- **System View:** the selected branch becomes a luminous primary; agents, artifacts, findings, anomalies, and child branches occupy typed orbital bands.

The visual language uses deep astronomical fields, procedural nebulae, survey cyan, stellar gold, and territory violet. It borrows the legibility and scale-switching conventions of space-strategy cartography without copying any game artwork, icons, typography, or branded interface assets.

The direction is **the quiet survey instrument**: a dark mineral field, measured typography, procedural marks, and sparse warm accents. It borrows its visual logic from optical calibration plates, sampling instruments, and scientific notation—not from a game cockpit. The galaxy is a navigable analytical projection, not scenery.

## Signature: the evidence aperture

The memorable element is a broken circular aperture around each semantic system. Its segments encode real state:

- outer arc: lifecycle state, with dash pattern as a non-color channel;
- middle arc: evidence coverage, rendered in four discrete segments;
- inner witness mark: anomaly or approval state;
- selected path: aligned ticks appear across connected apertures, making provenance read like a calibrated instrument.

The aperture replaces generic glowing selection rings. It scales from a six-pixel system mark to the inspector's detailed evidence summary. No segment animates unless an observable event changes its value.

## Core tokens

### Palette

| Token | Hex | Purpose |
|---|---|---|
| Survey black | `#071318` | Canvas and deepest field |
| Mineral slate | `#102329` | Panels, trays, local system wells |
| Paper trace | `#D9E1DC` | Primary text and critical linework |
| Weathered label | `#91A5A2` | Secondary text and inactive marks |
| Oxide copper | `#C58B63` | Selection, human action, evidence emphasis |
| Glacial glass | `#75AEB3` | Active computation and navigational focus |

Semantic overlays are deliberately muted: lichen `#95AF7E` for validated/completed, ochre `#D2B56D` for waiting/warning, and clay `#D98278` for failed/contradicted. Status always also changes shape, stroke, label, or texture. Contrast must be verified in the rendered context; token names are not a WCAG claim.

The sRGB token check on 2026-07-17 measured 12.17:1 for paper trace, 6.26:1 for weathered label, 5.60:1 for oxide copper, and 6.54:1 for glacial glass against mineral slate. The same pairs are stronger against survey black. These token-level ratios pass WCAG AA for normal text, but the built UI still requires rendered-state testing for opacity, compositing, font weight, focus, and chart marks.

Avoid saturated blue-purple gradients, bloom-heavy cyan, and large luminous fog fields. Small luminance changes should carry depth; color carries classification.

### Typography

No downloadable font asset is required for v1.

- Objectives and promoted findings: `ui-serif, Georgia, serif`, sentence case, restrained at 500 weight. The serif is used only for analytical theses, never for navigation.
- Controls and explanations: `system-ui, sans-serif`, 400/600 weights, generous line height.
- IDs, times, costs, and exact measurements: `ui-monospace, SFMono-Regular, Consolas, monospace`, tabular numerals.

The contrast between a thesis voice and an instrument voice is the typographic identity. Do not use wide-tracked all-caps as a default sci-fi signal. Uppercase is reserved for short machine states of four characters or fewer.

### Spacing and geometry

- Base spacing: 4 px; scale: 4, 8, 12, 16, 24, 32, 48.
- Panel radius: 3 px; large floating cards and pill-shaped containers are avoided.
- Borders: one-pixel mineral rules. The active panel receives two short copper witness marks at opposite corners instead of a glow.
- Touch targets: minimum 44 by 44 CSS px even when the visible icon is smaller.
- Dense data rows remain 32 px high only when an adjacent keyboard/search path exposes the same action with a 44 px target.

## Layout

The canvas is the work surface, with stable analytical trays around it. The lower timeline is a scrub instrument, not a decorative footer.

```text
+------------------------------------------------------------------+
| Run thesis | state | exact runtime / tokens / cost | connection   |
+-------------+--------------------------------------+--------------+
| Explorer    |                                      | Inspector    |
| branches    |      procedural galaxy canvas        | evidence     |
| filters     |      + evidence apertures             | provenance   |
| text tree   |                                      | artifacts    |
|             |                                      | actions      |
+-------------+--------------------------------------+--------------+
| event scale / replay / live edge / lag / causal receipts          |
+------------------------------------------------------------------+
```

The explorer and inspector may collapse, but the run thesis and connection/lag state remain visible. On narrow screens, the canvas becomes one view among tabs; the text tree is never hidden behind an inaccessible map-only mode.

## Logo construction

The first-party mark is an open aperture crossed by a single offset survey chord. Three unequal witness ticks sit on the aperture; only two are connected. This represents selected relationships in a larger, deliberately incomplete observation.

Construct it from strokes and circles on a 32-unit grid with round caps, no starburst, no rocket, and no letter monogram. Use one color at small sizes. Generate the SVG from repository-owned vector instructions and record it in the asset manifest when it ships.

## Procedural visual families

### Systems and stars

Systems are quiet luminous discs inside the evidence aperture. A seeded combination of core size, one asymmetric occlusion notch, and two low-opacity grain bands creates variety. Avoid photographic flares, multi-point fantasy stars, and constant pulsing.

Lifecycle encoding:

| State | Non-color treatment | Motion |
|---|---|---|
| Proposed | Open aperture; dotted outer arc | None |
| Queued | Single clock notch | None |
| Working | Solid inner disc; rotating progress notch | Rotation follows real progress only |
| Waiting/approval | Square witness mark | One transition, then still |
| Completed | Closed evidence segments; check notch | Short settle, then still |
| Failed | Broken inner disc and fault slash | One causal fracture, then still |

### Artifact planets

Planets are **data seals**, not miniature realistic worlds. A consistent circular body receives one family mark:

- dataset/table: horizontal sampling bands;
- chart: one rising trace cut into the disc;
- notebook/code: paired vertical gutters;
- model: triangulated cell pattern;
- report/markdown: offset folio edge;
- reproduction bundle: double enclosure;
- external link/other: open boundary.

Dataset versions share a family texture and differ by a small ordinal notch. Moons use compact tool/validation glyphs and aggregate below the system zoom.

### Agents, fleets, and probes

Agents use an original **sampling caliper** silhouette: an asymmetric open U-frame, a narrow central sensor, and one short trailing counterweight. It reads as an instrument rather than a naval ship or arrowhead. Role is encoded by the sensor insert; status by the outline and wake.

Movement is literal:

- traveling: moves along the assigned relationship with a single fading sampling wake;
- working: docks at the system's evidence aperture;
- waiting: remains still with an ochre square witness mark;
- handoff: the receiving probe departs only when the handoff event exists;
- failed: remains at the failure location with a broken sensor mark;
- completed: returns or docks only when that state is present in telemetry.

### Major structures

High-value synthesis uses a **crossbeam array**: two offset beams around a central data wafer. Additional beams represent validated evidence packages, never arbitrary building complexity. The shape is reserved for promoted outputs and must remain rare.

### Hyperlanes and territories

Relationships are evidence traces, differentiated by dash/cap pattern and direction marks as well as color. Supporting and contradicting edges must remain distinguishable in monochrome.

Territories are low-opacity survey isolines with sparse edge ticks. They indicate semantic grouping, not ownership. Use stable cluster envelopes or alpha shapes; do not fill the map with faction colors. When grouping changes, interpolate only if motion is enabled and the semantic change is real.

### Background and particles

Generate the field from deterministic, low-frequency noise plus a sparse survey grid. Dust points are static per run seed. There are no downloaded nebula photographs, random shooting stars, or ambient particle storms. At most one local concentration band may frame the home system, and it must not compete with labels.

## Semantic zoom and asset sizes

| Tier | Typical on-screen size | Required treatment |
|---|---:|---|
| Distant | 6–10 px | Systems, major structures, territories, active probes; no planet detail |
| Regional | 12–28 px | Evidence apertures, significant planets, typed trace patterns, anomaly marks |
| System | 24–64 px | Planet family marks, moons, local lineage, docked probe state |
| Inspector | 96–160 px | High-detail procedural seal with exact text adjacent, never text baked into texture |

Every family needs a silhouette test at 8, 16, 32, and 64 CSS px on survey black and in high contrast. Prefer vector/procedural drawing for small marks; use atlases only after profiling demonstrates a benefit.

## Motion language

Motion communicates causality:

- 120–180 ms for focus and hover response;
- 240–360 ms for state transitions;
- distance-based travel with a capped duration and explicit start/end events;
- no ambient camera drift, breathing panels, decorative orbiting, or perpetual star pulse;
- pause stops visual motion while event ingestion continues;
- reduced motion replaces travel with origin/destination emphasis and an immediate position update.

Only one orchestrated moment is allowed: when a finding is promoted, its evidence path resolves outward-to-inward once, then the scene returns to stillness.

## Icon and chart treatment

Icons use 1.5 px strokes on a 24-unit grid, round caps, and one intentional open corner. Filled icons are reserved for destructive or blocking state. Sanitize SVG and add the accessible name in UI code; do not bake labels into SVG files.

Charts use survey black or paper-trace light surfaces, mineral gridlines, direct labels, and the semantic overlay colors. Contradicting series also receive a dash pattern. Decorative gradients and 3D chart effects are prohibited.

## Production pipeline

1. Author first-party SVG primitives or deterministic generator code. Record author, generator path, seed strategy, and source checksum.
2. Normalize to a 24- or 64-unit design grid. Run silhouette and monochrome tests before adding texture.
3. Produce LOD variants from one canonical source; do not hand-edit derivatives.
4. If profiling justifies raster atlases, render with a pinned toolchain, stable sort order, fixed color profile, premultiplied-alpha policy, and deterministic packing.
5. Export transparent PNG for GPU sprite atlases; optionally add WebP/AVIF for standalone previews only when browser decoding and visual quality are verified.
6. Generate 1x/2x outputs and record dimensions, bytes, MIME type, and SHA-256 for every shipped file.
7. Run asset verification, SVG sanitization, contrast checks, atlas-bleed tests, and visual regression at DPR 1 and 2.
8. Add every shipped file to `asset-manifest.json`. Third-party sources additionally require primary-source license evidence and exact attribution.
9. Review the integrated screenshots against [originality-review.md](./originality-review.md) before release.

Do not begin a mixed-pack 3D pipeline by default. If later usability testing requires richer probe sprites, commission or create one coherent first-party family. A third-party 3D source is admitted only after the license gate, then normalized in a scripted Blender pipeline with the original palette, fixed camera, consistent lighting, documented LOD, and preserved checksums.

## Accessibility and calm-under-load rules

- Paper trace on survey black is the default text pair; weathered label is not used for small critical text without measured contrast.
- Selection uses copper marks plus focus outline and label change.
- Failure, contradiction, validation, waiting, and active states each have a distinct glyph/pattern.
- The synchronized text tree, search, inspector, and tables expose every canvas entity and relationship.
- Canvas focus is mirrored into the text alternative; keyboard focus never disappears into a draw surface.
- User font scaling must not clip controls or exact metrics.
- At high activity, coalesce visual updates and show exact counts/lag. Never communicate load through faster decorative motion.
