from __future__ import annotations

import io
import json
import zipfile

from asterism_api.database import SessionLocal
from asterism_api.event_store import EventStore
from asterism_api.main import app
from fastapi.testclient import TestClient


def setup_function() -> None:
    with TestClient(app):
        with SessionLocal() as session:
            EventStore(session).reset()


def test_health_create_search_and_exports() -> None:
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        created = client.post(
            "/api/v1/runs", json={"title": "Evidence atlas", "objective": "Trace evidence"}
        )
        assert created.status_code == 201
        assert created.json()["run"]["tags"] == []
        run_id = created.json()["run"]["id"]
        state = client.get(f"/api/v1/runs/{run_id}/state")
        assert state.status_code == 200
        assert state.json()["last_sequence"] == 1
        found = client.get("/api/v1/search", params={"run_id": run_id, "q": "evidence"})
        assert found.status_code == 200
        assert found.json()["items"][0]["entity_type"] == "run"
        cloud = client.get(f"/api/v1/runs/{run_id}/export/cloudevents")
        assert cloud.status_code == 200
        envelope = json.loads(cloud.text.strip())
        assert envelope["specversion"] == "1.0"
        prov = client.get(f"/api/v1/runs/{run_id}/export/prov")
        assert prov.status_code == 200
        assert "http://www.w3.org/ns/prov#" in prov.text
        bundle = client.get(f"/api/v1/runs/{run_id}/export/reproduction")
        with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
            assert {"run.json", "events.jsonl", "environment.json", "README.md"} <= set(
                archive.namelist()
            )
        portable = client.get(f"/api/v1/runs/{run_id}/export/portable")
        assert portable.status_code == 200
        assert portable.headers["content-disposition"].endswith('.evolastra"')
        assert client.delete(f"/api/v1/runs/{run_id}").status_code == 204
        loaded = client.post(
            "/api/v1/imports/portable",
            files={
                "file": (
                    f"{run_id}.evolastra",
                    portable.content,
                    "application/vnd.evolastra.analysis+zip",
                )
            },
        )
        assert loaded.status_code == 200
        assert loaded.json()["run_id"] == run_id
        restored = client.get(f"/api/v1/runs/{run_id}/state")
        assert restored.status_code == 200
        assert restored.json()["run"]["title"] == "Evidence atlas"


def test_run_summary_exposes_tags_for_client_side_fixture_classification() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/runs",
            json={"title": "Explicit fixture", "objective": "Test only", "tags": ["seeded-demo"]},
        )
        assert created.status_code == 201
        assert created.json()["run"]["tags"] == ["seeded-demo"]
        assert client.get("/api/v1/runs").json()["items"][0]["tags"] == ["seeded-demo"]


def test_portable_import_rejects_unrecognized_archives() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("unexpected.html", "<script>alert(1)</script>")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/imports/portable",
            files={"file": ("unsafe.evolastra", buffer.getvalue(), "application/zip")},
        )
    assert response.status_code == 422
    assert "only manifest.json and events.jsonl" in response.json()["detail"]


def test_invalid_event_is_quarantined_and_large_body_rejected() -> None:
    with TestClient(app) as client:
        invalid = client.post("/api/v1/events", json={"not": "a CloudEvent"})
        assert invalid.status_code == 422
        assert invalid.json()["quarantine_id"]
        quarantine = client.get("/api/v1/quarantine")
        assert quarantine.json()["items"]
        too_large = client.post(
            "/api/v1/events",
            content=b"x",
            headers={"content-length": "99999999", "content-type": "application/json"},
        )
        assert too_large.status_code == 413
