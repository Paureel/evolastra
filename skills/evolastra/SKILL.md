---
name: evolastra
description: Operate and connect the local-first Evolastra analysis observatory. Use when Codex needs to install, start, stop, pair, diagnose, or verify the Evolastra companion; connect a Codex session to a local or Netlify/VPS-hosted Evolastra viewer; explain the hooks/outbox/live-view data flow; or help load, save, export, and troubleshoot portable `.evolastra` analyses without placing analysis data on the hosted server.
---

# Evolastra

Operate Evolastra as a static hosted viewer backed by a companion, database, Codex hooks, and files on the user's own computer.

## Control the companion

Run the bundled controller instead of reconstructing commands:

```powershell
python <skill-directory>/scripts/evolastra_control.py diagnose
python <skill-directory>/scripts/evolastra_control.py ensure
python <skill-directory>/scripts/evolastra_control.py ensure --origin https://evolastra.com
python <skill-directory>/scripts/evolastra_control.py pair
```

Use `diagnose` first for status questions. Use `ensure` when the user asks to connect, run, or prepare Evolastra; it installs when needed, starts the companion, and verifies Codex hooks. Pass the exact viewer origin—scheme and host, without a path—to `--origin` for a hosted site.

Use `start`, `stop`, `status`, or `install` only when the requested state change specifically calls for them. Do not enable autostart unless the user explicitly requests it.

## Connect Codex

1. Ensure the companion is installed and running.
2. Confirm `hooks.installed` is true in controller output.
3. If hooks were newly installed or changed, tell the user to restart Codex, review `/hooks`, and trust the commands. Do not claim the current session is captured when it started before hook activation.
4. For a browser connection, generate a one-use code with `pair` and give it only to the user who requested it. Do not store it.
5. Tell the user to open the viewer and enter the code. The grant is short-lived and browser-origin-bound.

Codex lifecycle hooks write redacted events to the local outbox. The companion drains the outbox into local SQLite and streams projections to the paired browser. Never configure a remote event destination.

## Preserve the privacy boundary

- Treat the hosted site as static presentation code only.
- Keep the API on loopback (`127.0.0.1` or `localhost`).
- Never deploy the Python API, SQLite database, connector, outbox, token, or analysis files to Netlify/VPS.
- Never read, print, copy, or place `~/.evolastra/companion-token` in a prompt, hook, URL, log, or configuration. Pair through `evolastra pair` instead.
- Do not add remote API URLs, proxies, serverless ingestion functions, telemetry exporters, or cloud storage unless the user explicitly changes the local-only architecture.
- Describe ordinary static-host access logs separately from analysis storage; they can include IP, asset path, user agent, and timestamp but must not contain analysis content.

## Interface with analyses

Use the viewer for normal interaction:

- **Live work:** hooks feed the running local companion automatically.
- **Load:** open **Advanced → Save / load → Load analysis** and select a local `.evolastra` file.
- **Save:** use **Save analysis** to download a portable `.evolastra` file.
- **Replay:** select the run and use the replay controls on the timeline.

File selection sends the analysis from browser memory to the loopback companion, not to the hosted origin. Each visitor's `localhost` resolves to that visitor's own machine.

Read [references/interface.md](references/interface.md) when diagnosing paths, pairing/CORS, custom adapter ingestion, hosted-origin setup, or portable analysis behavior.

## Report completion

State the service URL, running state, hook state, registered viewer origins, and autostart state. Mention any required Codex restart or browser pairing. Never include access tokens or private analysis content.
