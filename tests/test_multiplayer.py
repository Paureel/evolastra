from __future__ import annotations

from types import SimpleNamespace

import pytest
from asterism_api import multiplayer as multiplayer_module
from asterism_api import multiplayer_api
from asterism_api.database import SessionLocal
from asterism_api.db_models import MultiplayerSessionRecord
from asterism_api.event_store import EventStore
from asterism_api.main import app
from asterism_api.multiplayer import (
    MultiplayerError,
    clear_multiplayer_runtime,
    decode_invite,
    delete_session_for_run,
    normalize_share_url,
)
from asterism_api.simulator import DEMO_SEED, build_demo_events
from fastapi.testclient import TestClient


def setup_function() -> None:
    with TestClient(app):
        with SessionLocal() as session:
            EventStore(session).reset()


def local_private_settings() -> SimpleNamespace:
    return SimpleNamespace(deployment_profile="local-private", companion_port=8000)


def start_demo(client: TestClient) -> tuple[str, dict[str, object]]:
    response = client.post(
        "/api/v1/runs",
        json={"title": "Multiplayer fixture", "objective": "Explore one problem", "seed": DEMO_SEED},
    )
    assert response.status_code == 201
    run_id = response.json()["run"]["id"]
    events = [event.model_dump(mode="json") for event in build_demo_events(run_id, DEMO_SEED)]
    ingested = client.post("/api/v1/events/batch", json={"events": events})
    assert ingested.status_code == 202
    assert ingested.json()["accepted"] == len(events)
    state = client.get(f"/api/v1/runs/{run_id}/state").json()
    return run_id, state


def test_single_player_remains_default_and_multiplayer_requires_local_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(app) as client:
        run_id, state_before = start_demo(client)
        multiplayer = client.get(f"/api/v1/multiplayer/runs/{run_id}")
        assert multiplayer.status_code == 200
        assert multiplayer.json() == {"enabled": False}

        blocked = client.post(
            "/api/v1/multiplayer/host",
            json={
                "run_id": run_id,
                "display_name": "Aurel",
                "color": "#71E6E1",
                "share_url": "https://host.example.ts.net",
            },
        )
        assert blocked.status_code == 409
        state_after = client.get(f"/api/v1/runs/{run_id}/state").json()
        assert state_after == state_before


def test_host_invite_member_claim_and_publication_are_separate_from_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multiplayer_api, "get_settings", local_private_settings)
    with TestClient(app) as client:
        run_id, analysis = start_demo(client)
        sequence_before = analysis["last_sequence"]
        hosted = client.post(
            "/api/v1/multiplayer/host",
            json={
                "run_id": run_id,
                "display_name": "Aurel",
                "color": "#71E6E1",
                "share_url": "https://host.example.ts.net",
            },
        )
        assert hosted.status_code == 201
        invite_code = hosted.json()["invite_code"]
        invite = decode_invite(invite_code)
        host_state = hosted.json()["state"]
        assert host_state["enabled"] is True
        assert host_state["session"]["mode"] == "host"
        assert len(host_state["players"]) == 1
        assert len(host_state["claims"]) == 1
        assert "secret" not in host_state["session"]

        tailnet = {"Tailscale-User-Login": "peer@example.test"}
        denied = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/join",
            headers={"Authorization": f"Bearer {invite['secret']}"},
            json={
                "display_name": "Peer",
                "color": "#FFD36A",
                "project_fingerprint": invite["fingerprint"],
            },
        )
        assert denied.status_code == 403

        joined = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/join",
            headers={**tailnet, "Authorization": f"Bearer {invite['secret']}"},
            json={
                "display_name": "Peer",
                "color": "#FFD36A",
                "project_fingerprint": invite["fingerprint"],
            },
        )
        assert joined.status_code == 200
        member_token = joined.json()["member_token"]
        player_id = joined.json()["player"]["id"]
        member_headers = {**tailnet, "Authorization": f"Bearer {member_token}"}

        root_id = host_state["claims"][0]["node_id"]
        node_id = next(node["id"] for node in analysis["nodes"] if node["id"] != root_id)
        claimed = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/claims",
            headers=member_headers,
            json={"node_id": node_id},
        )
        assert claimed.status_code == 200
        assert any(
            claim["node_id"] == node_id and claim["player_id"] == player_id
            for claim in claimed.json()["claims"]
        )

        published = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/publications",
            headers=member_headers,
            json={
                "finding_id": "finding_123456789abc4def8abc123456789abc",
                "title": "Independent direction",
                "summary": "A bounded summary explicitly selected for federation sharing.",
            },
        )
        assert published.status_code == 200
        assert published.json()["publications"][0]["summary"].startswith("A bounded summary")

        analysis_after = client.get(f"/api/v1/runs/{run_id}/state").json()
        assert analysis_after["last_sequence"] == sequence_before
        assert analysis_after == analysis

        left = client.delete(
            f"/api/v1/federation/sessions/{invite['session_id']}/members/self",
            headers=member_headers,
        )
        assert left.status_code == 200
        host_after_leave = client.get(f"/api/v1/multiplayer/runs/{run_id}").json()
        assert all(player["id"] != player_id for player in host_after_leave["players"])
        assert all(claim["player_id"] != player_id for claim in host_after_leave["claims"])

        assert client.delete(f"/api/v1/runs/{run_id}").status_code == 204
        assert client.get(f"/api/v1/multiplayer/runs/{run_id}").json() == {"enabled": False}


