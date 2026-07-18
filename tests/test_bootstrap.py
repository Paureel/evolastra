from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="The supported bootstrap is Windows-only")
def test_bootstrap_check_is_machine_readable_from_another_directory() -> None:
    powershell = shutil.which("powershell")
    assert powershell is not None
    completed = subprocess.run(  # noqa: S603 - resolved trusted system executable
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "bootstrap.ps1"),
            "-CheckOnly",
        ],
        cwd=ROOT.parent,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(completed.stdout[completed.stdout.index("{") :])
    assert payload["ready"] is True
    assert payload["platform"] == "windows"
    assert Path(payload["repository"]) == ROOT


def test_onboarding_documents_share_the_supported_commands() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "getting-started.md").read_text(encoding="utf-8")

    assert "npm run bootstrap" in readme
    assert "npm run bootstrap:check" in agents
    assert "bootstrap.ps1 -NoBrowser" in agents
    assert "never read or print the root companion token" in guide
    assert "evolastra.exe pair" in guide
