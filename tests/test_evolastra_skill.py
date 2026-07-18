from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from skills.evolastra.scripts import evolastra_control


def test_skill_accepts_hosted_https_and_rejects_remote_http() -> None:
    assert evolastra_control.normalize_origin("https://evolastra.com/") == (
        "https://evolastra.com"
    )
    assert evolastra_control.normalize_origin("http://127.0.0.1:8000") == (
        "http://127.0.0.1:8000"
    )
    with pytest.raises(ValueError, match="HTTPS"):
        evolastra_control.normalize_origin("http://evolastra.com")


def test_registering_an_origin_restarts_a_running_companion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    status_calls = 0

    def fake_run_cli(_launcher: list[str], *arguments: str) -> dict[str, Any]:
        nonlocal status_calls
        calls.append(arguments)
        if arguments == ("service", "status"):
            status_calls += 1
            return {
                "installed": True,
                "running": True,
                "autostart": False,
                "allowed_origins": [] if status_calls == 1 else ["https://evolastra.com"],
            }
        if arguments == ("service", "start"):
            return {"installed": True, "running": True}
        if arguments == ("codex", "status"):
            return {"installed": True, "events": 10}
        return {}

    monkeypatch.setattr(evolastra_control, "run_cli", fake_run_cli)
    args = SimpleNamespace(
        origin="https://evolastra.com",
        port=8000,
        no_hooks=False,
        autostart=False,
    )

    result = evolastra_control.ensure(["evolastra"], args)

    assert result["registered_origin"] is True
    assert ("service", "stop") in calls
    assert ("service", "start") in calls
