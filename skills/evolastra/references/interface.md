# Evolastra interface reference

## Local architecture

```text
Codex hooks -> ~/.codex/evolastra-outbox -> loopback companion
                                                |
                                                +-> ~/.evolastra/data/evolastra.db
                                                +-> ~/.evolastra/artifacts
                                                +-> paired browser via HTTP/SSE

static host -> HTML/CSS/JavaScript -> browser -> http://127.0.0.1:8000
```

The hosted origin does not sit in the analysis-data path. Browser requests for runs, state, imports, exports, commands, and event streams go to loopback.

## Controller actions

Run `scripts/evolastra_control.py <action>`:

| Action | Behavior |
| --- | --- |
| `diagnose` | Read service and managed-hook status without changing state. |
| `ensure` | Install if absent, register `--origin` if supplied, start, and report status. |
| `install` | Install/update the manual-start companion and managed hooks. |
| `start` / `stop` / `status` | Perform the corresponding service operation. |
| `pair` | Create a five-minute, one-use browser pairing code. |

Options:

- `--origin https://viewer.example.com`: register an exact HTTPS hosted origin. Loopback HTTP origins are also accepted.
- `--repo <path>`: identify the Evolastra checkout if automatic discovery fails.
- `--port 8000`: select the loopback port during first installation.
- `--autostart`: use only after explicit user approval.

The controller discovers the installed service's Python interpreter, the repository virtual environment, `EVOLASTRA_REPO`, or an `evolastra` executable on `PATH`. It does not read the root capability token.

## Codex session behavior

Managed user-level hooks cover `SessionStart`, tool/permission lifecycle events, compaction, prompts, subagents, and `Stop`. Hooks spool bounded redacted CloudEvents locally and never call a hosted server. New or changed hooks require a Codex restart plus review/trust through `/hooks`.

If the current task began before the hooks were active, it cannot retroactively emit the missing lifecycle. Start a new Codex task after activation for a complete live run.

## Pairing and browser access

The exact hosted `window.location.origin` must appear in the companion's allowed origins. Run:

```text
python scripts/evolastra_control.py ensure --origin https://evolastra.com
python scripts/evolastra_control.py pair
```

The browser exchanges the code directly with loopback. The returned session grant is origin-bound, expires automatically, and stays in that browser tab's `sessionStorage`. Never substitute the root companion token.

Some browsers display a private-network permission prompt for an HTTPS page accessing loopback. Grant it only for the expected viewer origin.

## Supported local API surfaces

The companion exposes these relevant routes under `http://127.0.0.1:8000/api/v1`:

- `GET /pairing/info` and `POST /pairing/exchange`
- `GET /connection`
- `GET /runs` and `GET /runs/{run_id}/state`
- `GET /runs/{run_id}/events/stream` for resumable SSE
- `POST /events` and `POST /events/batch` for supported local adapters
- `POST /imports/portable`
- `GET /runs/{run_id}/export/evolastra`

Use the managed hooks for Codex rather than inventing direct API calls. For a custom adapter, follow the repository's schemas and SDK, preserve CloudEvent IDs for idempotency, send only to loopback, and use an authorized local integration path. Do not extract the companion token for convenience.

## Portable analyses

A `.evolastra` export contains a redacted, transportable event history. Loading one sends the selected file to the local companion, which validates and imports it into local SQLite. Saving returns a browser download. The static host receives neither direction of transfer.

## Troubleshooting

- `installed: false`: run `ensure`, optionally with `--repo`.
- `running: false`: run `start`; inspect `~/.evolastra/companion.log` only if startup fails.
- `port_conflict: true`: identify the listener before changing or terminating anything.
- Pairing CORS failure: register the exact hosted origin with `ensure --origin ...`, restart the companion, then create a new code.
- No live Codex activity: verify hooks, restart Codex, trust `/hooks`, start a new task, and confirm the local outbox is draining.
- Viewer loads but has no runs: pair the browser and verify it targets loopback, then load a `.evolastra` file or begin a hooked Codex task.
