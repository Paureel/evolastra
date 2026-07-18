from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_deployment_has_no_api_database_or_connector() -> None:
    assert not (ROOT / "apps/api/asterism_api/connector.py").exists()
    assert not (ROOT / "deploy/evolastra.env.example").exists()
    assert not (ROOT / "deploy/evolastra.service").exists()

    caddy = (ROOT / "deploy/Caddyfile.example").read_text(encoding="utf-8")
    assert "file_server" in caddy
    assert "reverse_proxy" not in caddy


def test_hosted_viewer_can_only_connect_to_loopback() -> None:
    source = (ROOT / "apps/web/src/connection.ts").read_text(encoding="utf-8")
    assert "VITE_API_URL" not in source
    assert "connectWithAccessToken" not in source
    assert 'const DEFAULT_ENDPOINT = "http://127.0.0.1:8000"' in source
    assert '"127.0.0.1", "localhost", "[::1]"' in source

    netlify = (ROOT / "netlify.toml").read_text(encoding="utf-8")
    csp = next(line for line in netlify.splitlines() if "connect-src" in line)
    assert "connect-src 'self'" not in csp
    assert "connect-src https:" not in csp
    assert "http://127.0.0.1:*" in csp
    assert "http://localhost:*" in csp
