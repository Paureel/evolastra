# Plan: public three-empire showcase

_A deliberately narrow, sanitized demo that works before local pairing_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

Visitors can choose a read-only three-empire STAD showcase from the connection
screen and inspect its map, replay, findings, and figures without a local
companion. Private and user-authored analyses remain local-only.

## Context

The hosted web app currently contains viewer code only. This change creates one
explicit architecture exception for a versioned, aggregate-only public fixture.
It must not become a general upload, persistence, or hosted-analysis surface.

Relevant boundaries: [architecture invariants](../../architecture/invariants.md),
[privacy model](../../security/privacy-model.md), and
[web instructions](../../../apps/web/AGENTS.md).

## Scope

- Included: one allowlisted public JSON bundle, unpaired demo entry, local
  replay/search, read-only federation presentation, bounded figure previews.
- Excluded: raw CNA rows, sample identifiers, prompts, tool output, credentials,
  remote APIs, hosted persistence, and mutations while viewing the showcase.

## Steps

- [x] Add and validate the sanitized public showcase bundle.
- [x] Add unpaired read-only loading, replay, search, figures, and federation UI.
- [x] Encode the narrow hosted-content exception in architecture and security checks.
- [x] Update product documentation and complete focused and release validation.

## Decisions and surprises

- The showcase is a same-origin static asset, so Netlify can serve it without a
  backend, database, account, or pairing ceremony.
- The asset contains curated aggregate results and synthetic display entities;
  it is not an export of the private STAD run.
- The release migration smoke test previously reused `data/asterism.db`; it now
  receives a disposable temporary database and artifact directory so verification
  cannot mutate or be blocked by operator state.

## Validation

- `npm run check` — passed: harness, Ruff, mypy, 126 Python tests, TypeScript,
  and 45 Vitest tests.
- `npm --prefix apps/web run test:e2e -- --grep "public three-empire showcase"`
  — passed with the installed companion stopped and restored around the run.
- `npm run verify` — passed: the checks above, isolated Alembic smoke migration,
  production Vite build, zero npm/pip audit findings, 7 Playwright tests including
  accessibility, asset verification, and the focused security scan.
- `git diff --check` — passed before handoff.
