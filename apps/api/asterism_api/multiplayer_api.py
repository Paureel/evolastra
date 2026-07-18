from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import bearer_scheme, require_api_access
from .config import get_settings
from .database import get_session
from .db_models import MultiplayerSessionRecord, RunRecord
from .multiplayer import (
    MultiplayerError,
    authenticate_invite,
    authenticate_member,
    claim_node,
    close_local_session,
    create_host_session,
    join_host,
    join_remote_session,
    local_finding,
    publish_finding,
    refresh_guest_session,
    release_node,
    remote_member_action,
    remove_member,
    renew_host_invite,
    session_snapshot,
    tailscale_readiness,
    touch_local_player,
)
from .schemas import (
    FederationClaimRequest,
    FederationJoinRequest,
    FederationPublishRequest,
    MultiplayerClaimRequest,
    MultiplayerHostRequest,
    MultiplayerJoinRequest,
    MultiplayerPublishRequest,
)

SessionDep = Annotated[Session, Depends(get_session)]
local_router = APIRouter(prefix="/api/v1/multiplayer", dependencies=[Depends(require_api_access)])
federation_router = APIRouter(prefix="/api/v1/federation")


def _error(error: MultiplayerError, status_code: int = 409) -> HTTPException:
    return HTTPException(status_code=status_code, detail=str(error))


def _require_local_private() -> None:
    if get_settings().deployment_profile != "local-private":
        raise HTTPException(
            status_code=409,
            detail="Multiplayer is available only through the installed Local Private companion",
        )


def _local_session(db: Session, run_id: str) -> MultiplayerSessionRecord | None:
    return db.scalar(
        select(MultiplayerSessionRecord).where(MultiplayerSessionRecord.run_id == run_id)
    )


def _require_local_session(db: Session, run_id: str) -> MultiplayerSessionRecord:
    session = _local_session(db, run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="No multiplayer session is active for this project")
    return session


def _bearer(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status_code=401, detail="A multiplayer invite or member grant is required")
    return credentials.credentials


def _tailnet_request(request: Request) -> None:
    settings = get_settings()
    if (
        settings.deployment_profile == "local-private"
        and not request.headers.get("tailscale-user-login")
    ):
        raise HTTPException(status_code=403, detail="Federation requests must arrive through Tailscale Serve")


@local_router.get("/readiness")
def multiplayer_readiness() -> dict[str, Any]:
    return tailscale_readiness(get_settings().companion_port)


@local_router.get("/runs/{run_id}")
def multiplayer_state(run_id: str, db: SessionDep) -> dict[str, Any]:
    session = _local_session(db, run_id)
    if session is None:
        return {"enabled": False}
    if session.mode == "guest":
        return refresh_guest_session(db, session)
    touch_local_player(db, session)
    return session_snapshot(db, session)


