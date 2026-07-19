# Plan: restore the three-empire STAD showcase

_Execution context, decisions, progress, and validation evidence_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

The hosted STAD CNA showcase opens as an intelligible twelve-phase expedition,
renders all nested semantic systems, and visibly grows three distinct empires.

## Context

The aggregate fixture already contained three players, six figures, and six
hypotheses, but exposed only four replay steps. The galaxy layout also discarded
nested nodes, so most claimed systems and two empire territories had no spatial
position even though their records were present.

## Scope

- Included: public showcase replay metadata, nested semantic layout, three
  branch-capital claims, entry copy, timeline labels, and regressions.
- Excluded: local companion event semantics and any patient-level or private
  STAD data.

## Steps

- [x] Define and validate twelve named public replay phases.
- [x] Position all semantic nodes and reveal three territories as phases advance.
- [x] Clarify the STAD CNA expansion before demo entry.
- [x] Run focused, repository, browser, and production verification.

## Decisions and surprises

- Replay phases are explicit presentation metadata. Durable event sequence
  semantics remain unchanged, preserving the boundary between the public static
  projection and local analytical history.
- Semantic parent relationships remain authoritative for provenance; the galaxy
  projection now positions nested nodes instead of treating nesting as a reason
  to omit them.
- The original fixture was not missing results. Its nested nodes were omitted by
  the disposable layout and its public replay metadata stopped at four.

## Validation

- `npm --prefix apps/web run typecheck` — passed.
- `npm --prefix apps/web test -- --run src/layout.test.ts src/showcase.test.ts src/components/ConnectionPanel.test.tsx` — 19 tests passed.
- `.\.venv\Scripts\python.exe -m pytest tests/test_public_showcase.py tests/test_harness.py -q` — 16 tests passed.
- `npm --prefix apps/web run test:e2e -- --grep "public three-empire showcase"` — passed.
- Playwright CLI snapshot and `output/playwright/stad-showcase-fixed.png` — visually confirmed 13 systems and three distinct territory colors.
- `npm run check` — passed (130 Python tests and 46 web tests).
- `npm run verify` — passed, including 7 browser tests, accessibility, audits, build, security scan, and locked-dependency audit.
- `git diff --check` — passed.
