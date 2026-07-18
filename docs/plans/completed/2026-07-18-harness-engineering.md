# Plan: harness-engineer the Evolastra repository

_Implementation record for the repository's agent control plane_

---

Status: completed
Owner: Codex
Last updated: 2026-07-18

## 🎯 Outcome

Make Evolastra legible and self-checking for coding agents through progressive
instructions, an authoritative repository map, executable architecture rules,
fast feedback commands, versioned plans, and CI enforcement.

## 📍 Scope

- Included: agent guidance, architecture boundaries, repository diagnostics,
  Markdown links, plan lifecycle, command ladder, tests, and CI.
- Excluded: product behavior, event semantics, UI redesign, and deployment model.

## 💡 Decisions and surprises

- The existing release gate was comprehensive but provided no fast repository
  shape or architecture check.
- Installation guidance dominated the root agent file, so it became a concise
  index with local instructions closer to each major code surface.
- Architecture rules were encoded with a small standard-library script to keep
  feedback available before project dependencies are installed.

## ✅ Validation

- `npm run doctor`: all required tools and installed dependencies ready
- `npm run harness`: eight repository checks passed
- `npm run check`: 105 Python tests and 26 Vitest tests passed with lint and typing
- `npm run verify`: fast checks plus migration, build, three Playwright scenarios, security scans, and dependency audits passed
- `git diff --check`: clean
