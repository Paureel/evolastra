from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .access import pairing_broker, require_api_access
from .codex_dispatch import (
    CodexDispatchError,
    MissionReceipt,
    dispatch_codex_mission,
    find_codex_executable,
)
from .config import get_settings
from .database import SessionLocal, get_session
from .db_models import EventRecord, QuarantineRecord, RunRecord, SnapshotRecord
from .event_store import EventStore, event_json, make_event
from .exports import (
    cloudevents_jsonl,
    json_bytes,
    obsidian_zip,
    openlineage_export,
    portable_bundle,
    prov_export,
    read_portable_bundle,
    reproduction_zip,
)
from .schemas import (
    ApprovalRequest,
    CommandRequest,
    EventBatch,
    PairingExchange,
    RunCreate,
    RunPatch,
    ShipBuildRequest,
    ShipDispatchRequest,
)
from .security import redact
from .shipyard import (
    blueprint_catalog,
    find_blueprint,
    mission_developer_instructions,
    mission_prompt,
    ship_name,
)
from .simulator import set_speed, start_demo

public_router = APIRouter(prefix="/api/v1")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_access)])
SessionDep = Annotated[Session, Depends(get_session)]


@public_router.get("/pairing/info")
def pairing_info() -> dict[str, Any]:
    settings = get_settings()
    return {
        "application": "Evolastra",
        "profile": settings.deployment_profile,
        "authentication_required": settings.auth_required,
        "local_data": settings.local_data,
        "pairing_supported": settings.deployment_profile == "local-private",
    }


@public_router.post("/pairing/exchange")
def exchange_pairing_code(payload: PairingExchange, request: Request) -> dict[str, Any]:
    settings = get_settings()
    if settings.deployment_profile != "local-private":
        raise HTTPException(status_code=404, detail="Local pairing is not enabled")
    origin = request.headers.get("origin")
    if origin is None or origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Pairing origin is not allowed")
    exchanged = pairing_broker.exchange(payload.code, origin, settings.session_ttl_seconds)
    if exchanged is None:
        raise HTTPException(status_code=401, detail="Pairing code is invalid or expired")
    token, expires_at = exchanged
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "profile": settings.deployment_profile,
        "local_data": True,
    }


@router.post("/pairing/code")
def create_pairing_code() -> dict[str, Any]:
    settings = get_settings()
    if settings.deployment_profile != "local-private":
        raise HTTPException(status_code=404, detail="Local pairing is not enabled")
    code, expires_at = pairing_broker.create_code(settings.pairing_ttl_seconds)
    return {"code": code, "expires_at": expires_at.isoformat()}


@router.get("/connection")
def connection_info() -> dict[str, Any]:
    settings = get_settings()
    return {
        "application": "Evolastra",
        "profile": settings.deployment_profile,
        "local_data": settings.local_data,
        "instance_id": settings.instance_id,
    }


