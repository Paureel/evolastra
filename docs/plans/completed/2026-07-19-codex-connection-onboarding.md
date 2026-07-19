# Plan: human and agent connection onboarding

_Execution context, decisions, progress, and validation evidence_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

First-time visitors can tell that connecting real Codex work requires one local
installation, then follow audience-specific instructions for either a human or
a Codex agent without leaving the pairing screen.

## Context

The hosted viewer previously showed only a pairing field and a terse command.
It did not explain prerequisites, installation, hosted-origin configuration, or
the human trust actions required after an agent completes setup. The repository
is now public, so anonymous cloning is the supported first step.

## Scope

- Included: human and agent setup tabs, copyable setup commands and prompt,
  machine-readable hosted instructions, public-repository documentation,
  browser coverage, privacy assertions, and responsive presentation.
- Excluded: silent installation from the browser and automation of Codex hook
  approval or one-time pairing entry.

## Steps

- [x] Confirm the supported public installation, hook, and pairing commands.
- [x] Add human and agent onboarding paths to the hosted connection dialog.
- [x] Publish `/agent-setup.md` and `/llms.txt` and align repository guidance.
- [x] Verify desktop, mobile, privacy, accessibility, and release behavior.

## Decisions and surprises

- The browser cannot and should not silently install local software. The UI says
  this directly and copies a bootstrap command configured for the exact hosted
  origin.
- The agent path pauses at hook approval and pairing because those are deliberate
  human trust actions. It explicitly forbids reading the companion token.
- Removing pairing-field autofocus prevents the scrollable first-run sheet from
  skipping past the installation explanation on entry.
- A production smoke check showed that clipboard permission can be denied even
  on HTTPS, so copy actions fall back to a temporary selected textarea without
  reading clipboard contents.

## Validation

- `npm --prefix apps/web run typecheck` — passed.
- `npm --prefix apps/web run test -- --run src/components/ConnectionPanel.test.tsx` — 2 tests passed.
- `.\.venv\Scripts\python.exe -m pytest tests/test_static_viewer_privacy.py tests/test_bootstrap.py -q` — 5 tests passed.
- `npm --prefix apps/web run test:e2e -- --grep "public three-empire showcase"` — passed.
- Playwright CLI desktop human/agent and 390px mobile screenshots — visually reviewed.
- `npm run check` — passed (131 Python tests and 47 web tests).
- `npm run verify` — passed, including 7 browser tests, accessibility, build,
  security scan, npm audit, and locked Python dependency audit.
- `git diff --check` — passed.
- Production `/agent-setup.md` returned `text/markdown` and `/llms.txt` returned
  `text/plain`, both with the expected hosted-origin instructions.
