from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .access import ensure_private_token

STATE_ROOT = Path(os.getenv("EVOLASTRA_HOME", "~/.evolastra")).expanduser().resolve()
CONFIG_PATH = STATE_ROOT / "service.json"
TOKEN_PATH = STATE_ROOT / "companion-token"
PID_PATH = STATE_ROOT / "companion.pid"
LOG_PATH = STATE_ROOT / "companion.log"


def repository_web_root() -> Path:
    return (Path(__file__).resolve().parents[3] / "apps" / "web" / "dist").resolve()


@dataclass
class ServiceConfig:
    instance_id: str
    port: int
    allowed_origins: list[str]
    database_path: str
    artifact_root: str
    codex_spool: str
    web_root: str
    python: str

    @classmethod
    def default(cls, *, port: int = 8000, origins: list[str] | None = None) -> ServiceConfig:
        root = STATE_ROOT
        return cls(
            instance_id=f"local_{uuid.uuid4().hex}",
            port=port,
            allowed_origins=origins
            or ["http://127.0.0.1:5173", "http://localhost:5173"],
            database_path=str((root / "data" / "evolastra.db").resolve()),
            artifact_root=str((root / "artifacts").resolve()),
            codex_spool=str(Path("~/.codex/evolastra-outbox").expanduser().resolve()),
            web_root=str(repository_web_root()),
            python=str(Path(sys.executable).resolve()),
        )


def load_config() -> ServiceConfig:
    if not CONFIG_PATH.exists():
        raise RuntimeError("Evolastra companion is not installed")
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw.setdefault(
        "web_root",
        str(repository_web_root()),
    )
    return ServiceConfig(**raw)


def save_config(config: ServiceConfig) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_name(f".{CONFIG_PATH.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(asdict(config), indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(CONFIG_PATH)


def service_environment(config: ServiceConfig) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "ASTERISM_ENV": "production",
            "ASTERISM_DEPLOYMENT_PROFILE": "local-private",
            "ASTERISM_DATABASE_URL": f"sqlite:///{Path(config.database_path).as_posix()}",
            "ASTERISM_ARTIFACT_ROOT": config.artifact_root,
            "ASTERISM_TOKEN_FILE": str(TOKEN_PATH),
            "ASTERISM_ALLOWED_ORIGINS": ",".join(config.allowed_origins),
            "ASTERISM_ALLOWED_HOSTS": "127.0.0.1,localhost",
            "ASTERISM_CODEX_SPOOL": config.codex_spool,
            "ASTERISM_DRAIN_CODEX_SPOOL": "true",
            "ASTERISM_SERVE_WEB": "true",
            "ASTERISM_WEB_ROOT": config.web_root,
            "ASTERISM_COMPANION_PORT": str(config.port),
            "ASTERISM_INSTANCE_ID": config.instance_id,
        }
    )
    return environment


def _health(config: ServiceConfig, timeout: float = 0.8) -> dict[str, Any] | None:
    try:
        with urlopen(  # noqa: S310 - fixed loopback URL
            f"http://127.0.0.1:{config.port}/health/service", timeout=timeout
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return None


def service_status() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"installed": False, "running": False}
    config = load_config()
    health = _health(config)
    running = bool(health and health.get("instance_id") == config.instance_id)
    result: dict[str, Any] = {
        "installed": True,
        "running": running,
        "profile": "local-private",
        "url": f"http://127.0.0.1:{config.port}",
        "database": config.database_path,
        "codex_spool": config.codex_spool,
        "web_root": config.web_root,
        "allowed_origins": config.allowed_origins,
        "autostart": _autostart_path().exists(),
    }
    if health:
        result["pid"] = health.get("pid")
        result["port_conflict"] = not running
    return result


def _autostart_path() -> Path:
    if os.name == "nt":
        appdata = Path(os.environ.get("APPDATA", STATE_ROOT))
        return appdata / "Microsoft/Windows/Start Menu/Programs/Startup/EvolastraCompanion.vbs"
    return Path("~/.config/systemd/user/evolastra-companion.service").expanduser().resolve()


def install_autostart(config: ServiceConfig) -> Path:
    destination = _autostart_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        pythonw = Path(config.python).with_name("pythonw.exe")
        interpreter = pythonw if pythonw.exists() else Path(config.python)
        command = subprocess.list2cmdline(
            [str(interpreter), "-m", "asterism_api.service", "run"]
        ).replace('"', '""')
        content = (
            'Set shell = CreateObject("WScript.Shell")\n'
            f'shell.Run "{command}", 0, False\n'
        )
    else:
        content = "\n".join(
            [
                "[Unit]",
                "Description=Evolastra local-private companion",
                "After=network.target",
                "",
                "[Service]",
                f'ExecStart={config.python} -m asterism_api.service run',
                "Restart=on-failure",
                "RestartSec=3",
                "",
                "[Install]",
                "WantedBy=default.target",
                "",
            ]
        )
    destination.write_text(content, encoding="utf-8")
    return destination


