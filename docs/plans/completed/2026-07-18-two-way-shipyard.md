# Plan: two-way Codex shipyard

_Persistent ships and user-dispatched Codex tasks from the Evolastra observatory_

---

Status: completed
Owner: Codex
Last updated: 2026-07-18

## 🎯 Outcome

Users can click the starting system's central star, build a Codex-backed ship,
enter a mission, and launch a new local Codex thread. Completed tech-tree nodes
unlock specialist ship blueprints derived from that analytical problem.

## 📋 Context

The Local Private companion already authenticates paired browser state changes
and captures Codex lifecycle hooks. Codex app-server is the documented rich-client
surface for starting threads and turns with the user's existing Codex login.

## 📍 Scope

- Included: default and research-unlocked blueprints, persisted ship agents,
  shipyard UI, Codex app-server stdio client, mission lifecycle events, tests,
  security boundary, and documentation.
- Excluded: remote listeners, automatic permission escalation, browser access to
  Codex credentials, fleet combat, resources/build time, and autonomous recurring
  missions.

## ✍️ Steps

- [x] Implement deterministic blueprint and prompt contracts
- [x] Add paired build and dispatch endpoints
- [x] Add app-server lifecycle and semantic mission events
- [x] Add central-star shipyard and tech-tree launch controls
- [x] Verify focused, browser, security, and release gates

## 💡 Decisions and surprises

- Use app-server over local stdio, never a WebSocket listener.
- Omit the model so new threads inherit the user's configured Codex model.
- Use `workspace-write` with approval policy `never`; missions can work inside the
  repository but cannot silently escalate beyond it.
- Persist mission prompts under the `prompt` key so Evolastra's default content
  redaction keeps private instructions out of the semantic event log.
- Record the running lifecycle event before starting the completion monitor, so
  even a near-instant task cannot finish out of order.
- Treat the tech progression as an accessible region of ordinary controls rather
  than applying an invalid ARIA tree pattern to adjacent build actions.

## ✅ Validation

- Real signed-in Codex app-server mission: completed over stdio and persisted as a local rollout
- `npm run check`: 110 Python tests, 27 Vitest tests, lint, typing, and nine harness checks passed
- `npm run verify`: production build, four Playwright scenarios, Axe scan, security and asset scans, and both dependency audits passed
- Browser inspection: command-star drydock, core hull construction, and research hull selection verified
- `git diff --check`: clean