@local_router.post("/host", status_code=status.HTTP_201_CREATED)
def host_multiplayer(payload: MultiplayerHostRequest, db: SessionDep) -> dict[str, Any]:
    _require_local_private()
    run = db.get(RunRecord, payload.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    try:
        session, invite_code = create_host_session(
            db,
            run=run,
            display_name=payload.display_name,
            color=payload.color,
            share_url=payload.share_url,
        )
    except MultiplayerError as error:
        raise _error(error) from error
    return {"state": session_snapshot(db, session), "invite_code": invite_code}


@local_router.post("/join", status_code=status.HTTP_201_CREATED)
def join_multiplayer(payload: MultiplayerJoinRequest, db: SessionDep) -> dict[str, Any]:
    _require_local_private()
    try:
        session = join_remote_session(
            db,
            invite_code=payload.invite_code,
            display_name=payload.display_name,
            color=payload.color,
        )
        return refresh_guest_session(db, session)
    except MultiplayerError as error:
        raise _error(error, 503 if "unreachable" in str(error).casefold() else 409) from error


@local_router.post("/runs/{run_id}/claims")
def claim_multiplayer_system(
    run_id: str, payload: MultiplayerClaimRequest, db: SessionDep
) -> dict[str, Any]:
    session = _require_local_session(db, run_id)
    try:
        if session.mode == "guest":
            remote_member_action(
                session,
                method="POST",
                suffix="/claims",
                payload={"node_id": payload.node_id},
            )
            return refresh_guest_session(db, session)
        claim_node(db, session=session, player_id=session.local_player_id, node_id=payload.node_id)
        return session_snapshot(db, session)
    except MultiplayerError as error:
        raise _error(error) from error


@local_router.post("/runs/{run_id}/invite")
def renew_multiplayer_invite(run_id: str, db: SessionDep) -> dict[str, str]:
    session = _require_local_session(db, run_id)
    try:
        return {"invite_code": renew_host_invite(db, session)}
    except MultiplayerError as error:
        raise _error(error) from error


@local_router.delete("/runs/{run_id}/claims/{node_id}")
def release_multiplayer_system(run_id: str, node_id: str, db: SessionDep) -> dict[str, Any]:
    session = _require_local_session(db, run_id)
    try:
        if session.mode == "guest":
            remote_member_action(session, method="DELETE", suffix=f"/claims/{node_id}")
            return refresh_guest_session(db, session)
        release_node(db, session=session, player_id=session.local_player_id, node_id=node_id)
        return session_snapshot(db, session)
    except MultiplayerError as error:
        raise _error(error) from error


@local_router.post("/runs/{run_id}/publications")
def publish_multiplayer_finding(
    run_id: str, payload: MultiplayerPublishRequest, db: SessionDep
) -> dict[str, Any]:
    session = _require_local_session(db, run_id)
    run = db.get(RunRecord, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    try:
        title, summary = local_finding(run, payload.finding_id)
        if session.mode == "guest":
            remote_member_action(
                session,
                method="POST",
                suffix="/publications",
                payload={
                    "finding_id": payload.finding_id,
                    "title": title,
                    "summary": summary,
                },
            )
            return refresh_guest_session(db, session)
        publish_finding(
            db,
            session=session,
            player_id=session.local_player_id,
            finding_id=payload.finding_id,
            title=title,
            summary=summary,
        )
        return session_snapshot(db, session)
    except MultiplayerError as error:
        raise _error(error) from error


@local_router.delete("/runs/{run_id}")
def leave_multiplayer(run_id: str, db: SessionDep) -> dict[str, bool]:
    session = _require_local_session(db, run_id)
    if session.mode == "guest":
        try:
            remote_member_action(session, method="DELETE", suffix="/members/self")
        except MultiplayerError:
            pass
    close_local_session(db, session)
    return {"closed": True}


@federation_router.post("/sessions/{session_id}/join", dependencies=[Depends(_tailnet_request)])
def federation_join(
    session_id: str,
    payload: FederationJoinRequest,
    db: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    try:
        session = authenticate_invite(db, session_id, _bearer(credentials))
        player, member_token = join_host(
            db,
            session=session,
            display_name=payload.display_name,
            color=payload.color,
            fingerprint=payload.project_fingerprint,
        )
        return {
            "member_token": member_token,
            "player": {"id": player.id, "display_name": player.display_name, "color": player.color},
            "state": session_snapshot(db, session),
        }
    except MultiplayerError as error:
        raise _error(error, 401) from error


@federation_router.get("/sessions/{session_id}", dependencies=[Depends(_tailnet_request)])
def federation_state(
    session_id: str,
    db: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    try:
        session, _ = authenticate_member(db, session_id, _bearer(credentials))
        return session_snapshot(db, session)
    except MultiplayerError as error:
        raise _error(error, 401) from error


@federation_router.post("/sessions/{session_id}/claims", dependencies=[Depends(_tailnet_request)])
def federation_claim(
    session_id: str,
    payload: FederationClaimRequest,
    db: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    try:
        session, player = authenticate_member(db, session_id, _bearer(credentials))
        claim_node(db, session=session, player_id=player.id, node_id=payload.node_id)
        return session_snapshot(db, session)
    except MultiplayerError as error:
        raise _error(error) from error


@federation_router.delete(
    "/sessions/{session_id}/claims/{node_id}", dependencies=[Depends(_tailnet_request)]
)
def federation_release(
    session_id: str,
    node_id: str,
    db: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    try:
        session, player = authenticate_member(db, session_id, _bearer(credentials))
        release_node(db, session=session, player_id=player.id, node_id=node_id)
        return session_snapshot(db, session)
    except MultiplayerError as error:
        raise _error(error) from error


@federation_router.post(
    "/sessions/{session_id}/publications", dependencies=[Depends(_tailnet_request)]
)
def federation_publish(
    session_id: str,
    payload: FederationPublishRequest,
    db: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    try:
        session, player = authenticate_member(db, session_id, _bearer(credentials))
        publish_finding(
            db,
            session=session,
            player_id=player.id,
            finding_id=payload.finding_id,
            title=payload.title,
            summary=payload.summary,
        )
        return session_snapshot(db, session)
    except MultiplayerError as error:
        raise _error(error) from error


@federation_router.delete(
    "/sessions/{session_id}/members/self", dependencies=[Depends(_tailnet_request)]
)
def federation_leave(
    session_id: str,
    db: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, bool]:
    try:
        session, player = authenticate_member(db, session_id, _bearer(credentials))
        remove_member(db, session=session, player=player)
        return {"left": True}
    except MultiplayerError as error:
        raise _error(error) from error
