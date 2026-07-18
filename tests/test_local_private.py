from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from asterism_api import main as main_module
from asterism_api.access import PairingBroker, validate_security_configuration
from asterism_api.codex_install import (
    HOOK_EVENTS,
    codex_hook_status,
    install_codex_hooks,
    managed_hook,
    uninstall_codex_hooks,
)
from asterism_api.config import Settings
from asterism_api.service import ServiceConfig, install_service
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError


def test_pairing_codes_are_one_use_expiring_and_origin_bound() -> None:
    broker = PairingBroker()
    code, _ = broker.create_code(300)
    exchanged = broker.exchange(code, "https://viewer.example", 600)
    assert exchanged is not None
    token, _ = exchanged
    assert broker.exchange(code, "https://viewer.example", 600) is None
    assert broker.validate(token, "https://viewer.example")
    assert not broker.validate(token, "https://other.example")


def test_remote_storage_profile_is_not_supported() -> None:
    with pytest.raises(ValidationError):
        Settings(deployment_profile="hosted-team")  # type: ignore[arg-type]


def test_production_api_must_be_local_private() -> None:
    settings = Settings(
        env="production",
        deployment_profile="development",
        api_token=SecretStr("x" * 48),
    )
    with pytest.raises(RuntimeError, match="loopback-only"):
        validate_security_configuration(settings)


def test_local_private_api_requires_root_or_paired_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    output = Path.cwd() / "output"
    output.mkdir(exist_ok=True)
    settings = main_module.settings
    monkeypatch.setattr(settings, "deployment_profile", "local-private")
    monkeypatch.setattr(settings, "api_token", SecretStr("root-token-for-focused-test-000000000000"))
    allowed_origin = "http://127.0.0.1:5173"
    monkeypatch.setattr(settings, "allowed_origins", [allowed_origin])
    with tempfile.TemporaryDirectory(dir=output) as directory:
        monkeypatch.setattr(settings, "token_file", Path(directory) / "token")
        with TestClient(main_module.app) as client:
            assert client.get("/health/live").status_code == 200
            assert client.get("/api/v1/runs").status_code == 401
            preflight = client.options(
                "/api/v1/runs",
                headers={
                    "Origin": allowed_origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                    "Access-Control-Request-Private-Network": "true",
                },
            )
            assert preflight.status_code == 200
            assert preflight.headers["access-control-allow-origin"] == allowed_origin
            assert preflight.headers["access-control-allow-private-network"] == "true"
            root_headers = {"Authorization": "Bearer root-token-for-focused-test-000000000000"}
            assert client.get("/api/v1/runs", headers=root_headers).status_code == 200
            code_response = client.post("/api/v1/pairing/code", headers=root_headers)
            assert code_response.status_code == 200
            exchange = client.post(
                "/api/v1/pairing/exchange",
                json={"code": code_response.json()["code"]},
                headers={"Origin": allowed_origin, "Sec-Fetch-Site": "cross-site"},
            )
            assert exchange.status_code == 200
            session_headers = {
                "Authorization": f"Bearer {exchange.json()['access_token']}",
                "Origin": allowed_origin,
            }
            assert client.get("/api/v1/runs", headers=session_headers).status_code == 200


def test_production_companion_rejects_non_loopback_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = main_module.settings
    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "deployment_profile", "local-private")
    monkeypatch.setattr(settings, "api_token", SecretStr("x" * 48))
    with TestClient(main_module.app, client=("203.0.113.9", 50000)) as client:
        response = client.get("/health/live")
    assert response.status_code == 403
    assert "loopback" in response.json()["detail"]


def test_codex_hook_installer_preserves_unrelated_hooks() -> None:
    output = Path.cwd() / "output"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        root = Path(directory)
        destination = root / "hooks.json"
        destination.write_text(
            json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "keep-me"}]}]}}),
            encoding="utf-8",
        )
        spool = root / "outbox"
        installed = install_codex_hooks(
            config_path=destination, spool=spool, python="C:/Python/python.exe"
        )
        assert installed["events"] == len(HOOK_EVENTS)
        assert codex_hook_status(destination)["installed"]
        payload = json.loads(destination.read_text(encoding="utf-8"))
        assert any(
            entry["hooks"][0].get("command") == "keep-me"
            for entry in payload["hooks"]["Stop"]
        )
        removed = uninstall_codex_hooks(destination)
        assert removed["removed"] == len(HOOK_EVENTS)
        payload = json.loads(destination.read_text(encoding="utf-8"))
        assert payload["hooks"]["Stop"][0]["hooks"][0]["command"] == "keep-me"


def test_codex_hook_uses_windows_native_generic_command_on_windows() -> None:
    hook = managed_hook(
        "C:/Program Files/Python/python.exe",
        Path("C:/Users/example/evolastra-outbox"),
        windows=True,
    )

    assert hook["command"] == hook["commandWindows"]
    assert "'" not in hook["command"]


def test_service_install_is_manual_start_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    output = Path.cwd() / "output"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        root = Path(directory)
        config = ServiceConfig.default()
        config.web_root = str(root / "dist")
        Path(config.web_root).mkdir()
        (Path(config.web_root) / "index.html").write_text("ok", encoding="utf-8")
        startup = root / "EvolastraCompanion.vbs"
        startup.write_text("old autostart", encoding="utf-8")

        monkeypatch.setattr("asterism_api.service.CONFIG_PATH", root / "service.json")
        monkeypatch.setattr("asterism_api.service.TOKEN_PATH", root / "token")
        monkeypatch.setattr("asterism_api.service._autostart_path", lambda: startup)
        monkeypatch.setattr(ServiceConfig, "default", classmethod(lambda cls, **kwargs: config))
        monkeypatch.setattr(
            "asterism_api.codex_install.install_codex_hooks",
            lambda **kwargs: {"installed": True},
        )

        result = install_service(port=8000, origins=[])

        assert result["autostart"] is False
        assert not startup.exists()
