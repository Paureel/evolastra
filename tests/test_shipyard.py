from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from asterism_api import api as api_module
from asterism_api.codex_dispatch import CodexAppServerMission, MissionReceipt
from asterism_api.database import SessionLocal
from asterism_api.event_store import EventStore
from asterism_api.main import app
from asterism_api.shipyard import blueprint_catalog, find_blueprint, mission_prompt
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def setup_function() -> None:
    with TestClient(app):
        with SessionLocal() as session:
            EventStore(session).reset()


def completed_node() -> dict[str, object]:
    return {
        "id": "node_123456789abc4def8abc123456789abc",
        "parent_node_id": "node_abcdefabcdef4abc8abcdefabcdefabc",
        "title": "Focal CNA recurrence",
        "description": "Prioritize recurrent focal copy-number drivers",
        "node_type": "exploration",
        "status": "completed",
        "progress": 1,
    }


def test_catalog_has_three_core_hulls_and_completed_research_specialist() -> None:
    researching = {**completed_node(), "id": "node_abcdef1234564abc8defabcdef123456", "status": "running", "progress": 0.4}
    state = {"nodes": [completed_node(), researching]}

    catalog = blueprint_catalog(state)

    assert [item.id for item in catalog[:3]] == ["frigate", "mothership", "colony"]
    assert len(catalog) == 4
    assert catalog[-1].id == f"specialist:{completed_node()['id']}"
    assert catalog[-1].source_objective == "Prioritize recurrent focal copy-number drivers"


def test_hull_prompts_encode_distinct_operating_roles() -> None:
    state = {"nodes": [completed_node()]}
    run = {"title": "STAD CNA", "objective": "Find focal drivers"}
    ship = {"name": "Test vessel"}

    mothership = mission_prompt(
        blueprint=find_blueprint(state, "mothership"),  # type: ignore[arg-type]
        ship=ship,
        run=run,
        user_prompt="Compare hypotheses",
    )
    colony = mission_prompt(
        blueprint=find_blueprint(state, "colony"),  # type: ignore[arg-type]
        ship=ship,
        run=run,
        user_prompt="Explore a new direction",
    )
    specialist = mission_prompt(
        blueprint=find_blueprint(state, f"specialist:{completed_node()['id']}"),  # type: ignore[arg-type]
        ship=ship,
        run=run,
        user_prompt="Test this target",
    )

    assert "explicitly authorizes you to spawn Codex subagents" in mothership
    assert "underexplored but testable paths" in colony
    assert "Prioritize recurrent focal copy-number drivers" in specialist
    assert "Mission from the user:\nTest this target" in specialist


def test_app_server_client_starts_configured_model_thread_without_escalation() -> None:
    server = r'''
import json, sys
for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    if method == "initialize":
        print(json.dumps({"id": message["id"], "result": {"userAgent": "fake"}}), flush=True)
    elif method == "thread/start":
        params = message["params"]
        assert "model" not in params
        assert params["sandbox"] == "workspace-write"
        assert params["approvalPolicy"] == "never"
        print(json.dumps({"id": message["id"], "result": {"thread": {"id": "thr_ship"}}}), flush=True)
    elif method == "turn/start":
        print(json.dumps({"id": message["id"], "result": {"turn": {"id": "turn_ship", "status": "inProgress", "items": []}}}), flush=True)
        print(json.dumps({"method": "turn/completed", "params": {"turn": {"id": "turn_ship", "status": "completed", "items": []}}}), flush=True)
'''
    mission = CodexAppServerMission(
        cwd=ROOT,
        prompt="Inspect only",
        command=[sys.executable, "-u", "-c", server],
        request_timeout=5,
    )
    receipt = mission.start()
    completed: list[tuple[MissionReceipt, str, str | None]] = []

    mission.monitor(lambda result, status, error: completed.append((result, status, error)))

    assert receipt == MissionReceipt(thread_id="thr_ship", turn_id="turn_ship")
    assert completed == [(receipt, "completed", None)]


def test_build_and_dispatch_persist_ship_without_prompt_content(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/runs", json={"title": "Shipyard test", "objective": "Launch one mission"}
        )
        run_id = created.json()["run"]["id"]
        yard = client.get(f"/api/v1/runs/{run_id}/shipyard")
        assert yard.status_code == 200
        assert [item["id"] for item in yard.json()["blueprints"]] == [
            "frigate",
            "mothership",
            "colony",
        ]

        built = client.post(
            f"/api/v1/runs/{run_id}/shipyard/build", json={"blueprint_id": "frigate"}
        )
        assert built.status_code == 201
        ship_id = built.json()["ship"]["id"]

        monkeypatch.setattr(
            api_module,
            "get_settings",
            lambda: SimpleNamespace(codex_dispatch_enabled=True, codex_workspace_root=ROOT),
        )
        def fake_dispatch(**kwargs):  # type: ignore[no-untyped-def]
            receipt = MissionReceipt(thread_id="thr_test", turn_id="turn_test")
            kwargs["started"](receipt)
            return receipt

        monkeypatch.setattr(api_module, "dispatch_codex_mission", fake_dispatch)
        dispatched = client.post(
            f"/api/v1/runs/{run_id}/ships/{ship_id}/dispatch",
            json={"prompt": "Private operator mission"},
        )
        assert dispatched.status_code == 202
        assert dispatched.json()["thread_id"] == "thr_test"
        state = client.get(f"/api/v1/runs/{run_id}/state").json()
        ship = next(agent for agent in state["agents"] if agent["id"] == ship_id)
        assert ship["status"] == "running"
        assert ship["prompt"] == "[CONTENT_CAPTURE_DISABLED]"
        assert ship["codex_thread_id"] == "thr_test"
