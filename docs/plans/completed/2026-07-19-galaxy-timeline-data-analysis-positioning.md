# Plan: galaxy timeline and data-analysis positioning

_Execution context, decisions, progress, and validation evidence_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

Galaxy view exposes a compact, synchronized replay control at the bottom of the
map, while the README and GitHub metadata clearly position Evolastra as a tool
for agentic data analysis presented as a space strategy game.

## Context

Replay was only directly controllable from Advanced view. The repository copy
led with the game metaphor but did not establish data analysis as the primary
use case early enough.

## Scope

- Included: shared replay transport, galaxy overlay, responsive styling,
  browser regression, README opening copy, and GitHub repository description.
- Excluded: replay semantics, event persistence, and other map controls.

## Steps

- [x] Share replay controls between Galaxy and Advanced views.
- [x] Add restrained desktop and mobile galaxy styling plus browser coverage.
- [x] Reframe repository copy around agentic data analysis.
- [x] Verify, publish, and inspect the deployed result.

## Decisions and surprises

- The galaxy control is an instrument strip rather than another full footer, so
  it remains visible without competing with the selected-system brief.
- Galaxy and Advanced views render one shared transport component against the
  same state; switching views cannot desynchronize their replay position.
- At narrow widths, the transport drops its status sentence and button text but
  keeps explicit accessible names and both endpoint labels.

## Validation

- `npm --prefix apps/web run typecheck` — passed.
- `npm --prefix apps/web run test` — 46 tests passed.
- `npm --prefix apps/web run test:e2e -- --grep "live galaxy and system maps"` — passed.
- Playwright CLI snapshots at 1280px and 390px plus
  `output/playwright/galaxy-timeline-{desktop,mobile}.png` — visually reviewed.
- `npm run check` — passed (130 Python tests and 46 web tests).
- `npm run verify` — passed, including 7 browser tests, accessibility, build,
  security scan, npm audit, and locked Python dependency audit.
- `git diff --check` — passed.
- `gh repo view Paureel/evolastra --json description` — confirmed data-analysis
  positioning in repository metadata.