def remove_autostart() -> None:
    _autostart_path().unlink(missing_ok=True)


def install_service(
    *,
    port: int,
    origins: list[str],
    install_hooks: bool = True,
    autostart: bool = False,
) -> dict[str, Any]:
    existing = load_config() if CONFIG_PATH.exists() else None
    merged_origins = list(dict.fromkeys([
        *(existing.allowed_origins if existing else []),
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        *origins,
    ]))
    config = existing or ServiceConfig.default(port=port, origins=merged_origins)
    config.port = port
    config.allowed_origins = merged_origins
    config.python = str(Path(sys.executable).resolve())
    if existing:
        # An editable checkout may move. Reinstallation should serve the build
        # belonging to the interpreter's active repository, not a stale path.
        config.web_root = str(repository_web_root())
    if not (Path(config.web_root) / "index.html").is_file():
        raise RuntimeError("Build the web application before installing: npm run build")
    save_config(config)
    ensure_private_token(TOKEN_PATH)
    if autostart:
        install_autostart(config)
    else:
        remove_autostart()
    hook_result: dict[str, Any] | None = None
    if install_hooks:
        from .codex_install import install_codex_hooks

        hook_result = install_codex_hooks(
            spool=Path(config.codex_spool), python=config.python
        )
    return {
        "installed": True,
        "profile": "local-private",
        "autostart": autostart,
        "hooks": hook_result,
        "url": f"http://127.0.0.1:{config.port}",
    }


def start_service() -> dict[str, Any]:
    config = load_config()
    status = service_status()
    if status.get("running"):
        return status
    if status.get("port_conflict"):
        raise RuntimeError(f"Port {config.port} is occupied by another service")
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    log = LOG_PATH.open("ab")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    process = subprocess.Popen(  # noqa: S603 - fixed interpreter and module
        [config.python, "-m", "asterism_api.service", "run"],
        cwd=STATE_ROOT,
        env=service_environment(config),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=log,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )
    PID_PATH.write_text(str(process.pid), encoding="ascii")
    for _ in range(60):
        time.sleep(0.1)
        current = service_status()
        if current.get("running"):
            return current
        if process.poll() is not None:
            break
    raise RuntimeError(f"Evolastra companion failed to start; inspect {LOG_PATH}")


def stop_service() -> dict[str, Any]:
    config = load_config()
    health = _health(config)
    if not health or health.get("instance_id") != config.instance_id:
        PID_PATH.unlink(missing_ok=True)
        return {**service_status(), "stopped": True}
    pid = int(health["pid"])
    if os.name == "nt":
        taskkill = shutil.which("taskkill") or str(
            Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/taskkill.exe"
        )
        subprocess.run(  # noqa: S603 - verified service PID, fixed taskkill command
            [taskkill, "/PID", str(pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        os.kill(pid, signal.SIGTERM)
    for _ in range(30):
        time.sleep(0.1)
        if _health(config) is None:
            break
    PID_PATH.unlink(missing_ok=True)
    return {**service_status(), "stopped": True}


def uninstall_service(*, uninstall_hooks: bool = True) -> dict[str, Any]:
    if CONFIG_PATH.exists():
        stop_service()
    remove_autostart()
    hook_result: dict[str, Any] | None = None
    if uninstall_hooks:
        from .codex_install import uninstall_codex_hooks

        hook_result = uninstall_codex_hooks()
    CONFIG_PATH.unlink(missing_ok=True)
    PID_PATH.unlink(missing_ok=True)
    return {"installed": False, "running": False, "hooks": hook_result}


def create_pairing_code() -> dict[str, Any]:
    config = load_config()
    token = ensure_private_token(TOKEN_PATH)
    request = Request(
        f"http://127.0.0.1:{config.port}/api/v1/pairing/code",
        data=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2.0) as response:  # noqa: S310 - fixed loopback URL
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError("Pairing response was invalid")
            return payload
    except HTTPError as exc:
        raise RuntimeError(f"Pairing request failed ({exc.code})") from exc
    except URLError as exc:
        raise RuntimeError("Evolastra companion is not running") from exc


def run_service() -> None:
    config = load_config()
    os.environ.update(service_environment(config))
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="ascii")
    import uvicorn

    try:
        uvicorn.run(
            "asterism_api.main:app",
            host="127.0.0.1",
            port=config.port,
            workers=1,
            access_log=False,
        )
    finally:
        PID_PATH.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m asterism_api.service")
    parser.add_argument("command", choices=["run"])
    args = parser.parse_args(argv)
    if args.command == "run":
        run_service()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