def get_run_or_404(session: Session, run_id: str) -> RunRecord:
    record = session.get(RunRecord, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return record


def run_summary(record: RunRecord) -> dict[str, Any]:
    state = record.state
    metrics = state.get("metrics", [])
    latest_metric = metrics[-1] if metrics else {}
    return {
        "id": record.id,
        "schema_version": record.schema_version,
        "title": record.title,
        "objective": record.objective,
        "status": record.status,
        "seed": record.seed,
        "privacy_class": record.privacy_class,
        "source_adapters": record.source_adapters,
        "tags": state.get("run", {}).get("tags", []),
        "last_sequence": record.last_sequence,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "counts": {
            key: len(state.get(key, {}))
            for key in (
                "nodes",
                "agents",
                "tool_calls",
                "datasets",
                "artifacts",
                "claims",
                "findings",
                "anomalies",
            )
        },
        "latest_metric": latest_metric,
    }


@router.post("/runs", status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, session: SessionDep) -> dict[str, Any]:
    record, event = EventStore(session).create_run(payload)
    return {"run": run_summary(record), "event": event}


@router.get("/runs")
def list_runs(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    records = session.scalars(
        select(RunRecord).order_by(RunRecord.updated_at.desc()).offset(offset).limit(limit)
    ).all()
    total = session.scalar(select(func.count()).select_from(RunRecord)) or 0
    return {
        "items": [run_summary(record) for record in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}")
def read_run(run_id: str, session: SessionDep) -> dict[str, Any]:
    return run_summary(get_run_or_404(session, run_id))


@router.patch("/runs/{run_id}")
def update_run(run_id: str, payload: RunPatch, session: SessionDep) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    patch = payload.model_dump(exclude_none=True)
    event = make_event(
        run_id=run_id,
        event_type="galaxy.analysis.run.updated.v1",
        subject=f"run/{run_id}",
        data={"run": {"id": run_id, **patch, "update_time": datetime.now(UTC).isoformat()}},
        source="urn:galaxy:ui",
    )
    result = EventStore(session).ingest(event.model_dump(mode="json"))
    if not result.accepted:
        raise HTTPException(status_code=422, detail=result.reason)
    session.refresh(run)
    return run_summary(run)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, session: SessionDep) -> Response:
    from .multiplayer import delete_session_for_run

    run = get_run_or_404(session, run_id)
    store = EventStore(session)
    store.audit("run.delete", run_id, {"title": run.title})
    session.query(EventRecord).filter(EventRecord.run_id == run_id).delete()
    session.query(SnapshotRecord).filter(SnapshotRecord.run_id == run_id).delete()
    session.query(QuarantineRecord).filter(QuarantineRecord.run_id == run_id).delete()
    delete_session_for_run(session, run_id)
    session.delete(run)
    session.commit()
    return Response(status_code=204)


@router.get("/runs/{run_id}/state")
def read_state(
    run_id: str,
    session: SessionDep,
    at: int | None = Query(default=None, ge=0),
) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    return EventStore(session).state_at(run, at)


@router.get("/runs/{run_id}/graph")
def read_graph(
    run_id: str, session: SessionDep, at: int | None = Query(default=None, ge=0)
) -> dict[str, Any]:
    return read_state(run_id, session, at)


@router.post("/runs/{run_id}/rebuild")
def rebuild_projection(run_id: str, session: SessionDep) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    store = EventStore(session)
    state_data = store.rebuild(run)
    store.audit("projection.rebuild", run_id)
    session.commit()
    return {"run_id": run_id, "last_sequence": run.last_sequence, "state": state_data}


@router.get("/runs/{run_id}/events")
def list_events(
    run_id: str,
    session: SessionDep,
    after: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=2_000),
) -> dict[str, Any]:
    get_run_or_404(session, run_id)
    records = session.scalars(
        select(EventRecord)
        .where(EventRecord.run_id == run_id, EventRecord.sequence > after)
        .order_by(EventRecord.sequence)
        .limit(limit)
    ).all()
    return {
        "items": [record.envelope for record in records],
        "next_cursor": records[-1].sequence if records else after,
    }


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def ingest_event(payload: dict[str, Any], session: SessionDep) -> JSONResponse:
    result = EventStore(session).ingest(payload)
    code = 202 if result.accepted else 422
    return JSONResponse(status_code=code, content=result.model_dump(mode="json"))


@router.post("/events/batch", status_code=status.HTTP_202_ACCEPTED)
def ingest_batch(payload: EventBatch, session: SessionDep) -> dict[str, Any]:
    results = [EventStore(session).ingest(raw).model_dump(mode="json") for raw in payload.events]
    return {
        "results": results,
        "accepted": sum(1 for result in results if result["accepted"]),
        "quarantined": sum(1 for result in results if not result["accepted"]),
    }


@router.post("/imports/jsonl")
async def import_jsonl(session: SessionDep, file: UploadFile = File(...)) -> dict[str, Any]:
    settings = get_settings()
    body = await file.read(settings.max_request_bytes + 1)
    if len(body) > settings.max_request_bytes:
        raise HTTPException(status_code=413, detail="Import exceeds configured limit")
    return import_event_lines(session, body)


def import_event_lines(
    session: Session,
    body: bytes,
    *,
    expected_run_id: str | None = None,
) -> dict[str, Any]:
    try:
        lines = body.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Import must be UTF-8 JSONL") from exc
    accepted = 0
    duplicates = 0
    quarantined = 0
    run_ids: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            EventStore(session).quarantine(
                {"line": line[:2_000], "line_number": line_number}, f"invalid JSON: {exc.msg}"
            )
            quarantined += 1
            continue
        if not isinstance(payload, dict):
            EventStore(session).quarantine(
                {"line_number": line_number, "value_type": type(payload).__name__},
                "event line must be a JSON object",
            )
            quarantined += 1
            continue
        run_id = payload.get("runid")
        if expected_run_id is not None and run_id != expected_run_id:
            raise HTTPException(
                status_code=422,
                detail=f"Portable event {line_number} does not belong to the manifest run",
            )
        if isinstance(run_id, str):
            run_ids.add(run_id)
        if payload.get("type") == "galaxy.analysis.snapshot.created.v1":
            continue
        payload.pop("sequence", None)
        result = EventStore(session).ingest(payload)
        accepted += int(result.accepted)
        duplicates += int(result.duplicate)
        quarantined += int(not result.accepted)
    return {
        "accepted": accepted,
        "duplicates": duplicates,
        "quarantined": quarantined,
        "run_ids": sorted(run_ids),
    }


@router.post("/imports/portable")
async def import_portable(session: SessionDep, file: UploadFile = File(...)) -> dict[str, Any]:
    settings = get_settings()
    body = await file.read(settings.max_request_bytes + 1)
    if len(body) > settings.max_request_bytes:
        raise HTTPException(status_code=413, detail="Portable analysis exceeds configured limit")
    try:
        manifest, event_body = read_portable_bundle(body, max_bytes=settings.max_request_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = import_event_lines(session, event_body, expected_run_id=str(manifest["run_id"]))
    if result["quarantined"]:
        raise HTTPException(status_code=422, detail="Portable analysis contains invalid events")
    return {**result, "run_id": manifest["run_id"], "title": manifest.get("title")}


@router.get("/quarantine")
def list_quarantine(
    session: SessionDep, limit: int = Query(default=100, ge=1, le=500)
) -> dict[str, Any]:
    rows = session.scalars(
        select(QuarantineRecord).order_by(QuarantineRecord.received_at.desc()).limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "run_id": row.run_id,
                "reason": row.reason,
                "received_at": row.received_at.isoformat(),
                "retry_count": row.retry_count,
            }
            for row in rows
        ]
    }


