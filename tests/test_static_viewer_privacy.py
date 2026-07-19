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


def test_hosted_viewer_can_only_fetch_its_own_static_assets_and_loopback_api() -> None:
    source = (ROOT / "apps/web/src/connection.ts").read_text(encoding="utf-8")
    assert "VITE_API_URL" not in source
    assert "connectWithAccessToken" not in source
    assert 'const DEFAULT_ENDPOINT = "http://127.0.0.1:8000"' in source
    assert '"127.0.0.1", "localhost", "[::1]"' in source

    netlify = (ROOT / "netlify.toml").read_text(encoding="utf-8")
    csp = next(line for line in netlify.splitlines() if "connect-src" in line)
    assert "connect-src 'self'" in csp
    assert "connect-src https:" not in csp
    assert "http://127.0.0.1:*" in csp
    assert "http://localhost:*" in csp
    assert "require-trusted-types-for 'script'" in csp
    assert "trusted-types evolastra-worker" in csp
    assert "trusted-types *" not in csp

    canvas = (ROOT / "apps/web/src/components/GalaxyCanvas.tsx").read_text(encoding="utf-8")
    assert 'createPolicy("evolastra-worker"' in canvas
    assert "candidate.origin !== window.location.origin" in canvas
    assert "src\\/layout\\.worker\\.ts" in canvas
    assert 'Cross-Origin-Opener-Policy = "same-origin"' in netlify
    assert 'Cross-Origin-Resource-Policy = "same-origin"' in netlify
    assert 'Cache-Control = "no-store"' in netlify

    showcase = (ROOT / "apps/web/src/showcase.ts").read_text(encoding="utf-8")
    assert 'PUBLIC_SHOWCASE_PATH = "/demo/stad-three-empires-v1.json"' in showcase
    assert "fetch(PUBLIC_SHOWCASE_PATH" in showcase


def test_hosted_viewer_publishes_safe_human_and_agent_setup_routes() -> None:
    agent_setup = (ROOT / "apps/web/public/agent-setup.md").read_text(encoding="utf-8")
    llms = (ROOT / "apps/web/public/llms.txt").read_text(encoding="utf-8")

    assert "-Origin https://evolastra.netlify.app" in agent_setup
    assert "restart Codex" in agent_setup
    assert "approve them" in agent_setup
    assert "companion-token" in agent_setup
    assert "https://evolastra.netlify.app/agent-setup.md" in llms
    assert "Do not bypass or simulate these trust actions" in llms
