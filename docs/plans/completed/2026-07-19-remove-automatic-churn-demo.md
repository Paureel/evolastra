# Plan: remove the automatic churn demo

_Execution context, decisions, progress, and validation evidence_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

Fresh and production sessions never create or select the synthetic churn atlas.
An empty local companion displays an honest empty-analysis state, while the old
simulator remains reachable only through an explicit development workflow.

## Context

The browser automatically called the demo endpoint whenever the local database
contained no runs, then selected the newest run. Seeded churn runs also remained
durable locally and could therefore reappear in a fresh browser tab.

## Scope

- Included: run classification, production filtering, removal of automatic demo
  creation, empty state, explicit development URL, tests, and documentation.
- Excluded: destructive deletion of durable local history.

## Steps

- [x] Expose run tags and classify seeded development runs.
- [x] Remove automatic creation and render the empty state.
- [x] Gate the simulator projection behind an explicit development URL.
- [x] Verify and publish.

## Decisions and surprises

- Existing seeded records remain in SQLite to preserve the append-only history,
  but production surfaces no longer list or select them.
- Development tests opt in with `?development-demo=1`; production builds ignore
  that flag because it is guarded by Vite's development environment.

## Validation

- `npm --prefix apps/web run typecheck` — passed.
- `npm --prefix apps/web run test -- --run src/App.test.tsx` — 2 tests passed.
- `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q` — 4 tests passed.
- Focused Playwright churn-hidden and explicit-development flows — 2 passed.
- `npm run verify` — passed: 132 Python tests, 48 web tests, 8 browser tests,
  accessibility, production build, security scan, npm audit, and locked Python
  dependency audit.
- `git diff --check` — passed.
