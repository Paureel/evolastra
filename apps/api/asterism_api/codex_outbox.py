from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .access import configured_root_token
from .config import Settings

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


def drain_outbox_once(settings: Settings, *, limit: int = 100) -> tuple[int, int]:
    spool = settings.codex_spool.expanduser().resolve()
    if not spool.exists():
        return 0, 0
    token = configured_root_token(settings)
    endpoint = f"http://127.0.0.1:{settings.companion_port}/api/v1/events"
    sent = failed = 0
    pending = sorted(spool.glob("evt_*.json"), key=_event_order)
    for source in pending[:limit]:
        claimed = source.with_name(f".{source.name}.{os.getpid()}.sending")
        try:
            source.replace(claimed)
        except (FileNotFoundError, FileExistsError, PermissionError):
            continue
        try:
            headers = {"Content-Type": "application/cloudevents+json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            request = Request(  # noqa: S310 - fixed loopback URL
                endpoint, data=claimed.read_bytes(), headers=headers, method="POST"
            )
            try:
                with urlopen(request, timeout=2.0) as response:  # noqa: S310 - fixed loopback URL
                    status = response.status
            except HTTPError as exc:
                status = exc.code
            if 200 <= status < 300 or status == 409:
                claimed.unlink(missing_ok=True)
                sent += 1
            else:
                claimed.replace(source)
                failed += 1
        except (OSError, URLError, ValueError):
            if claimed.exists() and not source.exists():
                claimed.replace(source)
            failed += 1
    return sent, failed


async def drain_outbox_loop(settings: Settings) -> None:
    while True:
        await asyncio.sleep(0.75)
        await asyncio.to_thread(drain_outbox_once, settings)
