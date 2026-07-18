# Local Private deployment

Local Private is the default end-user deployment. The static interface may be served by Netlify or another CDN, but analysis data is written only to the companion on the user's computer.

The public site is presentation code only. It has no ingestion endpoint, server database, or server-side analysis process. The viewer's runtime policy rejects non-loopback API addresses.

## Data path

```text
Codex hook -> private local outbox -> Evolastra companion -> local SQLite
                                                        -> paired browser tab
```

The hook never contacts the network. It writes redacted CloudEvents to `~/.codex/evolastra-outbox`. The companion drains that directory, persists events beneath `~/.evolastra`, and serves REST plus resumable SSE on loopback. Raw prompt, response, transcript, and tool content remain capture-disabled by default; semantic titles and summaries are still application data.

## Install and start

Run from an installed checkout:

```powershell
& .\.venv\Scripts\evolastra.exe service install
& .\.venv\Scripts\evolastra.exe service start
& .\.venv\Scripts\evolastra.exe service status
```

Installation merges managed handlers into `~/.codex/hooks.json` without replacing unrelated hooks. The companion starts only when you run `evolastra service start`; it does not start with Windows by default. Restart Codex and review/trust the changed hooks through `/hooks`.

The hooks are user-level, so every later Codex session on this computer joins the running companion automatically. Each session becomes a separate live analysis run. Use `evolastra service status` to confirm the companion is running before opening a new session.

To opt into automatic startup at login, reinstall with `evolastra service install --autostart`.

For a static UI hosted at an exact origin, add that origin before pairing:

```powershell
& .\.venv\Scripts\evolastra.exe service install --origin https://your-site.netlify.app
& .\.venv\Scripts\evolastra.exe service stop
& .\.venv\Scripts\evolastra.exe service start
```

Generate a one-use five-minute code:

```powershell
& .\.venv\Scripts\evolastra.exe pair
```

Enter the code in the browser. The returned bearer grant is bound to the requesting origin, expires automatically, and is stored in session storage rather than persistent local storage. The root companion token remains in a user-private file and is never returned to the browser.

The browser talks directly to `127.0.0.1`; analysis traffic does not pass through the static host. The static host can still receive ordinary asset-request metadata such as IP address, user agent, and timestamps in its access logs.

## Portable analyses

Open **Advanced → Save / load**. **Save analysis** downloads one `.evolastra` file containing the redacted durable event history. **Load analysis** imports that file into this or another Evolastra instance and reconstructs replay, maps, findings, and provenance. The importer is bounded, accepts only the Evolastra manifest and JSONL members, and never extracts or executes archive content.

## Operations

```powershell
& .\.venv\Scripts\evolastra.exe codex status
& .\.venv\Scripts\evolastra.exe codex install
& .\.venv\Scripts\evolastra.exe codex uninstall
& .\.venv\Scripts\evolastra.exe service stop
& .\.venv\Scripts\evolastra.exe service uninstall
```

Uninstalling the service removes any optional managed startup entry and its hook registrations. It deliberately preserves `~/.evolastra/data`, the root token, logs, and any undelivered outbox files so data is not destroyed implicitly.

## Browser requirements

The hosted page must be HTTPS and its exact origin must be on the companion allowlist. Modern browsers may ask for local-network access when an HTTPS page first connects to loopback. Evolastra answers the Private Network Access preflight only for allowlisted origins. Browser policy can still disable loopback access in managed environments; in that case use the UI served locally by Evolastra.
