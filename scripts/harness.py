from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    "AGENTS.md",
    "LICENSE",
    "SECURITY.md",
    "apps/api/AGENTS.md",
    "apps/web/AGENTS.md",
    "schemas/AGENTS.md",
    "tests/AGENTS.md",
    "docs/architecture/invariants.md",
    "docs/architecture/repository-map.md",
    "docs/development/harness.md",
    "docs/plans/README.md",
    "docs/plans/template.md",
)

# These modules form the stable, low-level API core. Adding a dependency is an
# architecture decision: update the relevant invariant and its tests explicitly.
PYTHON_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "access.py": {"config"},
    "config.py": set(),
    "database.py": {"config", "db_models"},
    "db_models.py": {"database"},
    "exports.py": {"db_models"},
    "ids.py": set(),
    "reducer.py": set(),
    "schemas.py": set(),
    "security.py": set(),
}

WEB_DOMAIN_MODULES = (
    "connection.ts",
    "galaxyFrontier.ts",
    "layout.ts",
    "mapBrief.ts",
    "mapGraph.ts",
    "replay.ts",
    "spatial.ts",
    "techTree.ts",
    "types.ts",
)
WEB_FORBIDDEN_IMPORTS = ("./App", "./api", "./components", "./hooks")
VISUALIZATION_FIELDS = {
    "animation",
    "camera",
    "camera_position",
    "galaxy_coordinates",
    "layout_coordinates",
    "pitch",
    "screen_position",
    "viewport",
    "yaw",
    "zoom",
}

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
MERMAID_BLOCK = re.compile(r"```mermaid\s*\n([\s\S]*?)```", re.IGNORECASE)
IMPORT_SOURCE = re.compile(r"^\s*import(?:\s+type)?[\s\S]*?\sfrom\s+[\"']([^\"']+)[\"']", re.MULTILINE)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALL_INTERFACES = ".".join(("0", "0", "0", "0"))
CODEX_DISPATCH_REQUIRED = (
    '"app-server"',
    '"--listen"',
    '"stdio://"',
    '"sandbox": "workspace-write"',
    '"approvalPolicy": "never"',
    '"developerInstructions": self.developer_instructions',
    '"web_search": "disabled"',
    '"networkAccess": False',
    "env=sanitized_subprocess_environment()",
)
CODEX_DISPATCH_FORBIDDEN = ("danger-full-access", "http://", "https://", "ws://", "wss://")
MULTIPLAYER_REQUIRED = (
    'host.endswith(".ts.net")',
    'trust_env=False',
    '"tailscale-user-login"',
    'prefix="/api/v1/federation"',
)
PUBLIC_SHOWCASE_PATH = Path("apps/web/public/demo/stad-three-empires-v1.json")
PUBLIC_SHOWCASE_ID = "stad-three-empires-v1"
PUBLIC_SHOWCASE_FORBIDDEN_KEYS = {
    "authorization",
    "completion",
    "cookie",
    "database_url",
    "filename",
    "pairing_code",
    "password",
    "prompt",
    "raw_content",
    "sample_id",
    "token",
    "tool_input",
    "tool_output",
    "transcript",
}
PUBLIC_SAMPLE_ID = re.compile(r"\bTCGA-[A-Z0-9]{2}-[A-Z0-9]{4}\b", re.IGNORECASE)


@dataclass(frozen=True)
class Issue:
    rule: str
    path: str
    message: str


@dataclass(frozen=True)
class DoctorItem:
    name: str
    ok: bool
    required: bool
    detail: str
    remedy: str | None = None


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def check_required_paths(root: Path) -> list[Issue]:
    return [
        Issue("HARNESS-001", path, "required repository guidance or harness file is missing")
        for path in REQUIRED_PATHS
        if not (root / path).exists()
    ]


def markdown_target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return raw.split(maxsplit=1)[0]


def markdown_documents(root: Path) -> list[Path]:
    ignored = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".pytest-tmp",
        ".ruff_cache",
        ".venv",
        ".verify-venv",
        "dist",
        "env",
        "node_modules",
        "playwright-report",
        "test-results",
        "venv",
    }
    documents: list[Path] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(directory for directory in directories if directory not in ignored)
        documents.extend(Path(current) / filename for filename in sorted(files) if filename.endswith(".md"))
    return documents


