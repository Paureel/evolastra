# Agent instructions for Evolastra

_Repository-wide setup and engineering contract for coding agents_

---

## 📋 First actions

When asked to install, start, connect, or diagnose Evolastra:

1. Read this file and [`docs/getting-started.md`](docs/getting-started.md).
2. Confirm the checkout is on Windows and run the non-mutating prerequisite check:

   ```powershell
   npm run bootstrap:check
   ```

3. Install and start Evolastra without opening a browser from the agent session:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -NoBrowser
   ```

4. Verify both states:

   ```powershell
   & .\.venv\Scripts\evolastra.exe service status
   & .\.venv\Scripts\evolastra.exe codex status
   ```

5. If hooks were newly installed or changed, tell the user to restart Codex once, open `/hooks`, and approve the Evolastra commands. Do not claim that the current session is captured when it began before hook activation.
6. Generate a pairing code only when the user is ready to enter it:

   ```powershell
   & .\.venv\Scripts\evolastra.exe pair
   ```

7. Report the viewer URL, companion state, hook state, registered origins, and autostart state. Never report or read the root companion token.

## 🔐 Preserve the privacy boundary

- Keep the API, database, outbox, tokens, and analysis artifacts on loopback and local storage.
- Never read, print, copy, or expose `~/.evolastra/companion-token`.
- Never commit `.env`, databases, pairing state, private datasets, generated exports, or `stad_data/`.
- Never add a remote API, serverless ingestion route, telemetry exporter, or cloud database without explicit authorization to change the local-only architecture.
- Treat one-use pairing codes as short-lived credentials: show them only to the requesting user and never store them.
- Do not run `npm run reset` or uninstall hooks/services unless the user explicitly requests that state change.

## 🔧 Development workflow

For ordinary development after bootstrap:

```powershell
npm run demo
```

Use `npm run dev` for an empty observatory. Before committing a change, run the focused tests for the affected surface and then:

```powershell
npm run verify
```

Preserve these boundaries:

- Operational telemetry records execution facts.
- The semantic graph records analytical meaning and provenance.
- The visualization projection owns coordinates, camera state, and animation.
- Corrections are new events; durable history is not rewritten.

## ✅ Completion criteria

An installation task is complete only when:

- `service status` reports `installed: true` and `running: true`.
- `codex status` reports all managed hook events installed, unless `-NoHooks` was explicitly requested.
- The user has been told about any required Codex restart and `/hooks` approval.
- The browser pairing step is explained without exposing the root token.
- No private data or credentials were added to Git.

Use the bundled [`evolastra` skill](skills/evolastra/SKILL.md) when it is available; its controller is preferred for diagnosis and state repair.
