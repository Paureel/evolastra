# Plan: stable galaxy replay

_Keep revealed systems and their ownership visually fixed as the STAD showcase evolves_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

Timeline playback adds systems without moving any system already revealed, so
territories expand coherently and prior ownership remains visually stable.

## Context

`showcaseStateAtSequence` correctly preserves visible nodes and claims. The
drift originated in the disposable visualization layer: each phase passed only
its visible semantic nodes into the stress layout, which then recentered and
rescaled the entire set. Territory contours faithfully followed those changed
coordinates, making stable claims look unstable.

## Scope

- Included: run-scoped galaxy coordinates, replay stability, ownership
  regression coverage, projection documentation.
- Excluded: canonical event schemas, stored coordinates, semantic claim logic,
  and system-view orbital animation.

## Steps

- [x] Reproduce phase-to-phase movement and isolate the projection recompute.
- [x] Preserve issued system positions and align new semantic systems to them.
- [x] Verify claims persist and the semantic-neighborhood quality is retained.
- [x] Run the release gate and prepare the verified change for publication.

## Decisions and surprises

- A hash-only coordinate replacement kept positions stable but reduced the STAD
  semantic-distance Spearman score from at least 0.8 to 0.380, so it was
  rejected.
- Coordinates remain disposable and local to the renderer. The durable event
  stream and multiplayer claims remain authoritative.
- The first full release gate found that Playwright reused an already-running
  paired companion on port 8000, so browser setup received 401 before opening
  the UI. Browser tests now own an isolated development API on port 8011 and
  select it through session-scoped browser state. Production and installed
  companions retain the hard-coded, privacy-checked port 8000 default.

## Validation

- `npm --prefix apps/web test -- src/showcase.test.ts src/layout.test.ts`:
  21 tests passed, including the actual 12-phase public STAD asset.
- `npm --prefix apps/web run typecheck`: passed.
- `npm run check`: passed (132 Python tests and 50 frontend tests at the focused
  iteration point).
- `npm run verify`: passed (132 Python tests, 51 frontend tests, production
  build, dependency audits, security scan, and all 8 Playwright tests).
