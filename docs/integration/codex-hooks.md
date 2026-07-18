# Codex hooks

The hook command is intentionally fast and fail-open. It parses one documented JSON object from stdin, redacts it, writes one atomically named file to a local outbox, and exits `0` without contacting the API. The Local Private companion drains and retries this outbox automatically. Duplicate hook invocations resolve to the same event ID and outbox filename.

## Install

1. Install the companion and managed hooks, then start it when needed:

```powershell
evolastra service install
evolastra service start
```

2. Start a new Codex session, open `/hooks`, inspect the exact command, and trust it. Project hooks load only for trusted projects. Do not use the trust-bypass flag for normal installation.
3. Use `evolastra codex status` and `evolastra service status` for diagnostics.

The installer merges registrations into `~/.codex/hooks.json`, preserves unrelated hooks, and can be rerun safely. The example files remain useful for manual installations.

There is deliberately no remote connector command. Hooks always write locally, and only the user's loopback companion drains their outbox.

Content-shaped fields (prompts, inputs, outputs, transcripts, and response text) are redacted by default. `--capture-content` is an explicit local opt-in; secret-shaped fields remain redacted.

The currently documented hook events are `SessionStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, and `Stop`. Only command handlers execute today, matching hooks can run concurrently, and asynchronous command hooks are not currently supported. These details come from the current [Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks).

## Health diagnostics

Exercise capture without Codex:

```powershell
Get-Content -Raw examples/integrations/fixtures/codex_hook_session_start.json | python -m integrations.codex_hooks --spool "$env:TEMP/asterism-hook-check" capture
Get-ChildItem "$env:TEMP/asterism-hook-check"
python -m integrations.codex_hooks --spool "$env:TEMP/asterism-hook-check" flush --endpoint "http://127.0.0.1:8000/api/v1/events" --once
```

- A new `evt_*.json` proves local capture works.
- Files disappearing after a successful flush proves delivery/acknowledgement works.
- Remaining files mean delivery has not been acknowledged; inspect server availability and endpoint configuration.
- Codex skips changed hooks until they are reviewed again. Use `/hooks` after every command change.

## Uninstall

Remove only the Asterism handler entries from `hooks.json` or `config.toml`, restart Codex, and confirm they no longer appear in `/hooks`. Stop the flusher. Review the local outbox before deleting it; it may contain undelivered redacted telemetry. Setting `[features] hooks = false` disables every Codex hook and is broader than uninstalling this adapter.

The adapter never reads the transcript path. The documented transcript format is not a stable hook interface and is intentionally unsupported.
