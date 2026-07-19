from __future__ import annotations

import asyncio
import io
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from asterism_api import api as api_module  # noqa: E402
from asterism_api import main as main_module  # noqa: E402
from asterism_api.database import Base, engine  # noqa: E402
from asterism_api.db_models import QuarantineRecord, RunRecord, SnapshotRecord  # noqa: E402
from asterism_api.event_store import EventStore, make_event  # noqa: E402
from asterism_api.exports import obsidian_zip  # noqa: E402
from asterism_api.schemas import RunCreate  # noqa: E402
from asterism_api.security import redact  # noqa: E402


def temporary_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_api_sets_security_headers_and_rejects_untrusted_host() -> None:
    with TestClient(main_module.app) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cross-origin-opener-policy"] == "same-origin"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]

        rejected = client.get("/health/live", headers={"Host": "attacker.invalid"})
        assert rejected.status_code == 400


def test_cors_preflight_does_not_allow_unlisted_origin() -> None:
    with TestClient(main_module.app) as client:
        response = client.options(
            "/api/v1/demo/start",
            headers={
                "Origin": "https://attacker.invalid",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_declared_content_length_limit_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module.settings, "max_request_bytes", 16)
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/v1/events",
            content=b"{}",
            headers={"Content-Length": "17", "Content-Type": "application/json"},
        )
    assert response.status_code == 413


def test_jsonl_import_performs_its_own_bounded_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api_module,
        "get_settings",
        lambda: SimpleNamespace(max_request_bytes=16),
    )
    upload = UploadFile(file=io.BytesIO(b"x" * 17), filename="events.jsonl")
    with pytest.raises(HTTPException) as raised:
        asyncio.run(api_module.import_jsonl(None, upload))  # type: ignore[arg-type]
    assert raised.value.status_code == 413


def test_redaction_is_recursive_and_content_capture_is_default_deny() -> None:
    safe = redact(
        {
            "authorization": "Bearer abcdefghijklmnop",
            "nested": {"prompt": "private prompt", "note": "sk-abcdefghijklmnop"},
        }
    )
    assert safe["authorization"] == "[REDACTED]"
    assert safe["nested"]["prompt"] == "[CONTENT_CAPTURE_DISABLED]"
    assert safe["nested"]["note"] == "[REDACTED]"


def test_frontend_has_no_active_content_escape_hatches() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "apps" / "web" / "src").rglob("*.tsx")
    )
    forbidden = (
        "dangerouslySetInnerHTML",
        ".innerHTML",
        "insertAdjacentHTML",
        "document.write",
        "<iframe",
        "<object",
        "<embed",
    )
    assert not [pattern for pattern in forbidden if pattern in source]


def test_obsidian_export_member_names_do_not_traverse() -> None:
    run = SimpleNamespace(
        id="run_00000000-0000-4000-8000-000000000000",
        title="../../outside",
        objective="untrusted objective",
        status="completed",
        state={
            "findings": {
                "find_1": {
                    "id": "find_1",
                    "title": "../../finding",
                    "summary": "untrusted text",
                    "status": "promoted",
                }
            },
            "claims": {},
        },
    )
    archive = zipfile.ZipFile(io.BytesIO(obsidian_zip(run)))
    for name in archive.namelist():
        path = PurePosixPath(name)
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert "\\" not in name


def test_visual_asset_manifest_covers_every_scanned_asset() -> None:
    manifest = json.loads(
        (ROOT / "docs" / "assets" / "asset-manifest.json").read_text(encoding="utf-8")
    )
    extensions = {value.lower() for value in manifest["scope"]["assetExtensions"]}
    discovered: set[str] = set()
    for relative_root in manifest["scope"]["scanRoots"]:
        root = ROOT / relative_root
        if root.exists():
            discovered.update(
                path.relative_to(ROOT).as_posix()
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in extensions
            )
    recorded = {record["filename"] for record in manifest["assets"]}
    assert discovered == recorded


def test_unsafe_origin_cannot_trigger_state_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api_module,
        "start_demo",
        lambda speed: {"run_id": "run_test", "event_total": 0, "speed": speed},
    )
    with TestClient(main_module.app) as client:
        origin_response = client.post(
            "/api/v1/demo/start?speed=1",
            headers={"Origin": "https://attacker.invalid"},
        )
        fetch_metadata_response = client.post(
            "/api/v1/demo/start?speed=1",
            headers={"Sec-Fetch-Site": "cross-site"},
        )
    assert origin_response.status_code == 403
    assert fetch_metadata_response.status_code == 403


def test_streamed_body_without_content_length_is_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module.settings, "max_request_bytes", 16)

    async def exercise() -> int:
        async def body() -> object:
            yield b"x" * 17

        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.request("GET", "/health/live", content=body())
        return response.status_code

    assert asyncio.run(exercise()) == 413


def test_known_artifact_event_requires_artifact_schema() -> None:
    with temporary_session() as session:
        store = EventStore(session)
        run, _ = store.create_run(RunCreate(title="Security fixture", objective="Schema gate"))
        malformed = make_event(
            run_id=run.id,
            event_type="galaxy.analysis.artifact.created.v1",
            subject=f"run/{run.id}/artifact/not-valid",
            data={"artifact": {"id": "not-valid"}},
        )
        result = store.ingest(malformed.model_dump(mode="json"))
        assert not result.accepted


def test_other_known_event_families_require_payload_schema() -> None:
    with temporary_session() as session:
        store = EventStore(session)
        run, _ = store.create_run(RunCreate(title="Security fixture", objective="Schema gate"))
        malformed = make_event(
            run_id=run.id,
            event_type="galaxy.analysis.claim.created.v1",
            subject=f"run/{run.id}/claim/not-valid",
            data={"claim": {"id": "not-valid"}},
        )
        result = store.ingest(malformed.model_dump(mode="json"))
        assert not result.accepted


def test_run_deletion_removes_all_sensitive_run_payloads() -> None:
    now = datetime.now(UTC)
    with temporary_session() as session:
        run = RunRecord(
            id="run_00000000-0000-4000-8000-000000000000",
            title="Sensitive run",
            objective="Sensitive objective",
            status="created",
            seed=1,
            state={"run": {"title": "Sensitive run"}},
            created_at=now,
            updated_at=now,
        )
        snapshot = SnapshotRecord(
            id="snap_00000000-0000-4000-8000-000000000000",
            run_id=run.id,
            sequence=50,
            state={"secret": "residual"},
            created_at=now,
        )
        quarantine = QuarantineRecord(
            id="quar_00000000-0000-4000-8000-000000000000",
            run_id=run.id,
            reason="fixture",
            payload={"secret": "residual"},
            received_at=now,
        )
        snapshot_id = snapshot.id
        quarantine_id = quarantine.id
        session.add_all([run, snapshot, quarantine])
        session.commit()

        api_module.delete_run(run.id, session)

        assert session.get(SnapshotRecord, snapshot_id) is None
        assert session.get(QuarantineRecord, quarantine_id) is None


def test_redaction_covers_camel_case_secret_keys() -> None:
    safe = redact({"clientSecret": "opaque-secret", "accessToken": "opaque-token"})
    assert safe == {"clientSecret": "[REDACTED]", "accessToken": "[REDACTED]"}


def test_sqlite_secure_delete_is_enabled() -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA secure_delete")) == 1