def check_markdown_links(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for document in markdown_documents(root):
        content = document.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(content):
            target = markdown_target(match.group(1))
            parsed = urlparse(target)
            if not target or target.startswith("#") or parsed.scheme or target.startswith("//"):
                continue
            path_text = unquote(target.split("#", 1)[0]).replace("/", os.sep)
            if not path_text:
                continue
            destination = (document.parent / path_text).resolve()
            if not destination.exists():
                line = content.count("\n", 0, match.start()) + 1
                issues.append(
                    Issue(
                        "HARNESS-002",
                        f"{relative(root, document)}:{line}",
                        f"relative Markdown target does not exist: {target}",
                    )
                )
    return issues


def check_mermaid_accessibility(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    unsupported = (
        "architecture",
        "block",
        "kanban",
        "mindmap",
        "packet",
        "quadrantchart",
        "radar-beta",
        "sankey-beta",
        "timeline",
        "treemap-beta",
        "xychart-beta",
    )
    for document in markdown_documents(root):
        content = document.read_text(encoding="utf-8")
        for match in MERMAID_BLOCK.finditer(content):
            diagram = match.group(1)
            first_line = next((line.strip().casefold() for line in diagram.splitlines() if line.strip()), "")
            if first_line.startswith(unsupported):
                continue
            missing = [field for field in ("accTitle:", "accDescr:") if field not in diagram]
            if missing:
                line = content.count("\n", 0, match.start()) + 1
                issues.append(
                    Issue(
                        "HARNESS-004",
                        f"{relative(root, document)}:{line}",
                        f"Mermaid diagram is missing {', '.join(missing)}",
                    )
                )
    return issues


def python_internal_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level and node.module:
            imports.add(node.module.split(".", 1)[0])
        elif node.level and not node.module:
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif node.module and node.module.startswith("asterism_api."):
            imports.add(node.module.split(".", 2)[1])
    return imports


def check_python_boundaries(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    package = root / "apps" / "api" / "asterism_api"
    for filename, allowed in PYTHON_INTERNAL_IMPORTS.items():
        path = package / filename
        if not path.exists():
            continue
        for imported in sorted(python_internal_imports(path) - allowed):
            issues.append(
                Issue(
                    "ARCH-001",
                    relative(root, path),
                    f"low-level module imports disallowed internal module '{imported}'",
                )
            )

    integrations = root / "integrations"
    for path in sorted(integrations.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = ""
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            elif isinstance(node, ast.Import):
                module = ",".join(alias.name for alias in node.names)
            if "asterism_api" in module:
                issues.append(
                    Issue(
                        "ARCH-002",
                        relative(root, path),
                        "protocol adapters must not depend on the companion implementation",
                    )
                )
    return issues


def check_web_boundaries(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    source = root / "apps" / "web" / "src"
    for filename in WEB_DOMAIN_MODULES:
        path = source / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for imported in IMPORT_SOURCE.findall(content):
            if imported.startswith(WEB_FORBIDDEN_IMPORTS):
                issues.append(
                    Issue(
                        "ARCH-003",
                        relative(root, path),
                        f"deterministic browser module imports stateful UI surface '{imported}'",
                    )
                )
    return issues


def iter_property_names(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            found.extend(str(key) for key in properties)
        for child in value.values():
            found.extend(iter_property_names(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(iter_property_names(child))
    return found


def check_event_schema_boundaries(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path in sorted((root / "schemas" / "events").glob("*.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            issues.append(Issue("ARCH-004", relative(root, path), f"invalid JSON: {error}"))
            continue
        leaked = sorted(set(iter_property_names(schema)) & VISUALIZATION_FIELDS)
        if leaked:
            issues.append(
                Issue(
                    "ARCH-004",
                    relative(root, path),
                    f"durable event schema contains visualization-owned fields: {', '.join(leaked)}",
                )
            )
    return issues


def check_local_private_boundary(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    candidates = [
        *sorted((root / "apps" / "api").rglob("*.py")),
        *sorted((root / "scripts").glob("*.py")),
        *sorted((root / "scripts").glob("*.ps1")),
    ]
    for path in candidates:
        content = path.read_text(encoding="utf-8")
        if ALL_INTERFACES in content:
            issues.append(
                Issue(
                    "ARCH-005",
                    relative(root, path),
                    "local-private runtime must not bind all network interfaces",
                )
            )
    return issues


def check_codex_dispatch_boundary(root: Path) -> list[Issue]:
    path = root / "apps" / "api" / "asterism_api" / "codex_dispatch.py"
    if not path.exists():
        return [Issue("ARCH-006", relative(root, path), "Codex dispatch boundary is missing")]
    content = path.read_text(encoding="utf-8")
    issues = [
        Issue("ARCH-006", relative(root, path), f"required Codex boundary is missing: {token}")
        for token in CODEX_DISPATCH_REQUIRED
        if token not in content
    ]
    issues.extend(
        Issue("ARCH-006", relative(root, path), f"Codex dispatch uses forbidden transport or permission: {token}")
        for token in CODEX_DISPATCH_FORBIDDEN
        if token in content
    )
    return issues


def check_multiplayer_boundary(root: Path) -> list[Issue]:
    implementation = root / "apps" / "api" / "asterism_api" / "multiplayer.py"
    routes = root / "apps" / "api" / "asterism_api" / "multiplayer_api.py"
    persistence = (
        root / "apps" / "api" / "asterism_api" / "db_models.py",
        root / "migrations" / "versions" / "20260718_0002_multiplayer.py",
    )
    issues: list[Issue] = []
    content = ""
    for path in (implementation, routes):
        if not path.exists():
            issues.append(Issue("ARCH-007", relative(root, path), "multiplayer boundary file is missing"))
        else:
            content += path.read_text(encoding="utf-8")
    for token in MULTIPLAYER_REQUIRED:
        if token not in content:
            issues.append(
                Issue("ARCH-007", relative(root, implementation), f"required multiplayer boundary is missing: {token}")
            )
    if "dependencies=[Depends(_tailnet_request)]" not in content:
        issues.append(
            Issue("ARCH-007", relative(root, routes), "federation routes must require the tailnet request gate")
        )
    for path in persistence:
        if path.exists() and "member_token" in path.read_text(encoding="utf-8"):
            issues.append(
                Issue("ARCH-007", relative(root, path), "raw multiplayer member grants must not be persisted")
            )
    return issues


def check_public_showcase_boundary(root: Path) -> list[Issue]:
    path = root / PUBLIC_SHOWCASE_PATH
    folder = path.parent
    issues: list[Issue] = []
    if not path.exists():
        return [Issue("ARCH-008", relative(root, path), "the allowlisted public showcase is missing")]
    unexpected = [item for item in folder.rglob("*") if item.is_file() and item != path]
    issues.extend(
        Issue("ARCH-008", relative(root, item), "only the allowlisted public showcase may be hosted")
        for item in unexpected
    )
    if path.stat().st_size > 150_000:
        issues.append(Issue("ARCH-008", relative(root, path), "public showcase exceeds 150 KB"))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as reason:
        return [*issues, Issue("ARCH-008", relative(root, path), f"public showcase is invalid JSON: {reason}")]
    if not isinstance(payload, dict) or payload.get("id") != PUBLIC_SHOWCASE_ID or payload.get("public") is not True:
        issues.append(Issue("ARCH-008", relative(root, path), "public showcase identity and public marker are required"))
    run = payload.get("run", {}) if isinstance(payload, dict) else {}
    if not isinstance(run, dict) or run.get("privacy_class") != "public":
        issues.append(Issue("ARCH-008", relative(root, path), "public showcase run must use the public privacy class"))
    state = payload.get("state", {}) if isinstance(payload, dict) else {}
    replay = payload.get("replay", {}) if isinstance(payload, dict) else {}
    phases = replay.get("phases", []) if isinstance(replay, dict) else []
    if not isinstance(state, dict) or state.get("last_sequence") != 12 or not isinstance(replay, dict) or replay.get("last_sequence") != 12:
        issues.append(Issue("ARCH-008", relative(root, path), "public showcase must expose the complete twelve-phase replay"))
    if not isinstance(phases, list) or len(phases) != 12 or any(
        not isinstance(phase, dict)
        or phase.get("sequence") != index
        or not isinstance(phase.get("label"), str)
        or not isinstance(phase.get("node_ids"), list)
        for index, phase in enumerate(phases, start=1)
    ):
        issues.append(Issue("ARCH-008", relative(root, path), "public showcase replay phases must be ordered, named, and mapped to systems"))
    multiplayer = payload.get("multiplayer", {}) if isinstance(payload, dict) else {}
    players = multiplayer.get("players", []) if isinstance(multiplayer, dict) else []
    claims = multiplayer.get("claims", []) if isinstance(multiplayer, dict) else []
    player_ids = {player.get("id") for player in players if isinstance(player, dict)} if isinstance(players, list) else set()
    claim_owners = {claim.get("player_id") for claim in claims if isinstance(claim, dict)} if isinstance(claims, list) else set()
    if len(player_ids) != 3 or claim_owners != player_ids:
        issues.append(Issue("ARCH-008", relative(root, path), "public showcase must contain visible claims for exactly three empires"))

    def inspect(value: Any, location: str = "$") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = key.casefold()
                if normalized in PUBLIC_SHOWCASE_FORBIDDEN_KEYS:
                    issues.append(Issue("ARCH-008", relative(root, path), f"forbidden public field at {location}.{key}"))
                is_identifier = normalized == "id" or normalized.endswith("_id")
                if is_identifier and isinstance(item, str) and item and item != PUBLIC_SHOWCASE_ID and not item.startswith("demo_"):
                    issues.append(Issue("ARCH-008", relative(root, path), f"non-demo identifier at {location}.{key}"))
                if normalized == "values" and isinstance(item, list) and len(item) > 12:
                    issues.append(Issue("ARCH-008", relative(root, path), f"preview exceeds 12 rows at {location}.{key}"))
                inspect(item, f"{location}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                inspect(item, f"{location}[{index}]")
        elif isinstance(value, str) and PUBLIC_SAMPLE_ID.search(value):
            issues.append(Issue("ARCH-008", relative(root, path), f"sample-shaped identifier at {location}"))

    inspect(payload)
    return issues


def metadata_value(content: str, label: str) -> str | None:
    match = re.search(rf"^{re.escape(label)}:\s*(.+?)\s*$", content, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None


def check_plan_lifecycle(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for state in ("active", "completed"):
        folder = root / "docs" / "plans" / state
        if not folder.exists():
            issues.append(Issue("HARNESS-003", relative(root, folder), "plan lifecycle folder is missing"))
            continue
        for path in sorted(folder.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            content = path.read_text(encoding="utf-8")
            status = metadata_value(content, "Status")
            owner = metadata_value(content, "Owner")
            updated = metadata_value(content, "Last updated")
            if status != state:
                issues.append(Issue("HARNESS-003", relative(root, path), f"Status must be '{state}'"))
            if not owner:
                issues.append(Issue("HARNESS-003", relative(root, path), "Owner metadata is required"))
            if not updated or not DATE.fullmatch(updated):
                issues.append(
                    Issue("HARNESS-003", relative(root, path), "Last updated must use YYYY-MM-DD")
                )
            has_validation = any(
                line.startswith("## ") and line.casefold().endswith("validation")
                for line in content.splitlines()
            )
            if not has_validation:
                issues.append(Issue("HARNESS-003", relative(root, path), "Validation section is required"))
    return issues


CHECKS = (
    ("required_paths", check_required_paths),
    ("markdown_links", check_markdown_links),
    ("mermaid_accessibility", check_mermaid_accessibility),
    ("python_boundaries", check_python_boundaries),
    ("web_boundaries", check_web_boundaries),
    ("event_schema_boundaries", check_event_schema_boundaries),
    ("local_private_boundary", check_local_private_boundary),
    ("codex_dispatch_boundary", check_codex_dispatch_boundary),
    ("multiplayer_boundary", check_multiplayer_boundary),
    ("public_showcase_boundary", check_public_showcase_boundary),
    ("plan_lifecycle", check_plan_lifecycle),
)


def run_checks(root: Path) -> tuple[dict[str, int], list[Issue]]:
    counts: dict[str, int] = {}
    issues: list[Issue] = []
    for name, check in CHECKS:
        found = check(root)
        counts[name] = len(found)
        issues.extend(found)
    return counts, issues


def command_version(command: str, arguments: list[str]) -> tuple[bool, str]:
    executable = shutil.which(command)
    if executable is None:
        return False, "not found on PATH"
    try:
        result = subprocess.run(  # noqa: S603 - resolved executable and constant arguments
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    output = (result.stdout or result.stderr).strip().splitlines()
    return result.returncode == 0, output[0] if output else f"exit {result.returncode}"


def version_at_least(detail: str, minimum: tuple[int, ...]) -> bool:
    match = re.search(r"\d+(?:\.\d+)+", detail)
    if not match:
        return False
    found = tuple(int(part) for part in match.group(0).split("."))
    width = max(len(found), len(minimum))
    return (*found, *((0,) * (width - len(found)))) >= (
        *minimum,
        *((0,) * (width - len(minimum))),
    )


def doctor(root: Path) -> list[DoctorItem]:
    items: list[DoctorItem] = []
    for name, command, arguments, minimum, remedy in (
        ("Python", "python", ["--version"], (3, 12), "Install Python 3.12 or newer."),
        ("Node.js", "node", ["--version"], (20,), "Install Node.js 20 or newer."),
        ("npm", "npm", ["--version"], (10,), "Install npm 10 or newer."),
        ("Git", "git", ["--version"], (2,), "Install Git for Windows."),
        ("PowerShell", "powershell", ["-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], (5, 1), "Enable Windows PowerShell 5.1 or newer."),
    ):
        available, detail = command_version(command, arguments)
        ok = available and version_at_least(detail, minimum)
        items.append(DoctorItem(name, ok, True, detail, None if ok else remedy))

    expected_root = (root / "package.json").exists() and (root / "pyproject.toml").exists()
    items.append(
        DoctorItem(
            "Repository",
            expected_root,
            True,
            str(root),
            None if expected_root else "Run this command from an Evolastra checkout.",
        )
    )
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    items.append(
        DoctorItem(
            "Python environment",
            venv_python.exists(),
            True,
            str(venv_python) if venv_python.exists() else "missing",
            None if venv_python.exists() else "Run npm run bootstrap or scripts/setup.ps1.",
        )
    )
    node_modules = root / "apps" / "web" / "node_modules"
    items.append(
        DoctorItem(
            "Frontend dependencies",
            node_modules.exists(),
            True,
            str(node_modules) if node_modules.exists() else "missing",
            None if node_modules.exists() else "Run npm run bootstrap or scripts/setup.ps1.",
        )
    )
    gh_ok, gh_detail = command_version("gh", ["--version"])
    items.append(
        DoctorItem(
            "GitHub CLI",
            gh_ok,
            False,
            gh_detail,
            None if gh_ok else "Optional: install GitHub CLI for repository workflows.",
        )
    )
    return items


def print_check_result(root: Path, as_json: bool) -> int:
    counts, issues = run_checks(root)
    payload = {
        "ok": not issues,
        "root": str(root),
        "checks": counts,
        "issues": [asdict(issue) for issue in issues],
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    elif issues:
        print(f"Repository harness found {len(issues)} issue(s):")
        for issue in issues:
            print(f"- [{issue.rule}] {issue.path}: {issue.message}")
    else:
        print(f"Repository harness passed ({len(CHECKS)} checks).")
    return 0 if not issues else 1


def print_doctor_result(root: Path, as_json: bool) -> int:
    items = doctor(root)
    ready = all(item.ok for item in items if item.required)
    payload = {"ready": ready, "root": str(root), "items": [asdict(item) for item in items]}
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print("Evolastra harness doctor")
        for item in items:
            mark = "OK" if item.ok else ("WARN" if not item.required else "FAIL")
            print(f"[{mark}] {item.name}: {item.detail}")
            if item.remedy and not item.ok:
                print(f"       {item.remedy}")
        print("Ready for development." if ready else "Run the remedies above, then repeat npm run doctor.")
    return 0 if ready else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evolastra repository harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("doctor", "check tools and installed development dependencies"),
        ("check", "check repository knowledge and architectural invariants"),
    ):
        child = subparsers.add_parser(command, help=help_text)
        child.add_argument("--json", action="store_true", help="emit machine-readable JSON")
        child.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = args.root.resolve()
    if args.command == "doctor":
        raise SystemExit(print_doctor_result(root, args.json))
    raise SystemExit(print_check_result(root, args.json))


if __name__ == "__main__":
    main()
