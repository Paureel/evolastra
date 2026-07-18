# Originality review

Status: **direction-level review complete; source-level integration review has open blockers**
Reviewed: 2026-07-17

## Result

The proposed direction passes the originality gate at specification level. It is an analytical “quiet survey instrument” built from evidence apertures, data seals, sampling-caliper probes, crossbeam arrays, and survey isolines. These devices derive from the product's provenance and evidence tasks rather than from a commercial space-strategy interface.

No product UI, artwork, screenshots, game files, third-party visual packs, or final rendered assets existed at the initial review. A Canvas component was added concurrently and has now received the source-level review below. This is still not a certification of an integrated build: the implementation-level gate remains open and must use actual screenshots at distant, regional, and system zoom.

## Source-level integration review

Reviewed source: `apps/web/src/components/GalaxyCanvas.tsx` on 2026-07-17. This review did not edit application code.

Aligned foundations:

- custom Canvas 2D keeps procedural rendering first-party and introduces no external visual asset;
- reduced-motion and high-contrast inputs exist;
- the canvas has a summary label and points to a complete nonvisual text-tree alternative;
- the palette is dark, restrained, and broadly compatible with the quiet-instrument direction.

Open blockers:

1. Every animated agent receives sinusoidal positional drift and slow rotation independent of an assignment, travel, handoff, or other observable event. This can imply work that did not occur. Replace it with event-bound movement; reduced motion should use immediate state changes.
2. The current filled agent polygon reads as an arrowhead/ship. Replace it with the asymmetric open sampling-caliper silhouette and verify it at 16, 32, and 64 px.
3. Selection is a complete white circular ring. Replace it with the broken evidence aperture and non-color state/path marks.
4. Edges currently share one undifferentiated stroke. Add relationship-specific dash/cap/direction treatment that remains legible in monochrome.
5. Systems do not yet render the evidence-coverage aperture, and artifact families are mostly distinguished by a generic ellipse. Add the semantic family marks before claiming the direction is implemented.

These are visual-originality and semantic-honesty blockers, not a request to replace the Canvas renderer.

## Constraint-by-constraint review

| Area | Direction-level finding | Integration evidence required |
|---|---|---|
| Overall composition | Evidence workbench with stable explorer, canvas, inspector, and causal timeline; avoids a game HUD/cockpit composition. | Desktop and narrow screenshots with panels open/closed. |
| Color system | Low-saturation mineral slate, paper trace, copper, and glacial glass; no neon blue-purple overload. | Token export and contrast report from the built UI. |
| Icon silhouettes | Open-corner scientific line marks; filled shapes reserved for blocking state. | Complete icon contact sheet at 16/24/32 px. |
| Agent silhouettes | Asymmetric sampling caliper, not a rocket, arrowhead, naval hull, or recognizable franchise craft. | Eight directions or runtime rotation at 16/32/64 px. |
| Territories | Unfilled survey isolines and edge ticks communicate grouping, not political ownership. | Incremental-layout recordings showing stable borders. |
| Stars/systems | Occluded discs plus evidence apertures; no photographic lens flare or fantasy starburst. | Seeded system contact sheet and reduced-motion capture. |
| Typography | Serif only for theses; system sans for UI and mono for exact values; no bespoke game-like display face. | Type-scale specimen at 100%, 200%, and high contrast. |
| Notifications | Inline causal receipts and a quiet lag/connection state, not stacked spectacle alerts. | Success, warning, error, approval, and stream-gap states. |
| Selection | Broken evidence aperture with aligned path ticks, not a generic glowing ring. | Mouse, keyboard, multi-select, and search-focus states. |
| Agent movement | Movement begins and ends on observable assignment/handoff events; no random roaming. | Event-to-animation trace and paused/reduced-motion variants. |
| Hyperlanes | Typed evidence traces use dash, cap, and direction marks. | Monochrome screenshot proving relationship distinctions. |
| System labels | Research-task titles with instrument-like secondary metrics, not fictional place names. | Collision and semantic-zoom screenshots. |
| Sound identity | No sound is proposed for v1. | If added later, run a separate provenance and originality review. |

## Forbidden-material check

- No Stellaris assets, screenshots, extracted files, logos, ship designs, icons, typography, shaders, sounds, terminology, or copied screen layouts may enter the repository.
- No prompt, filename, public metadata, or marketing copy may describe the product as imitating that game.
- No asset may be sourced from fan-art sites, image search, gameplay captures, mod packages, or model-rip archives.
- Avoid common imitation signals in combination: empire-colored filled territories, ornate top bars, constant blue bloom, heraldic faction shields, naval ship silhouettes, and densely framed sci-fi chrome.
- Inspiration screenshots used for an internal review must not be committed or redistributed unless separately licensed.

## Final integration checklist

An independent reviewer should complete this before release:

- [ ] Compare a full-screen screenshot at all three zoom tiers with the approved visual direction.
- [ ] Confirm every visible visual is first-party procedural or has an approved manifest record.
- [ ] Run the icon, agent, system, territory, label, selection, and notification contact-sheet review.
- [ ] Verify the same scene in normal, high-contrast, paused, and reduced-motion modes.
- [ ] Verify status and edge meaning in grayscale and with color-vision-deficiency simulation.
- [ ] Search source, metadata, filenames, alt text, and public copy for prohibited imitation language.
- [ ] Confirm no trademark, logo, UI capture, extracted asset, or recognizable third-party silhouette is present.
- [ ] Record reviewer, date, build/commit, screenshots, exceptions, and approval outcome below.

## Integrated review record

Not approved. Source-level blockers are listed above; screenshot review has not run. Required fields for the final record: reviewer, date, commit/build ID, browser, screenshot locations, exceptions, remediation, and final approval state.