def test_guest_grant_stays_in_memory_and_restart_pauses_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multiplayer_api, "get_settings", local_private_settings)
    with TestClient(app) as client:
        run_id, _ = start_demo(client)
        hosted = client.post(
            "/api/v1/multiplayer/host",
            json={
                "run_id": run_id,
                "display_name": "Temporary host",
                "color": "#71E6E1",
                "share_url": "https://host.example.ts.net",
            },
        ).json()
        invite_code = hosted["invite_code"]
        invite = decode_invite(invite_code)
        with SessionLocal() as db:
            delete_session_for_run(db, run_id)
            db.commit()

        remote_state = {
            "enabled": True,
            "session": {
                "id": invite["session_id"],
                "run_id": run_id,
                "mode": "host",
                "status": "active",
                "revision": 2,
                "host_url": invite["url"],
                "project_fingerprint": invite["fingerprint"],
                "local_player_id": "player_host",
                "title": "Shared analysis",
            },
            "players": [
                {
                    "id": "player_guest",
                    "display_name": "Guest",
                    "color": "#FFD36A",
                    "role": "member",
                    "online": True,
                    "last_seen_at": "2026-07-18T12:00:00Z",
                }
            ],
            "claims": [],
            "publications": [],
        }

        def fake_remote_request(**kwargs):  # type: ignore[no-untyped-def]
            if str(kwargs["path"]).endswith("/join"):
                return {
                    "member_token": "guest-memory-token-with-sufficient-length",
                    "player": {"id": "player_guest", "display_name": "Guest", "color": "#FFD36A"},
                    "state": remote_state,
                }
            return remote_state

        monkeypatch.setattr(multiplayer_module, "_remote_request", fake_remote_request)
        joined = client.post(
            "/api/v1/multiplayer/join",
            json={"invite_code": invite_code, "display_name": "Guest", "color": "#FFD36A"},
        )
        assert joined.status_code == 201
        assert joined.json()["session"]["mode"] == "guest"
        assert "member_token" not in joined.text
        with SessionLocal() as db:
            record = db.get(MultiplayerSessionRecord, invite["session_id"])
            assert record is not None
            assert not hasattr(record, "member_token")

        clear_multiplayer_runtime()
        paused = client.get(f"/api/v1/multiplayer/runs/{run_id}")
        assert paused.status_code == 200
        assert paused.json()["session"]["status"] == "paused"
        assert "Rejoin with a fresh invite" in paused.json()["connection_error"]


def test_project_mismatch_conflicts_and_closed_host_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multiplayer_api, "get_settings", local_private_settings)
    with TestClient(app) as client:
        run_id, analysis = start_demo(client)
        hosted = client.post(
            "/api/v1/multiplayer/host",
            json={
                "run_id": run_id,
                "display_name": "Host",
                "color": "#71E6E1",
                "share_url": "https://host.example.ts.net",
            },
        ).json()
        invite = decode_invite(hosted["invite_code"])
        tailnet = {"Tailscale-User-Login": "peer@example.test"}
        mismatch = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/join",
            headers={**tailnet, "Authorization": f"Bearer {invite['secret']}"},
            json={
                "display_name": "Peer",
                "color": "#FFD36A",
                "project_fingerprint": "0" * 64,
            },
        )
        assert mismatch.status_code == 401

        first = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/join",
            headers={**tailnet, "Authorization": f"Bearer {invite['secret']}"},
            json={
                "display_name": "Peer",
                "color": "#FFD36A",
                "project_fingerprint": invite["fingerprint"],
            },
        ).json()
        duplicate = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/join",
            headers={**tailnet, "Authorization": f"Bearer {invite['secret']}"},
            json={
                "display_name": "Second Peer",
                "color": "#FFD36A",
                "project_fingerprint": invite["fingerprint"],
            },
        )
        assert duplicate.status_code == 401

        closed = client.delete(f"/api/v1/multiplayer/runs/{run_id}")
        assert closed.status_code == 200
        member_state = client.get(
            f"/api/v1/federation/sessions/{invite['session_id']}",
            headers={**tailnet, "Authorization": f"Bearer {first['member_token']}"},
        )
        assert member_state.status_code == 200
        assert member_state.json()["session"]["status"] == "closed"
        node_id = analysis["nodes"][1]["id"]
        blocked_claim = client.post(
            f"/api/v1/federation/sessions/{invite['session_id']}/claims",
            headers={**tailnet, "Authorization": f"Bearer {first['member_token']}"},
            json={"node_id": node_id},
        )
        assert blocked_claim.status_code == 409

        reset = client.delete(f"/api/v1/multiplayer/runs/{run_id}")
        assert reset.status_code == 200
        assert client.get(f"/api/v1/multiplayer/runs/{run_id}").json() == {"enabled": False}


@pytest.mark.parametrize(
    "value",
    [
        "http://host.example.ts.net",
        "https://example.com",
        "https://user:password@host.example.ts.net",
        "https://host.example.ts.net/path",
    ],
)
def test_share_url_rejects_non_tailnet_or_credentialed_targets(value: str) -> None:
    with pytest.raises(MultiplayerError):
        normalize_share_url(value)
