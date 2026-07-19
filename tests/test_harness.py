from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.harness import (
    check_codex_dispatch_boundary,
    check_event_schema_boundaries,
    check_local_private_boundary,
    check_markdown_links,
    check_mermaid_accessibility,
    check_multiplayer_boundary,
    check_plan_lifecycle,
    check_public_showcase_boundary,
    check_python_boundaries,
    check_web_boundaries,
    version_at_least,
)
from scripts.verify import MIGRATION_COMMAND, command_environment

ROOT = Path(__file__).resolve().parents[1]


def test_repository_harness_is_machine_readable_from_another_directory() -> None:
    completed = subprocess.run(  # noqa: S603 - trusted interpreter and repository script
        [sys.executable, str(ROOT / "scripts" / "harness.py"), "check", "--json"],
        cwd=ROOT.parent,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["issues"] == []
    assert payload["checks"]["python_boundaries"] == 0


def test_harness_detects_low_level_python_dependency_reversal(tmp_path: Path) -> None:
    package = tmp_path / "apps" / "api" / "asterism_api"
    package.mkdir(parents=True)
    (package / "reducer.py").write_text("from .api import router\n", encoding="utf-8")

    issues = check_python_boundaries(tmp_path)

    assert any(issue.rule == "ARCH-001" and "api" in issue.message for issue in issues)


def test_harness_detects_stateful_import_in_browser_domain(tmp_path: Path) -> None:
    source = tmp_path / "apps" / "web" / "src"
    source.mkdir(parents=True)
    (source / "layout.ts").write_text('import { listRuns } from "./api";\n', encoding="utf-8")

    issues = check_web_boundaries(tmp_path)

    assert any(issue.rule == "ARCH-003" and "./api" in issue.message for issue in issues)


def test_harness_detects_broken_relative_document_link(tmp_path: Path) -> None:
    document = tmp_path / "docs" / "guide.md"
    document.parent.mkdir(parents=True)
    document.write_text("Read [the missing contract](../contract.md).\n", encoding="utf-8")

    issues = check_markdown_links(tmp_path)

    assert len(issues) == 1
    assert issues[0].rule == "HARNESS-002"
    assert issues[0].path == "docs/guide.md:1"


def test_harness_detects_inaccessible_supported_mermaid_diagram(tmp_path: Path) -> None:
    document = tmp_path / "docs" / "flow.md"
    document.parent.mkdir(parents=True)
    document.write_text("```mermaid\nflowchart LR\n    start --> done\n```\n", encoding="utf-8")

    issues = check_mermaid_accessibility(tmp_path)

    assert len(issues) == 1
    assert issues[0].rule == "HARNESS-004"
    assert "accTitle:" in issues[0].message
    assert "accDescr:" in issues[0].message


def test_harness_detects_visualization_state_in_event_schema(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas" / "events"
    schema_dir.mkdir(parents=True)
    (schema_dir / "event.json").write_text(
        json.dumps({"type": "object", "properties": {"camera": {"type": "object"}}}),
        encoding="utf-8",
    )

    issues = check_event_schema_boundaries(tmp_path)

    assert any(issue.rule == "ARCH-004" and "camera" in issue.message for issue in issues)


def test_harness_detects_public_network_binding(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "serve.py"
    script.parent.mkdir(parents=True)
    all_interfaces = ".".join(("0", "0", "0", "0"))
    script.write_text(f'HOST = "{all_interfaces}"\n', encoding="utf-8")

    issues = check_local_private_boundary(tmp_path)

    assert any(issue.rule == "ARCH-005" for issue in issues)


def test_harness_detects_networked_or_escalated_codex_dispatch(tmp_path: Path) -> None:
    path = tmp_path / "apps" / "api" / "asterism_api" / "codex_dispatch.py"
    path.parent.mkdir(parents=True)
    path.write_text('COMMAND = ["app-server", "--listen", "ws://127.0.0.1", "danger-full-access"]\n', encoding="utf-8")

    issues = check_codex_dispatch_boundary(tmp_path)

    assert issues
    assert all(issue.rule == "ARCH-006" for issue in issues)
    assert any("ws://" in issue.message for issue in issues)
    assert any("danger-full-access" in issue.message for issue in issues)


def test_harness_detects_persisted_multiplayer_member_grant(tmp_path: Path) -> None:
    package = tmp_path / "apps" / "api" / "asterism_api"
    migration = tmp_path / "migrations" / "versions"
    package.mkdir(parents=True)
    migration.mkdir(parents=True)
    (package / "multiplayer.py").write_text(
        'host.endswith(".ts.net")\ntrust_env=False\n', encoding="utf-8"
    )
    (package / "multiplayer_api.py").write_text(
        'prefix="/api/v1/federation"\n"tailscale-user-login"\ndependencies=[Depends(_tailnet_request)]\n',
        encoding="utf-8",
    )
    (package / "db_models.py").write_text("member_token = Column(Text)\n", encoding="utf-8")
    (migration / "20260718_0002_multiplayer.py").write_text("pass\n", encoding="utf-8")

    issues = check_multiplayer_boundary(tmp_path)

    assert any(issue.rule == "ARCH-007" and "must not be persisted" in issue.message for issue in issues)


def test_harness_rejects_unallowlisted_or_private_public_showcase_content(tmp_path: Path) -> None:
    folder = tmp_path / "apps" / "web" / "public" / "demo"
    folder.mkdir(parents=True)
    (folder / "stad-three-empires-v1.json").write_text(
        json.dumps({
            "id": "stad-three-empires-v1",
            "public": True,
            "run": {"id": "demo_run", "privacy_class": "public"},
            "prompt": "private material",
        }),
        encoding="utf-8",
    )
    (folder / "another-analysis.json").write_text("{}", encoding="utf-8")

    issues = check_public_showcase_boundary(tmp_path)

    assert any(issue.rule == "ARCH-008" and "only the allowlisted" in issue.message for issue in issues)
    assert any(issue.rule == "ARCH-008" and "forbidden public field" in issue.message for issue in issues)


def test_harness_detects_incomplete_plan_metadata(tmp_path: Path) -> None:
    active = tmp_path / "docs" / "plans" / "active"
    completed = tmp_path / "docs" / "plans" / "completed"
    active.mkdir(parents=True)
    completed.mkdir(parents=True)
    (active / "work.md").write_text("Status: completed\n", encoding="utf-8")

    issues = check_plan_lifecycle(tmp_path)

    assert {issue.message for issue in issues} == {
        "Status must be 'active'",
        "Owner metadata is required",
        "Last updated must use YYYY-MM-DD",
        "Validation section is required",
    }


def test_version_floor_accepts_longer_and_rejects_older_versions() -> None:
    assert version_at_least("Python 3.12.4", (3, 12))
    assert version_at_least("v20.10.0", (20,))
    assert not version_at_least("9.9.0", (10,))


def test_dependency_using_root_commands_pin_the_repository_python() -> None:
    scripts = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["scripts"]
    for name in (
        "api",
        "benchmark",
        "check",
        "demo",
        "dev",
        "lint",
        "migrate",
        "reset",
        "security",
        "seed",
        "test",
        "test-integration",
        "typecheck",
        "verify",
        "verify-assets",
    ):
        assert ".venv\\Scripts\\python.exe" in scripts[name], name


def test_release_migration_smoke_test_uses_disposable_state(tmp_path: Path) -> None:
    environment = command_environment(MIGRATION_COMMAND, tmp_path)

    assert environment is not None
    assert environment["ASTERISM_DATABASE_URL"].endswith("/migration-smoke.db")
    assert environment["ASTERISM_ARTIFACT_ROOT"].replace("\\", "/").endswith("/artifacts")
