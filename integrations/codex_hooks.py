"""Fast, fail-open Codex command hook capture and an out-of-process flusher."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.core import build_event, entity_payload, new_prefixed_id, stable_prefixed_id

HOOK_TYPES = {
    "SessionStart": "galaxy.analysis.run.created.v1",
    "UserPromptSubmit": "galaxy.analysis.node.created.v1",
    "PreToolUse": "galaxy.analysis.toolcall.requested.v1",
    "PermissionRequest": "galaxy.governance.approval.requested.v1",
    "PostToolUse": "galaxy.analysis.toolcall.completed.v1",
    "SubagentStart": "galaxy.analysis.agent.started.v1",
    "SubagentStop": "galaxy.analysis.agent.completed.v1",
    "Stop": "galaxy.analysis.run.completed.v1",
    "PreCompact": "galaxy.integration.codex_compaction.started.v1",
    "PostCompact": "galaxy.integration.codex_compaction.completed.v1",
}
_EVENT_PRIORITY = {
    "galaxy.analysis.run.created.v1": 0,
    "galaxy.analysis.run.started.v1": 1,
    "galaxy.analysis.node.created.v1": 2,
}


def _event_order(path: Path) -> tuple[str, int, int, str]:
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
        return (
            str(event.get("time", "")),
            _EVENT_PRIORITY.get(str(event.get("type", "")), 10),
            path.stat().st_mtime_ns,
            path.name,
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return ("", 99, 0, path.name)


def map_hook(
    payload: Mapping[str, Any],
    *,
    capture_content: bool = False,
    run_id: str | None = None,
    subject_id: str | None = None,
    related_tool_call_id: str | None = None,
    node_id: str | None = None,
    event_type_override: str | None = None,
    native_suffix: str = "",
) -> dict[str, Any]:
    event_name = str(payload.get("hook_event_name") or "Unknown")
    session_id = str(payload.get("session_id") or "")
    turn_id = str(payload.get("turn_id") or "")
    agent_id = str(payload.get("agent_id") or "")
    native_material = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str) + native_suffix
    )
    run_id = run_id or stable_prefixed_id("run", "codex-session", session_id or native_material)
    event_type = event_type_override or HOOK_TYPES.get(
        event_name, "galaxy.integration.codex_hook.received.v1"
    )
    if subject_id:
        subject = subject_id
    elif event_name.startswith("Subagent") and agent_id:
        subject = stable_prefixed_id(
            "agent", "codex-agent", f"{session_id}:{agent_id}"
        )
    elif event_name in {"PreToolUse", "PostToolUse"} and payload.get("tool_use_id"):
        tool_use_id = str(payload.get("tool_use_id") or native_material)
        subject = stable_prefixed_id(
            "tool", "codex-tool-use", f"{session_id}:{tool_use_id}"
        )
    elif event_name == "PermissionRequest" and payload.get("tool_use_id"):
        tool_use_id = str(payload["tool_use_id"])
        subject = stable_prefixed_id(
            "approval", "codex-approval", f"{session_id}:{tool_use_id}"
        )
        related_tool_call_id = related_tool_call_id or stable_prefixed_id(
            "tool", "codex-tool-use", f"{session_id}:{tool_use_id}"
        )
    elif event_name == "UserPromptSubmit" and turn_id:
        subject = stable_prefixed_id("node", "codex-turn", f"{session_id}:{turn_id}")
    else:
        subject = run_id
    data: dict[str, Any] = {
        "hook_event_name": event_name,
        "session_id": session_id or None,
        "turn_id": turn_id or None,
        "native": dict(payload),
        "mapping": {"semantic_candidate": event_name in HOOK_TYPES},
    }
    action = event_type.split(".")[3]
    if event_type.startswith("galaxy.analysis.run.") and session_id:
        workspace = Path(str(payload.get("cwd") or "Codex workspace")).name or "Codex workspace"
        data.update(
            entity_payload(
                "run",
                entity_id=run_id,
                run_id=run_id,
                status=action,
                title=f"Codex · {workspace}"[:300],
                objective="Visualize observable Codex session activity as it happens",
                run_seed=int(hashlib.sha256(run_id.encode()).hexdigest()[:8], 16),
                privacy_classification="internal",
            )
        )
    elif event_type.startswith("galaxy.analysis.node.") and turn_id:
        data.update(
            entity_payload(
                "node",
                entity_id=subject,
                run_id=run_id,
                status=action,
                title=f"Codex turn · {turn_id[-8:]}",
                description="User-directed Codex work. Prompt content is not captured by default.",
                node_type="analysis",
                parent_node_id=None,
                progress=1 if action == "completed" else 0,
            )
        )
    elif event_type.startswith("galaxy.analysis.toolcall.") and payload.get("tool_use_id"):
        data.update(
            entity_payload(
                "tool_call",
                entity_id=subject,
                run_id=run_id,
                status=action,
                node_id=node_id
                or (
                    stable_prefixed_id("node", "codex-turn", f"{session_id}:{turn_id}")
                    if turn_id
                    else None
                ),
                tool_name=payload.get("tool_name"),
            )
        )
    elif event_type.startswith("galaxy.analysis.agent.") and agent_id:
        current_node_id = node_id or (
            stable_prefixed_id("node", "codex-turn", f"{session_id}:{turn_id}")
            if turn_id
            else None
        )
        data.update(
            entity_payload(
                "agent",
                entity_id=subject,
                run_id=run_id,
                status=action,
                name=str(payload.get("agent_type") or "Codex agent")[:120],
                role=str(payload.get("agent_type") or "analysis agent")[:120],
                current_node_id=current_node_id,
                framework="Codex",
            )
        )
    elif event_type.startswith("galaxy.governance.approval.") and related_tool_call_id:
        data.update(
            entity_payload(
                "approval",
                entity_id=subject,
                run_id=run_id,
                status=action,
                tool_call_id=related_tool_call_id,
            )
        )
    elif event_type.startswith(("galaxy.analysis.", "galaxy.governance.")):
        event_type = "galaxy.integration.codex_hook.received.v1"
        data["mapping_limitation"] = "hook payload lacked documented semantic entity identity"
    return build_event(
        event_type=event_type,
        source="urn:asterism:integration:codex-hooks",
        subject=subject,
        run_id=run_id,
        adapter="codex-hooks/0.1.0",
        native_id=native_material,
        correlation_id=session_id or native_material,
        causation_id=turn_id,
        capture_content=capture_content,
        data=data,
    )


def spool_event(event: Mapping[str, Any], spool: str | os.PathLike[str]) -> Path:
    directory = Path(spool).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    integration = (
        event.get("data", {}).get("integration", {})
        if isinstance(event.get("data"), Mapping)
        else {}
    )
    key = integration.get("deduplication_key") if isinstance(integration, Mapping) else None
    filename_key = str(key or event["id"])
    destination = directory / f"evt_{filename_key}.json"
    if destination.exists():
        return destination
    temporary = directory / f".{filename_key}.{os.getpid()}.tmp"
    data = json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    with temporary.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.replace(destination)
    except FileExistsError:
        temporary.unlink(missing_ok=True)
    return destination


def _spooled_id(spool: str | os.PathLike[str], prefix: str, namespace: str, value: str) -> str:
    """Persist native-to-UUIDv4 identity across short-lived hook processes."""

    directory = Path(spool).expanduser() / ".ids"
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{prefix}\0{namespace}\0{value}".encode()).hexdigest()
    destination = directory / key
    if not destination.exists():
        temporary = directory / f".{key}.{os.getpid()}.tmp"
        identifier = new_prefixed_id(prefix)
        with temporary.open("xb") as handle:
            handle.write(identifier.encode("ascii"))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            pass  # noqa: S110 - another hook process already persisted the mapping
        except OSError:
            if not destination.exists():
                temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination.read_text(encoding="ascii").strip()


def capture_stdin(*, spool: str | os.PathLike[str], capture_content: bool = False) -> int:
    """Read one hook object and spool it; always fail open with exit code zero."""

    try:
        raw = sys.stdin.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            return 0
        # Windows PowerShell 5 may pipe an UTF-8 BOM through the console code
        # page as the three visible characters U+00EF/U+00BB/U+00BF.
        if raw.startswith("\u00ef\u00bb\u00bf"):
            raw = raw[3:]
        payload = json.loads(raw.lstrip("\ufeff"))
        if isinstance(payload, dict):
            session_id = str(payload.get("session_id") or "")
            native_material = json.dumps(payload, sort_keys=True, default=str)
            run_id = _spooled_id(spool, "run", "codex-session", session_id or native_material)
            event_name = str(payload.get("hook_event_name") or "Unknown")
            subject_id = None
            related_tool_call_id = None
            node_id = (
                _spooled_id(spool, "node", "codex-turn", f"{session_id}:{payload['turn_id']}")
                if payload.get("turn_id")
                else None
            )
            if event_name.startswith("Subagent") and payload.get("agent_id"):
                subject_id = _spooled_id(
                    spool, "agent", "codex-agent", f"{session_id}:{payload['agent_id']}"
                )
            elif event_name in {"PreToolUse", "PostToolUse"} and payload.get("tool_use_id"):
                tool_use_id = str(payload["tool_use_id"])
                subject_id = _spooled_id(
                    spool, "tool", "codex-tool-use", f"{session_id}:{tool_use_id}"
                )
            elif event_name == "PermissionRequest" and payload.get("tool_use_id"):
                tool_use_id = str(payload["tool_use_id"])
                subject_id = _spooled_id(
                    spool, "approval", "codex-approval", f"{session_id}:{tool_use_id}"
                )
                related_tool_call_id = _spooled_id(
                    spool, "tool", "codex-tool-use", f"{session_id}:{tool_use_id}"
                )
            elif event_name == "UserPromptSubmit" and payload.get("turn_id"):
                subject_id = node_id
            mapped = map_hook(
                payload,
                capture_content=capture_content,
                run_id=run_id,
                subject_id=subject_id,
                related_tool_call_id=related_tool_call_id,
                node_id=node_id,
            )
            spool_event(mapped, spool)
            if event_name == "SessionStart":
                spool_event(
                    map_hook(
                        payload,
                        capture_content=capture_content,
                        run_id=run_id,
                        event_type_override="galaxy.analysis.run.started.v1",
                        native_suffix=":started",
                    ),
                    spool,
                )
            if event_name == "UserPromptSubmit" and node_id:
                spool_event(
                    map_hook(
                        payload,
                        capture_content=capture_content,
                        run_id=run_id,
                        subject_id=node_id,
                        node_id=node_id,
                        event_type_override="galaxy.analysis.node.started.v1",
                        native_suffix=":started",
                    ),
                    spool,
                )
            if event_name == "Stop" and node_id:
                spool_event(
                    map_hook(
                        payload,
                        capture_content=capture_content,
                        run_id=run_id,
                        subject_id=node_id,
                        node_id=node_id,
                        event_type_override="galaxy.analysis.node.completed.v1",
                        native_suffix=":node-completed",
                    ),
                    spool,
                )
    except Exception:  # noqa: S110 - fail-open hooks must not emit output or alter Codex
        # Hooks are noncritical observability. Writing to stderr/stdout can alter
        # Codex hook behavior, so failure is intentionally silent.
        pass
    return 0


def flush_once(
    *,
    spool: str | os.PathLike[str],
    endpoint: str,
    timeout: float = 2.0,
    limit: int = 100,
    bearer_token: str | None = None,
) -> tuple[int, int]:
    """Post pending events. Successful and duplicate responses acknowledge files."""

    parsed_endpoint = urlsplit(endpoint)
    if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.netloc:
        raise ValueError("endpoint must be an absolute HTTP(S) URL")
    if parsed_endpoint.username or parsed_endpoint.password:
        raise ValueError("endpoint credentials must not be embedded in the URL")
    sent = failed = 0
    directory = Path(spool).expanduser()
    pending = (
        sorted(directory.glob("evt_*.json"), key=_event_order)[:limit]
        if directory.exists()
        else []
    )
    for path in pending:
        try:
            body = path.read_bytes()
            headers = {"Content-Type": "application/cloudevents+json"}
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"
            request = Request(  # noqa: S310 - endpoint scheme and authority validated above
                endpoint,
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                with urlopen(request, timeout=timeout) as response:  # noqa: S310 - scheme and authority validated above
                    status = response.status
            except HTTPError as exc:
                status = exc.code
            if 200 <= status < 300 or status == 409:
                path.unlink(missing_ok=True)
                sent += 1
            else:
                failed += 1
        except (OSError, URLError, ValueError):
            failed += 1
    return sent, failed


def flush_loop(
    *, spool: str, endpoint: str, interval: float, timeout: float, bearer_token: str | None = None
) -> int:
    try:
        while True:
            flush_once(
                spool=spool, endpoint=endpoint, timeout=timeout, bearer_token=bearer_token
            )
            time.sleep(max(interval, 0.1))
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spool", default=os.getenv("GALAXY_CODEX_SPOOL", "~/.codex/asterism-outbox")
    )
    parser.add_argument("--capture-content", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("capture")
    flush = subparsers.add_parser("flush")
    flush.add_argument(
        "--endpoint", default=os.getenv("GALAXY_INGEST_URL", "http://127.0.0.1:8000/api/v1/events")
    )
    flush.add_argument("--interval", type=float, default=1.0)
    flush.add_argument("--timeout", type=float, default=2.0)
    flush.add_argument("--once", action="store_true")
    flush.add_argument("--token", default=os.getenv("GALAXY_API_TOKEN"))
    args = parser.parse_args(argv)
    if args.command in (None, "capture"):
        return capture_stdin(spool=args.spool, capture_content=args.capture_content)
    if args.once:
        _, failed = flush_once(
            spool=args.spool,
            endpoint=args.endpoint,
            timeout=args.timeout,
            bearer_token=args.token,
        )
        return 1 if failed else 0
    return flush_loop(
        spool=args.spool,
        endpoint=args.endpoint,
        interval=args.interval,
        timeout=args.timeout,
        bearer_token=args.token,
    )


if __name__ == "__main__":
    raise SystemExit(main())
