from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def state_root() -> Path:
    return Path(os.getenv("EVOLASTRA_HOME", "~/.evolastra")).expanduser().resolve()


def service_config() -> dict[str, Any] | None:
    path = state_root() / "service.json"
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def repository_candidates(explicit: str | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.getenv("EVOLASTRA_REPO"):
        candidates.append(Path(os.environ["EVOLASTRA_REPO"]))
    candidates.append(Path(__file__).resolve().parents[3])
    candidates.extend([Path.cwd(), *Path.cwd().parents])
    candidates.append(Path.home() / "Documents" / "starexplorer")
    return list(dict.fromkeys(path.expanduser().resolve() for path in candidates))


def repository_launcher(repo: Path) -> list[str] | None:
    metadata = repo / "pyproject.toml"
    if not metadata.is_file() or "evolastra-observatory" not in metadata.read_text(
        encoding="utf-8", errors="replace"
    ):
        return None
    executables = [
        repo / ".venv" / "Scripts" / "evolastra.exe",
        repo / ".venv" / "bin" / "evolastra",
    ]
    for executable in executables:
        if executable.is_file():
            return [str(executable)]
    interpreters = [
        repo / ".venv" / "Scripts" / "python.exe",
        repo / ".venv" / "bin" / "python",
    ]
    for interpreter in interpreters:
        if interpreter.is_file():
            return [str(interpreter), "-m", "asterism_api.cli"]
    return None


def discover_launcher(repo: str | None) -> list[str]:
    config = service_config()
    if config:
        python = Path(str(config.get("python", ""))).expanduser()
        if python.is_file():
            return [str(python.resolve()), "-m", "asterism_api.cli"]
    executable = shutil.which("evolastra")
    if executable:
        return [executable]
    for candidate in repository_candidates(repo):
        launcher = repository_launcher(candidate)
        if launcher:
            return launcher
    raise RuntimeError(
        "Cannot find Evolastra. Pass --repo, set EVOLASTRA_REPO, or install the repository virtual environment."
    )


def run_cli(launcher: list[str], *arguments: str) -> dict[str, Any]:
    process = subprocess.run(  # noqa: S603 - fixed discovered executable and argument vector
        [*launcher, *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode:
        detail = process.stderr.strip() or process.stdout.strip() or "unknown error"
        raise RuntimeError(f"Evolastra command failed: {detail}")
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Evolastra returned an invalid response") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Evolastra returned an invalid response")
    return payload


def normalize_origin(value: str) -> str:
    parsed = urlsplit(value.strip())
    loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    allowed_scheme = parsed.scheme == "https" or (parsed.scheme == "http" and loopback)
    if (
        not allowed_scheme
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Use an exact HTTPS origin, or an HTTP loopback origin, without a path")
    return f"{parsed.scheme}://{parsed.netloc}"


def install_arguments(args: argparse.Namespace, origin: str | None, autostart: bool) -> list[str]:
    values = ["service", "install", "--port", str(args.port)]
    if origin:
        values.extend(["--origin", origin])
    if args.no_hooks:
        values.append("--no-hooks")
    if autostart:
        values.append("--autostart")
    return values


def ensure(launcher: list[str], args: argparse.Namespace) -> dict[str, Any]:
    origin = normalize_origin(args.origin) if args.origin else None
    status = run_cli(launcher, "service", "status")
    installed_now = False
    registered_origin = False
    if not status.get("installed"):
        run_cli(launcher, *install_arguments(args, origin, args.autostart))
        installed_now = True
        registered_origin = origin is not None
        status = run_cli(launcher, "service", "status")
    elif origin and origin not in status.get("allowed_origins", []):
        was_running = bool(status.get("running"))
        run_cli(
            launcher,
            *install_arguments(args, origin, bool(status.get("autostart")) or args.autostart),
        )
        registered_origin = True
        status = run_cli(launcher, "service", "status")
        if was_running:
            run_cli(launcher, "service", "stop")
            status = run_cli(launcher, "service", "start")
    if not status.get("running"):
        status = run_cli(launcher, "service", "start")
    hooks = run_cli(launcher, "codex", "status")
    hooks_installed_now = False
    if not hooks.get("installed") and not args.no_hooks:
        run_cli(launcher, "codex", "install")
        hooks = run_cli(launcher, "codex", "status")
        hooks_installed_now = True
    return {
        "service": status,
        "hooks": hooks,
        "installed_now": installed_now,
        "hooks_installed_now": hooks_installed_now,
        "registered_origin": registered_origin,
        "restart_codex_required": installed_now or hooks_installed_now,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely operate the local Evolastra companion")
    parser.add_argument(
        "action", choices=["diagnose", "ensure", "install", "start", "stop", "status", "pair"]
    )
    parser.add_argument("--repo", help="Path to the Evolastra repository")
    parser.add_argument("--origin", help="Exact hosted viewer origin")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-hooks", action="store_true")
    parser.add_argument("--autostart", action="store_true")
    args = parser.parse_args()
    try:
        launcher = discover_launcher(args.repo)
        if args.action == "diagnose":
            result = {
                "service": run_cli(launcher, "service", "status"),
                "hooks": run_cli(launcher, "codex", "status"),
            }
        elif args.action == "ensure":
            result = ensure(launcher, args)
        elif args.action == "install":
            origin = normalize_origin(args.origin) if args.origin else None
            current = run_cli(launcher, "service", "status")
            preserve_autostart = bool(current.get("autostart")) or args.autostart
            result = run_cli(
                launcher, *install_arguments(args, origin, preserve_autostart)
            )
        elif args.action in {"start", "stop", "status"}:
            result = run_cli(launcher, "service", args.action)
        else:
            result = run_cli(launcher, "pair")
        print(json.dumps(result, indent=2, default=str))
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