@router.post("/quarantine/{quarantine_id}/retry")
def retry_quarantine(quarantine_id: str, session: SessionDep) -> dict[str, Any]:
    row = session.get(QuarantineRecord, quarantine_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Quarantine record not found")
    payload = row.payload
    row.retry_count += 1
    session.commit()
    result = EventStore(session).ingest(payload)
    if result.accepted:
        preserved = session.get(QuarantineRecord, quarantine_id)
        if preserved is not None:
            session.delete(preserved)
            session.commit()
        return result.model_dump(mode="json")
    if result.quarantine_id and result.quarantine_id != quarantine_id:
        replacement = session.get(QuarantineRecord, result.quarantine_id)
        if replacement is not None:
            session.delete(replacement)
    preserved = session.get(QuarantineRecord, quarantine_id)
    if preserved is not None:
        preserved.reason = result.reason or preserved.reason
    session.commit()
    return result.model_copy(update={"quarantine_id": quarantine_id}).model_dump(mode="json")


@router.get("/runs/{run_id}/events/stream")
async def stream_events(
    run_id: str, request: Request, session: SessionDep, after: int = Query(default=0, ge=0)
) -> StreamingResponse:
    get_run_or_404(session, run_id)
    last_event = request.headers.get("last-event-id")
    if last_event and last_event.isdigit():
        after = max(after, int(last_event))

    async def generator() -> Any:
        cursor = after
        idle_ticks = 0
        while not await request.is_disconnected():
            with next(get_session()) as poll_session:
                rows = poll_session.scalars(
                    select(EventRecord)
                    .where(EventRecord.run_id == run_id, EventRecord.sequence > cursor)
                    .order_by(EventRecord.sequence)
                    .limit(250)
                ).all()
            if rows:
                for row in rows:
                    cursor = row.sequence
                    yield f"id: {row.sequence}\nevent: semantic\ndata: {event_json(row)}\n\n"
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 30:
                    heartbeat = json.dumps(
                        {"runid": run_id, "sequence": cursor, "time": datetime.now(UTC).isoformat()}
                    )
                    yield f"event: heartbeat\ndata: {heartbeat}\n\n"
                    idle_ticks = 0
            await asyncio.sleep(0.5)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/runs/{run_id}/commands")
def command(run_id: str, payload: CommandRequest, session: SessionDep) -> dict[str, Any]:
    get_run_or_404(session, run_id)
    if payload.command == "set_simulator_speed":
        if not isinstance(payload.value, int | float):
            raise HTTPException(status_code=422, detail="A numeric speed is required")
        applied = set_speed(run_id, float(payload.value))
        return {"accepted": applied, "command": payload.command, "value": payload.value}
    if payload.command == "add_annotation":
        from .ids import new_id

        annotation = {
            "id": new_id("anno"),
            "run_id": run_id,
            "text": str(payload.value or "")[:2_000],
            "author": "local-operator",
        }
        event = make_event(
            run_id=run_id,
            event_type="galaxy.analysis.annotation.created.v1",
            subject=f"run/{run_id}/annotation/{annotation['id']}",
            data={"annotation": annotation},
            source="urn:galaxy:ui",
        )
        result = EventStore(session).ingest(event.model_dump(mode="json"))
        return result.model_dump(mode="json")
    return {"accepted": True, "command": payload.command, "value": payload.value, "scope": "client"}


def _state_values(state: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = state.get(key, {})
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _mission_completed(
    *, run_id: str, ship_id: str, thread_id: str, turn_id: str, status_value: str, error: str | None
) -> None:
    with SessionLocal() as session:
        run = session.get(RunRecord, run_id)
        if run is None:
            return
        agents = run.state.get("agents", {})
        current = agents.get(ship_id) if isinstance(agents, dict) else None
        if not isinstance(current, dict):
            return
        completed = status_value == "completed"
        agent = {
            **current,
            "status": "completed" if completed else "failed",
            "codex_thread_id": thread_id,
            "codex_turn_id": turn_id,
            "mission_completed_at": datetime.now(UTC).isoformat(),
            "error_summary": redact(error) if error else None,
        }
        event = make_event(
            run_id=run_id,
            event_type=(
                "galaxy.analysis.agent.completed.v1"
                if completed
                else "galaxy.analysis.agent.failed.v1"
            ),
            subject=f"run/{run_id}/agent/{ship_id}",
            data={"agent": agent},
            source="urn:galaxy:shipyard",
        )
        EventStore(session).ingest(event.model_dump(mode="json"))


@router.get("/runs/{run_id}/shipyard")
def get_shipyard(run_id: str, session: SessionDep) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    settings = get_settings()
    ships = [
        agent
        for agent in _state_values(run.state, "agents")
        if agent.get("framework") == "evolastra-shipyard"
    ]
    return {
        "blueprints": [blueprint.public() for blueprint in blueprint_catalog(run.state)],
        "ships": ships,
        "dispatch_enabled": settings.codex_dispatch_enabled,
        "codex_available": bool(settings.codex_dispatch_enabled and find_codex_executable()),
        "safety": {
            "transport": "local-stdio",
            "sandbox": "workspace-write",
            "approval_policy": "never",
            "workspace_fixed": True,
            "network_access": False,
            "web_search": "disabled",
            "environment_filtered": True,
            "context_isolated": True,
        },
    }


@router.post("/runs/{run_id}/shipyard/build", status_code=status.HTTP_201_CREATED)
def build_ship(
    run_id: str, payload: ShipBuildRequest, session: SessionDep
) -> dict[str, Any]:
    from .ids import new_id

    run = get_run_or_404(session, run_id)
    blueprint = find_blueprint(run.state, payload.blueprint_id)
    if blueprint is None:
        raise HTTPException(status_code=409, detail="This ship blueprint is not unlocked")
    agents = _state_values(run.state, "agents")
    root = next((node for node in _state_values(run.state, "nodes") if not node.get("parent_node_id")), None)
    ship_id = new_id("agent")
    agent = {
        "id": ship_id,
        "schema_version": 1,
        "run_id": run_id,
        "parent_agent_id": None,
        "name": ship_name(blueprint, agents),
        "role": blueprint.role,
        "model": "configured-codex-default",
        "provider": "openai-codex",
        "framework": "evolastra-shipyard",
        "status": "created",
        "current_node_id": str(root.get("id") if root else run_id),
        "capabilities": list(blueprint.capabilities),
        "permissions_profile": "workspace-write-no-escalation",
        "tool_access_profile": ["codex-app-server"],
        "ship_blueprint_id": blueprint.id,
        "ship_hull": blueprint.hull,
        "blueprint_source_node_id": blueprint.source_node_id,
        "built_at": datetime.now(UTC).isoformat(),
    }
    event = make_event(
        run_id=run_id,
        event_type="galaxy.analysis.agent.created.v1",
        subject=f"run/{run_id}/agent/{ship_id}",
        data={"agent": agent},
        source="urn:galaxy:shipyard",
    )
    result = EventStore(session).ingest(event.model_dump(mode="json"))
    if not result.accepted:
        raise HTTPException(status_code=409, detail=result.reason or "Ship could not be built")
    return {"ship": agent, "event": result.model_dump(mode="json")}


@router.post("/runs/{run_id}/ships/{ship_id}/dispatch", status_code=status.HTTP_202_ACCEPTED)
def dispatch_ship(
    run_id: str, ship_id: str, payload: ShipDispatchRequest, session: SessionDep
) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    settings = get_settings()
    if not settings.codex_dispatch_enabled:
        raise HTTPException(
            status_code=409,
            detail="Codex dispatch is available only through the installed Local Private companion",
        )
    agents = run.state.get("agents", {})
    ship = agents.get(ship_id) if isinstance(agents, dict) else None
    if not isinstance(ship, dict) or ship.get("framework") != "evolastra-shipyard":
        raise HTTPException(status_code=404, detail="Ship not found")
    if ship.get("status") == "running":
        raise HTTPException(status_code=409, detail="This ship already has an active mission")
    blueprint = find_blueprint(run.state, str(ship.get("ship_blueprint_id") or ""))
    if blueprint is None:
        raise HTTPException(status_code=409, detail="The ship's blueprint is no longer available")
    prompt = mission_prompt(
        blueprint=blueprint,
        ship=ship,
        run={**run.state.get("run", {}), "title": run.title, "objective": run.objective},
        user_prompt=payload.prompt,
    )
    workspace = settings.codex_workspace_root.expanduser().resolve()
    if not (workspace / ".git").exists():
        raise HTTPException(status_code=409, detail="The configured Codex workspace is not a Git repository")

    def record_started(receipt: MissionReceipt) -> None:
        started = {
            **ship,
            "status": "running",
            "current_task": f"Codex mission {receipt.thread_id}",
            "prompt": payload.prompt,
            "codex_thread_id": receipt.thread_id,
            "codex_turn_id": receipt.turn_id,
            "mission_started_at": datetime.now(UTC).isoformat(),
        }
        event = make_event(
            run_id=run_id,
            event_type="galaxy.analysis.agent.started.v1",
            subject=f"run/{run_id}/agent/{ship_id}",
            data={"agent": started},
            source="urn:galaxy:shipyard",
        )
        result = EventStore(session).ingest(event.model_dump(mode="json"))
        if not result.accepted:
            raise HTTPException(status_code=409, detail=result.reason or "Mission could not be recorded")

    try:
        receipt = dispatch_codex_mission(
            ship_id=ship_id,
            cwd=workspace,
            prompt=prompt,
            developer_instructions=mission_developer_instructions(blueprint),
            started=record_started,
            completion=lambda completed_receipt, mission_status, mission_error: _mission_completed(
                run_id=run_id,
                ship_id=ship_id,
                thread_id=completed_receipt.thread_id,
                turn_id=completed_receipt.turn_id,
                status_value=mission_status,
                error=mission_error,
            ),
        )
    except CodexDispatchError as error:
        raise HTTPException(
            status_code=503,
            detail="Codex mission could not be started inside the required safety boundary",
        ) from error
    return {
        "accepted": True,
        "ship_id": ship_id,
        "thread_id": receipt.thread_id,
        "turn_id": receipt.turn_id,
        "status": "running",
    }


@router.post("/runs/{run_id}/approvals/{approval_id}")
def record_approval(
    run_id: str, approval_id: str, payload: ApprovalRequest, session: SessionDep
) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    approvals = run.state.get("approvals", {})
    current = approvals.get(approval_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    approval = {
        **current,
        "status": payload.decision,
        "note": payload.note,
        "decided_by": "local-operator",
        "decided_at": datetime.now(UTC).isoformat(),
    }
    event = make_event(
        run_id=run_id,
        event_type="galaxy.analysis.approval.recorded.v1",
        subject=f"run/{run_id}/approval/{approval_id}",
        data={"approval": approval},
        source="urn:galaxy:ui",
    )
    result = EventStore(session).ingest(event.model_dump(mode="json"))
    if payload.decision == "approved" and result.accepted:
        from .ids import new_id

        report_id = new_id("art")
        report = {
            "id": report_id,
            "run_id": run_id,
            "node_id": next(iter(run.state.get("nodes", {})), None),
            "artifact_type": "markdown",
            "title": "Final evidence synthesis",
            "description": "Approved final report with claims, caveats, and reproduction status.",
            "mime_type": "text/markdown",
            "preview_status": "ready",
            "preview": {
                "kind": "markdown",
                "text": "The strongest evidence concerns early-tenure concentration. Associations are observational and should not be read as causal.",
            },
        }
        EventStore(session).ingest(
            make_event(
                run_id=run_id,
                event_type="galaxy.analysis.artifact.created.v1",
                subject=f"run/{run_id}/artifact/{report_id}",
                data={"artifact": report},
                source="urn:galaxy:simulator",
            ).model_dump(mode="json")
        )
        EventStore(session).ingest(
            make_event(
                run_id=run_id,
                event_type="galaxy.analysis.run.completed.v1",
                subject=f"run/{run_id}",
                data={
                    "run": {
                        "id": run_id,
                        "status": "completed",
                        "completion_time": datetime.now(UTC).isoformat(),
                        "summary": "Approved synthesis completed",
                        "final_artifact_ids": [report_id],
                    }
                },
                source="urn:galaxy:simulator",
            ).model_dump(mode="json")
        )
    return result.model_dump(mode="json")


@router.post("/demo/start")
async def start_seeded_demo(
    speed: float = Query(default=6.0, ge=0.1, le=50.0),
) -> dict[str, Any]:
    return start_demo(speed)


@router.get("/search")
def search_entities(
    session: SessionDep,
    q: str = Query(min_length=2, max_length=200),
    run_id: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    query = select(RunRecord)
    if run_id:
        query = query.where(RunRecord.id == run_id)
    records = session.scalars(query.order_by(RunRecord.updated_at.desc()).limit(100)).all()
    needle = q.casefold()
    results: list[dict[str, Any]] = []
    for run in records:
        if needle in f"{run.title} {run.objective}".casefold():
            results.append(
                {
                    "id": run.id,
                    "run_id": run.id,
                    "entity_type": "run",
                    "title": run.title,
                    "context": run.objective,
                    "status": run.status,
                }
            )
        for entity_type in (
            "nodes",
            "agents",
            "artifacts",
            "claims",
            "findings",
            "datasets",
            "anomalies",
            "tool_calls",
        ):
            for item in run.state.get(entity_type, {}).values():
                haystack = " ".join(
                    str(item.get(key, ""))
                    for key in (
                        "title",
                        "name",
                        "summary",
                        "statement",
                        "description",
                        "error",
                        "tool_name",
                    )
                )
                if needle in haystack.casefold():
                    results.append(
                        {
                            "id": item["id"],
                            "run_id": run.id,
                            "entity_type": entity_type.rstrip("s"),
                            "title": item.get("title")
                            or item.get("name")
                            or item.get("tool_name")
                            or item["id"],
                            "context": item.get("summary")
                            or item.get("description")
                            or item.get("statement")
                            or "",
                            "status": item.get("status"),
                        }
                    )
                if len(results) >= limit:
                    return {"items": results, "query": q}
    return {"items": results[:limit], "query": q}


@router.get("/runs/{run_id}/entities/{entity_type}")
def list_entities(run_id: str, entity_type: str, session: SessionDep) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    allowed = {
        "nodes",
        "agents",
        "tool_calls",
        "datasets",
        "dataset_versions",
        "artifacts",
        "claims",
        "evidence",
        "findings",
        "anomalies",
        "approvals",
        "metrics",
    }
    if entity_type not in allowed:
        raise HTTPException(status_code=404, detail="Entity collection not found")
    value = run.state.get(entity_type, {})
    return {"items": list(value.values()) if isinstance(value, dict) else value}


@router.get("/runs/{run_id}/artifacts/{artifact_id}/preview")
def artifact_preview(run_id: str, artifact_id: str, session: SessionDep) -> dict[str, Any]:
    run = get_run_or_404(session, run_id)
    artifact = run.state.get("artifacts", {}).get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"artifact": artifact, "bounded": True, "executed": False}


@router.get("/runs/{run_id}/export/{format_name}")
def export_run(run_id: str, format_name: str, session: SessionDep) -> Response:
    run = get_run_or_404(session, run_id)
    events = session.scalars(
        select(EventRecord).where(EventRecord.run_id == run_id).order_by(EventRecord.sequence)
    ).all()
    if format_name == "cloudevents":
        return Response(
            cloudevents_jsonl(events),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.jsonl"'},
        )
    if format_name == "openlineage":
        return Response(
            json_bytes(openlineage_export(run)),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.openlineage.json"'},
        )
    if format_name == "prov":
        return Response(
            json_bytes(prov_export(run)),
            media_type="application/ld+json",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.prov.jsonld"'},
        )
    if format_name == "obsidian":
        return Response(
            obsidian_zip(run),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.obsidian.zip"'},
        )
    if format_name == "reproduction":
        return Response(
            reproduction_zip(run, events),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.reproduction.zip"'},
        )
    if format_name == "portable":
        return Response(
            portable_bundle(run, events),
            media_type="application/vnd.evolastra.analysis+zip",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.evolastra"'},
        )
    raise HTTPException(status_code=404, detail="Export format not found")


@router.get("/runs/compare/{left_id}/{right_id}")
def compare_runs(left_id: str, right_id: str, session: SessionDep) -> dict[str, Any]:
    left = get_run_or_404(session, left_id)
    right = get_run_or_404(session, right_id)
    return {
        "left": run_summary(left),
        "right": run_summary(right),
        "delta": {
            key: len(right.state.get(key, {})) - len(left.state.get(key, {}))
            for key in ("nodes", "agents", "artifacts", "claims", "findings", "anomalies")
        },
    }
