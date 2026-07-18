# Agent instructions for Evolastra

_Repository-wide navigation and engineering contract for coding agents_

---

This file is the repository entry point, not an encyclopedia. Follow the links
that match the surface you are changing and prefer executable repository facts
over assumptions.

## 🎯 Start every task

1. Run `npm run doctor` after setup, or `npm run bootstrap:check` before setup.
2. Read the [repository map](docs/architecture/repository-map.md).
3. Read the nearest nested `AGENTS.md` for the files in scope.
4. For cross-cutting or multi-session work, create an active plan from
   [the plan template](docs/plans/template.md).
5. Run the smallest relevant test while editing, then `npm run check`.

## 📍 Knowledge map

| Need | Read |
| --- | --- |
| Product and install | [README](README.md), [Getting started](docs/getting-started.md) |
| System boundaries | [Architecture overview](docs/architecture/overview.md), [invariants](docs/architecture/invariants.md) |
| Where a change belongs | [Repository map](docs/architecture/repository-map.md) |
| Agent feedback loop | [Harness guide](docs/development/harness.md) |
| Tests and release gate | [Testing strategy](docs/development/testing.md) |
| Local-private security | [Privacy model](docs/security/privacy-model.md), [threat model](docs/security/threat-model.md) |
| Active and completed work | [Plans](docs/plans/README.md) |

Local instructions:

- [API companion](apps/api/AGENTS.md)
- [Web observatory](apps/web/AGENTS.md)
- [Event schemas](schemas/AGENTS.md)
- [Tests](tests/AGENTS.md)

## 🛡️ Non-negotiable invariants

- Durable events and the semantic projection are authoritative; spatial views
  are disposable projections.
- Corrections append new events. Never rewrite durable analytical history.
- Operational telemetry records execution facts; it does not promote semantic
  findings.
- Coordinates, camera state, and animation stay out of canonical event schemas.
- The companion, database, outbox, tokens, and analysis artifacts stay local and
  loopback-only unless the user explicitly authorizes an architecture change.
- Never read, print, copy, or expose `~/.evolastra/companion-token`.
- Never commit credentials, databases, pairing state, generated exports, private
  datasets, or `stad_data/`.

These rules are mapped to executable checks in
[architecture invariants](docs/architecture/invariants.md). If a check blocks an
intentional architecture change, update the decision record, documentation,
check, and regression tests together; do not route around the check.

## 🔧 Supported commands

```powershell
npm run doctor        # tools and installed dependency diagnosis
npm run harness       # repository knowledge and architecture invariants
npm run check         # fast preflight: harness, static checks, unit tests
npm run verify        # complete release gate including browser and audits
```

For a fresh Windows checkout:

```powershell
npm run bootstrap:check
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -NoBrowser
```

After hook installation or changes, tell the user to restart Codex once and
approve the managed commands in `/hooks`. Generate a one-use browser pairing
code only when the user is ready with `.\.venv\Scripts\evolastra.exe pair`.

## ✅ Definition of done

- Focused regression coverage passes.
- `npm run check` passes during iteration.
- `npm run verify` passes before handoff or push.
- User-facing behavior, decisions, and active plan state are updated.
- `git diff --check` is clean and no local/private data is staged.
