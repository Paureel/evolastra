from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "PostCompact",
    "Stop",
)
MATCHED_EVENTS = frozenset(HOOK_EVENTS) - {"SessionStart", "UserPromptSubmit", "Stop"}
MANAGED_MARKER = "integrations.codex_hooks"


def _command(python: str, spool: Path, *, windows: bool) -> str:
    parts = [python, "-m", "integrations.codex_hooks", "--spool", str(spool), "capture"]
    if windows:
        return subprocess_list2cmdline(parts)
    return shlex.join(parts)


def subprocess_list2cmdline(parts: list[str]) -> str:
    import subprocess

    return subprocess.list2cmdline(parts)


def managed_hook(
    python: str, spool: Path, *, windows: bool | None = None
) -> dict[str, Any]:
    is_windows = os.name == "nt" if windows is None else windows
    windows_command = _command(python, spool, windows=True)
    return {
        "type": "command",
        # Some Codex releases parse the generic command before applying the
        # Windows override. Keep both fields Windows-native on Windows so the
        # generic fallback cannot fail on POSIX single-quote syntax.
        "command": _command(python, spool, windows=is_windows),
        "commandWindows": windows_command,
        "timeout": 5,
        "statusMessage": "Updating Evolastra live observatory",
    }


def _is_managed(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(item, dict)
        and MANAGED_MARKER in f"{item.get('command', '')} {item.get('commandWindows', '')}"
        for item in hooks
    )


def install_codex_hooks(
    *,
    config_path: Path | None = None,
    spool: Path | None = None,
    python: str | None = None,
) -> dict[str, Any]:
    destination = (config_path or Path("~/.codex/hooks.json")).expanduser().resolve()
    outbox = (spool or Path("~/.codex/evolastra-outbox")).expanduser().resolve()
    interpreter = str(Path(python or sys.executable).resolve())
    destination.parent.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(destination.read_text(encoding="utf-8")) if destination.exists() else {}
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Cannot safely update {destination}: {exc}") from exc
    hooks = existing.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise RuntimeError(f"Cannot safely update {destination}: hooks must be an object")
    command = managed_hook(interpreter, outbox)
    for event_name in HOOK_EVENTS:
        entries = hooks.setdefault(event_name, [])
        if not isinstance(entries, list):
            raise RuntimeError(f"Cannot safely update {destination}: {event_name} must be a list")
        entries[:] = [entry for entry in entries if not _is_managed(entry)]
        registration: dict[str, Any] = {"hooks": [command]}
        if event_name in MATCHED_EVENTS:
            registration["matcher"] = "*"
        entries.append(registration)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    return {
        "installed": True,
        "config": str(destination),
        "spool": str(outbox),
        "events": len(HOOK_EVENTS),
    }


def uninstall_codex_hooks(config_path: Path | None = None) -> dict[str, Any]:
    destination = (config_path or Path("~/.codex/hooks.json")).expanduser().resolve()
    if not destination.exists():
        return {"installed": False, "config": str(destination), "removed": 0}
    try:
        existing = json.loads(destination.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Cannot safely update {destination}: {exc}") from exc
    hooks = existing.get("hooks", {})
    removed = 0
    if isinstance(hooks, dict):
        for event_name, entries in list(hooks.items()):
            if not isinstance(entries, list):
                continue
            kept = [entry for entry in entries if not _is_managed(entry)]
            removed += len(entries) - len(kept)
            if kept:
                hooks[event_name] = kept
            else:
                hooks.pop(event_name, None)
    destination.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return {"installed": False, "config": str(destination), "removed": removed}


def codex_hook_status(config_path: Path | None = None) -> dict[str, Any]:
    destination = (config_path or Path("~/.codex/hooks.json")).expanduser().resolve()
    if not destination.exists():
        return {"installed": False, "config": str(destination), "events": 0}
    try:
        existing = json.loads(destination.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"installed": False, "config": str(destination), "events": 0, "invalid": True}
    hooks = existing.get("hooks", {})
    count = 0
    if isinstance(hooks, dict):
        count = sum(
            1
            for entries in hooks.values()
            if isinstance(entries, list)
            for entry in entries
            if _is_managed(entry)
        )
    return {"installed": count == len(HOOK_EVENTS), "config": str(destination), "events": count}
