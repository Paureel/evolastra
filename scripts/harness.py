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
