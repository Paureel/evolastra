from __future__ import annotations

import io
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import urlopen

from asterism_api.database import SessionLocal
from asterism_api.event_store import EventStore
from asterism_api.main import app
from uvicorn import Config, Server

from integrations.codex_hooks import capture_stdin, flush_once


def test_codex_session_start_reaches_the_local_live_projection() -> None:
    output = Path.cwd() / "output"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        spool = Path(directory) / "outbox"
        with SessionLocal() as session:
            EventStore(session).reset()
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = int(reservation.getsockname()[1])
        server = Server(Config(app, host="127.0.0.1", port=port, log_level="error"))
        worker = threading.Thread(target=server.run, daemon=True)
        worker.start()
        try:
            for _ in range(50):
                try:
                    with urlopen(  # noqa: S310 - fixed test loopback URL
                        f"http://127.0.0.1:{port}/health/live", timeout=0.2
                    ):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise AssertionError("test API did not start")

            payload = {
                "hook_event_name": "SessionStart",
                "session_id": "session_local_live_projection",
                "cwd": "C:/workspace/local-analysis",
            }
            previous_stdin = sys.stdin
            try:
                sys.stdin = io.StringIO(json.dumps(payload))
                assert capture_stdin(spool=spool) == 0
            finally:
                sys.stdin = previous_stdin
            assert flush_once(
                spool=spool,
                endpoint=f"http://127.0.0.1:{port}/api/v1/events",
            ) == (2, 0)
            with urlopen(  # noqa: S310 - fixed test loopback URL
                f"http://127.0.0.1:{port}/api/v1/runs", timeout=1
            ) as response:
                runs = json.loads(response.read().decode("utf-8"))["items"]
            matching = [run for run in runs if run["title"] == "Codex · local-analysis"]
            assert len(matching) == 1
            assert matching[0]["status"] == "running"
            assert matching[0]["last_sequence"] == 2
        finally:
            server.should_exit = True
            worker.join(timeout=3)
            with SessionLocal() as session:
                EventStore(session).reset()


def test_codex_prompt_and_stop_capture_complete_the_turn() -> None:
    output = Path.cwd() / "output"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        spool = Path(directory) / "outbox"
        common = {
            "session_id": "session_turn_lifecycle",
            "turn_id": "turn_lifecycle_001",
            "cwd": "C:/workspace/local-analysis",
        }
        previous_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(
                json.dumps({**common, "hook_event_name": "UserPromptSubmit", "prompt": "test"})
            )
            assert capture_stdin(spool=spool) == 0
            sys.stdin = io.StringIO(json.dumps({**common, "hook_event_name": "Stop"}))
            assert capture_stdin(spool=spool) == 0
        finally:
            sys.stdin = previous_stdin

        events = [json.loads(path.read_text(encoding="utf-8")) for path in spool.glob("evt_*.json")]
        by_type = {event["type"]: event for event in events}
        assert "galaxy.analysis.node.created.v1" in by_type
        assert "galaxy.analysis.node.started.v1" in by_type
        assert "galaxy.analysis.node.completed.v1" in by_type
        assert (
            by_type["galaxy.analysis.node.completed.v1"]["data"]["node"]["id"]
            == by_type["galaxy.analysis.node.created.v1"]["data"]["node"]["id"]
        )
        assert by_type["galaxy.analysis.node.completed.v1"]["data"]["node"]["progress"] == 1
