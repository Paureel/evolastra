from __future__ import annotations

import base64
import hashlib
import json
import secrets
import shutil
import subprocess
import threading
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .db_models import (
    MultiplayerClaimRecord,
    MultiplayerPlayerRecord,
    MultiplayerPublicationRecord,
    MultiplayerSessionRecord,
    RunRecord,
)
from .ids import new_id

INVITE_PREFIX = "EVO1."
PRESENCE_SECONDS = 30
MAX_PLAYERS = 24
MAX_PUBLICATIONS = 500
_guest_token_lock = threading.RLock()
_guest_tokens: dict[str, str] = {}


class MultiplayerError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project_fingerprint(run: RunRecord) -> str:
    return _digest(f"evolastra-project-v1:{run.id}:{run.seed}:{run.schema_version}")


def normalize_share_url(raw: str) -> str:
    parsed = urlparse(raw.strip())
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not host.endswith(".ts.net"):
        raise MultiplayerError("The multiplayer URL must be an HTTPS Tailscale Serve address ending in .ts.net")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise MultiplayerError("The multiplayer URL cannot contain credentials, a query, or a fragment")
    path = parsed.path.rstrip("/")
    if path:
        raise MultiplayerError("Use the root Tailscale Serve URL without a path")
    try:
        parsed_port = parsed.port
    except ValueError as error:
        raise MultiplayerError("The multiplayer URL contains an invalid port") from error
    port = f":{parsed_port}" if parsed_port else ""
    return f"https://{host}{port}"


def encode_invite(*, session: MultiplayerSessionRecord, secret: str) -> str:
    payload = {
        "v": 1,
        "session_id": session.id,
        "run_id": session.run_id,
        "fingerprint": session.project_fingerprint,
        "url": session.host_url,
        "secret": secret,
        "expires_at": session.invite_expires_at.isoformat() if session.invite_expires_at else None,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"{INVITE_PREFIX}{encoded}"


def decode_invite(code: str) -> dict[str, str]:
    value = code.strip()
    if not value.startswith(INVITE_PREFIX):
        raise MultiplayerError("This is not an Evolastra multiplayer invite")
    encoded = value.removeprefix(INVITE_PREFIX)
    try:
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as error:
        raise MultiplayerError("The multiplayer invite is malformed") from error
    required = ("session_id", "run_id", "fingerprint", "url", "secret", "expires_at")
    if not isinstance(payload, dict) or any(not isinstance(payload.get(key), str) for key in required):
        raise MultiplayerError("The multiplayer invite is incomplete")
    if payload.get("v") != 1 or len(payload["secret"]) < 32:
        raise MultiplayerError("The multiplayer invite version or secret is invalid")
    try:
        expires_at = datetime.fromisoformat(payload["expires_at"])
    except ValueError as error:
        raise MultiplayerError("The multiplayer invite expiry is invalid") from error
    if _aware(expires_at) <= _now():
        raise MultiplayerError("The multiplayer invite has expired")
    payload["url"] = normalize_share_url(payload["url"])
    return {key: str(payload[key]) for key in required}


def _clear_session_rows(db: Session, session_id: str) -> None:
    for model in (MultiplayerClaimRecord, MultiplayerPublicationRecord, MultiplayerPlayerRecord):
        db.execute(delete(model).where(model.session_id == session_id))


def delete_session_for_run(db: Session, run_id: str) -> None:
    session = db.scalar(
        select(MultiplayerSessionRecord).where(MultiplayerSessionRecord.run_id == run_id)
    )
    if session is None:
        return
    with _guest_token_lock:
        _guest_tokens.pop(session.id, None)
    _clear_session_rows(db, session.id)
    db.delete(session)


def create_host_session(
    db: Session,
    *,
    run: RunRecord,
    display_name: str,
    color: str,
    share_url: str,
    invite_ttl_seconds: int = 86_400,
) -> tuple[MultiplayerSessionRecord, str]:
    existing = db.scalar(
        select(MultiplayerSessionRecord).where(MultiplayerSessionRecord.run_id == run.id)
    )
    if existing is not None:
        _clear_session_rows(db, existing.id)
        db.delete(existing)
        db.flush()
    now = _now()
    secret = secrets.token_urlsafe(48)
    session = MultiplayerSessionRecord(
        id=new_id("session"),
        run_id=run.id,
        mode="host",
        project_fingerprint=project_fingerprint(run),
        host_url=normalize_share_url(share_url),
        local_player_id=new_id("player"),
        invite_digest=_digest(secret),
        invite_expires_at=now + timedelta(seconds=invite_ttl_seconds),
        remote_state={},
        status="active",
        revision=1,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.add(
        MultiplayerPlayerRecord(
            id=session.local_player_id,
            session_id=session.id,
            display_name=display_name.strip(),
            color=color.upper(),
            role="host",
            token_digest=None,
            joined_at=now,
            last_seen_at=now,
        )
    )
    root = next(
        (
            node
            for node in _state_values(run.state, "nodes")
            if not node.get("parent_node_id") and node.get("id")
        ),
        None,
    )
    if root is not None:
        db.add(
            MultiplayerClaimRecord(
                id=new_id("claim"),
                session_id=session.id,
                node_id=str(root["id"]),
                player_id=session.local_player_id,
                claimed_at=now,
            )
        )
    db.commit()
    return session, encode_invite(session=session, secret=secret)


def renew_host_invite(
    db: Session, session: MultiplayerSessionRecord, invite_ttl_seconds: int = 86_400
) -> str:
    if session.mode != "host" or session.status != "active":
        raise MultiplayerError("Only the active host can create an invite")
    secret = secrets.token_urlsafe(48)
    session.invite_digest = _digest(secret)
    session.invite_expires_at = _now() + timedelta(seconds=invite_ttl_seconds)
    session.updated_at = _now()
    db.commit()
    return encode_invite(session=session, secret=secret)


def _state_values(state: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = state.get(key, {})
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _session_run(db: Session, session: MultiplayerSessionRecord) -> RunRecord:
    run = db.get(RunRecord, session.run_id)
    if run is None:
        raise MultiplayerError("The shared project is no longer available on the host")
    return run


def _touch(db: Session, session: MultiplayerSessionRecord, player_id: str) -> None:
    player = db.get(MultiplayerPlayerRecord, player_id)
    if player is not None and player.session_id == session.id:
        player.last_seen_at = _now()
    session.updated_at = _now()


def touch_local_player(db: Session, session: MultiplayerSessionRecord) -> None:
    _touch(db, session, session.local_player_id)
    db.commit()


def _advance(session: MultiplayerSessionRecord) -> None:
    session.revision += 1
    session.updated_at = _now()


def session_snapshot(db: Session, session: MultiplayerSessionRecord) -> dict[str, Any]:
    run = _session_run(db, session)
    now = _now()
    players = list(
        db.scalars(
            select(MultiplayerPlayerRecord)
            .where(MultiplayerPlayerRecord.session_id == session.id)
            .order_by(MultiplayerPlayerRecord.joined_at)
        )
    )
    claims = list(
        db.scalars(
            select(MultiplayerClaimRecord)
            .where(MultiplayerClaimRecord.session_id == session.id)
            .order_by(MultiplayerClaimRecord.claimed_at)
        )
    )
    publications = list(
        db.scalars(
            select(MultiplayerPublicationRecord)
            .where(MultiplayerPublicationRecord.session_id == session.id)
            .order_by(MultiplayerPublicationRecord.published_at.desc())
            .limit(100)
        )
    )
    simulation_active = bool(
        isinstance(session.remote_state, dict) and session.remote_state.get("simulation_active")
    )
    return {
        "enabled": True,
        "session": {
            "id": session.id,
            "run_id": session.run_id,
            "mode": session.mode,
            "status": session.status,
            "revision": session.revision,
            "host_url": session.host_url,
            "project_fingerprint": session.project_fingerprint,
            "local_player_id": session.local_player_id,
            "title": run.title,
            "simulation_active": simulation_active,
        },
        "players": [
            {
                "id": player.id,
                "display_name": player.display_name,
                "color": player.color,
                "role": player.role,
                "online": session.status == "active"
                and (
                    simulation_active
                    or (now - _aware(player.last_seen_at)).total_seconds() <= PRESENCE_SECONDS
                ),
                "last_seen_at": _aware(player.last_seen_at).isoformat(),
            }
            for player in players
        ],
        "claims": [
            {
                "id": claim.id,
                "node_id": claim.node_id,
                "player_id": claim.player_id,
                "claimed_at": _aware(claim.claimed_at).isoformat(),
            }
            for claim in claims
        ],
        "publications": [
            {
                "id": publication.id,
                "finding_id": publication.finding_id,
                "player_id": publication.player_id,
                "title": publication.title,
                "summary": publication.summary,
                "published_at": _aware(publication.published_at).isoformat(),
            }
            for publication in publications
        ],
    }


def authenticate_invite(db: Session, session_id: str, secret: str) -> MultiplayerSessionRecord:
    session = db.get(MultiplayerSessionRecord, session_id)
    if (
        session is None
        or session.mode != "host"
        or session.status != "active"
        or session.invite_digest is None
        or session.invite_expires_at is None
        or _aware(session.invite_expires_at) <= _now()
        or not secrets.compare_digest(session.invite_digest, _digest(secret))
    ):
        raise MultiplayerError("The multiplayer invite is invalid, expired, or closed")
    return session


def authenticate_member(
    db: Session, session_id: str, member_token: str
) -> tuple[MultiplayerSessionRecord, MultiplayerPlayerRecord]:
    session = db.get(MultiplayerSessionRecord, session_id)
    digest = _digest(member_token)
    player = db.scalar(
        select(MultiplayerPlayerRecord).where(
            MultiplayerPlayerRecord.session_id == session_id,
            MultiplayerPlayerRecord.token_digest == digest,
        )
    )
    if session is None or session.mode != "host" or player is None:
        raise MultiplayerError("The multiplayer member grant is invalid or the session is closed")
    _touch(db, session, player.id)
    db.commit()
    return session, player


def join_host(
    db: Session,
    *,
    session: MultiplayerSessionRecord,
    display_name: str,
    color: str,
    fingerprint: str,
) -> tuple[MultiplayerPlayerRecord, str]:
    if not secrets.compare_digest(session.project_fingerprint, fingerprint):
        raise MultiplayerError("Load the same Evolastra analysis before joining this session")
    existing_name = db.scalar(
        select(MultiplayerPlayerRecord).where(
            MultiplayerPlayerRecord.session_id == session.id,
            MultiplayerPlayerRecord.display_name == display_name.strip(),
        )
    )
    if existing_name is not None:
        offline = (_now() - _aware(existing_name.last_seen_at)).total_seconds() > PRESENCE_SECONDS
        if offline and existing_name.color == color.upper() and existing_name.role == "member":
            token = secrets.token_urlsafe(48)
            existing_name.token_digest = _digest(token)
            existing_name.last_seen_at = _now()
            _advance(session)
            db.commit()
            return existing_name, token
        raise MultiplayerError("That player name is already in use")
    if db.scalar(
        select(MultiplayerPlayerRecord).where(
            MultiplayerPlayerRecord.session_id == session.id,
            MultiplayerPlayerRecord.color == color.upper(),
        )
    ):
        raise MultiplayerError("That territory color is already in use")
    player_count = db.scalar(
        select(func.count()).select_from(MultiplayerPlayerRecord).where(
            MultiplayerPlayerRecord.session_id == session.id
        )
    )
    if int(player_count or 0) >= MAX_PLAYERS:
        raise MultiplayerError(f"This Phase 1 federation is limited to {MAX_PLAYERS} players")
    token = secrets.token_urlsafe(48)
    now = _now()
    player = MultiplayerPlayerRecord(
        id=new_id("player"),
        session_id=session.id,
        display_name=display_name.strip(),
        color=color.upper(),
        role="member",
        token_digest=_digest(token),
        joined_at=now,
        last_seen_at=now,
    )
    db.add(player)
    _advance(session)
    db.commit()
    return player, token


def claim_node(
    db: Session, *, session: MultiplayerSessionRecord, player_id: str, node_id: str
) -> None:
    if session.status != "active":
        raise MultiplayerError("The multiplayer session is not active")
    run = _session_run(db, session)
    if not any(str(node.get("id")) == node_id for node in _state_values(run.state, "nodes")):
        raise MultiplayerError("That analysis system does not exist in the shared project")
    existing = db.scalar(
        select(MultiplayerClaimRecord).where(
            MultiplayerClaimRecord.session_id == session.id,
            MultiplayerClaimRecord.node_id == node_id,
        )
    )
    if existing is not None and existing.player_id != player_id:
        owner = db.get(MultiplayerPlayerRecord, existing.player_id)
        label = owner.display_name if owner else "another player"
        raise MultiplayerError(f"This system is already claimed by {label}")
    if existing is None:
        db.add(
            MultiplayerClaimRecord(
                id=new_id("claim"),
                session_id=session.id,
                node_id=node_id,
                player_id=player_id,
                claimed_at=_now(),
            )
        )
        _advance(session)
    _touch(db, session, player_id)
    db.commit()


def release_node(
    db: Session, *, session: MultiplayerSessionRecord, player_id: str, node_id: str
) -> None:
    if session.status != "active":
        raise MultiplayerError("The multiplayer session is not active")
    claim = db.scalar(
        select(MultiplayerClaimRecord).where(
            MultiplayerClaimRecord.session_id == session.id,
            MultiplayerClaimRecord.node_id == node_id,
        )
    )
    if claim is None or claim.player_id != player_id:
        raise MultiplayerError("You can release only a system you claimed")
    db.delete(claim)
    _advance(session)
    _touch(db, session, player_id)
    db.commit()


def publish_finding(
    db: Session,
    *,
    session: MultiplayerSessionRecord,
    player_id: str,
    finding_id: str,
    title: str,
    summary: str,
) -> MultiplayerPublicationRecord:
    if session.status != "active":
        raise MultiplayerError("The multiplayer session is not active")
    publication_count = db.scalar(
        select(func.count()).select_from(MultiplayerPublicationRecord).where(
            MultiplayerPublicationRecord.session_id == session.id
        )
    )
    if int(publication_count or 0) >= MAX_PUBLICATIONS:
        raise MultiplayerError("This federation has reached its Phase 1 publication limit")
    publication = MultiplayerPublicationRecord(
        id=new_id("publication"),
        session_id=session.id,
        player_id=player_id,
        finding_id=finding_id,
        title=title.strip()[:300],
        summary=summary.strip()[:2_000],
        published_at=_now(),
    )
    db.add(publication)
    _advance(session)
    _touch(db, session, player_id)
    db.commit()
    return publication


def remove_member(
    db: Session, *, session: MultiplayerSessionRecord, player: MultiplayerPlayerRecord
) -> None:
    if player.role == "host":
        raise MultiplayerError("The host closes the federation instead of leaving it")
    db.execute(
        delete(MultiplayerClaimRecord).where(
            MultiplayerClaimRecord.session_id == session.id,
            MultiplayerClaimRecord.player_id == player.id,
        )
    )
    db.delete(player)
    _advance(session)
    db.commit()


def local_finding(run: RunRecord, finding_id: str) -> tuple[str, str]:
    finding = next(
        (item for item in _state_values(run.state, "findings") if str(item.get("id")) == finding_id),
        None,
    )
    if finding is None:
        raise MultiplayerError("Select a local finding from this analysis before publishing")
    title = str(finding.get("title") or finding.get("statement") or "Published finding")[:300]
    summary = str(
        finding.get("summary") or finding.get("description") or finding.get("statement") or title
    )[:2_000]
    return title, summary


def _remote_request(
    *, host_url: str, method: str, path: str, token: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=8, follow_redirects=False, trust_env=False) as client:
            response = client.request(
                method,
                f"{normalize_share_url(host_url)}{path}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                json=payload,
            )
    except (httpx.HTTPError, MultiplayerError) as error:
        raise MultiplayerError("The host is unreachable through Tailscale") from error
    if response.status_code >= 400:
        try:
            detail = str(response.json().get("detail") or "The host rejected the request")
        except (ValueError, AttributeError):
            detail = "The host rejected the request"
        raise MultiplayerError(detail[:500])
    result = response.json()
    if not isinstance(result, dict):
        raise MultiplayerError("The host returned an invalid multiplayer response")
    return result


def join_remote_session(
    db: Session, *, invite_code: str, display_name: str, color: str
) -> MultiplayerSessionRecord:
    invite = decode_invite(invite_code)
    run = db.get(RunRecord, invite["run_id"])
    if run is None or not secrets.compare_digest(project_fingerprint(run), invite["fingerprint"]):
        raise MultiplayerError("Load the matching .evolastra analysis on this computer before joining")
    result = _remote_request(
        host_url=invite["url"],
        method="POST",
        path=f"/api/v1/federation/sessions/{invite['session_id']}/join",
        token=invite["secret"],
        payload={
            "display_name": display_name.strip(),
            "color": color.upper(),
            "project_fingerprint": invite["fingerprint"],
        },
    )
    member_token = result.get("member_token")
    state = result.get("state")
    player = result.get("player")
    if not isinstance(member_token, str) or not isinstance(state, dict) or not isinstance(player, dict):
        raise MultiplayerError("The host returned an incomplete member grant")
    existing = db.scalar(
        select(MultiplayerSessionRecord).where(MultiplayerSessionRecord.run_id == run.id)
    )
    if existing is not None:
        _clear_session_rows(db, existing.id)
        db.delete(existing)
        db.flush()
    now = _now()
    session = MultiplayerSessionRecord(
        id=invite["session_id"],
        run_id=run.id,
        mode="guest",
        project_fingerprint=invite["fingerprint"],
        host_url=invite["url"],
        local_player_id=str(player.get("id")),
        invite_digest=None,
        invite_expires_at=None,
        remote_state=state,
        status="active",
        revision=int(state.get("session", {}).get("revision", 1)),
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    with _guest_token_lock:
        _guest_tokens[session.id] = member_token
    return session


def refresh_guest_session(db: Session, session: MultiplayerSessionRecord) -> dict[str, Any]:
    with _guest_token_lock:
        member_token = _guest_tokens.get(session.id)
    if member_token is None:
        session.status = "paused"
        db.commit()
        stale = dict(session.remote_state or {})
        stale_session = dict(stale.get("session") or {})
        stale_session.update({"status": "paused", "mode": "guest", "local_player_id": session.local_player_id})
        stale.update({
            "enabled": True,
            "session": stale_session,
            "connection_error": "Rejoin with a fresh invite after the companion restarts",
        })
        return stale
    try:
        state = _remote_request(
            host_url=session.host_url,
            method="GET",
            path=f"/api/v1/federation/sessions/{session.id}",
            token=member_token,
        )
    except MultiplayerError as error:
        session.status = "paused"
        session.updated_at = _now()
        db.commit()
        stale = dict(session.remote_state or {})
        stale_session = dict(stale.get("session") or {})
        stale_session.update({"status": "paused", "mode": "guest", "local_player_id": session.local_player_id})
        stale.update({"enabled": True, "session": stale_session, "connection_error": str(error)})
        return stale
    state_session = state.get("session")
    if not isinstance(state_session, dict):
        raise MultiplayerError("The host returned an invalid session snapshot")
    state_session["mode"] = "guest"
    state_session["local_player_id"] = session.local_player_id
    session.remote_state = state
    session.status = str(state_session.get("status") or "active")
    session.revision = int(state_session.get("revision") or session.revision)
    session.updated_at = _now()
    db.commit()
    return state


def remote_member_action(
    session: MultiplayerSessionRecord,
    *,
    method: str,
    suffix: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with _guest_token_lock:
        member_token = _guest_tokens.get(session.id)
    if member_token is None:
        raise MultiplayerError("The local member grant is missing")
    return _remote_request(
        host_url=session.host_url,
        method=method,
        path=f"/api/v1/federation/sessions/{session.id}{suffix}",
        token=member_token,
        payload=payload,
    )


def close_local_session(db: Session, session: MultiplayerSessionRecord) -> None:
    if session.mode == "host" and session.status != "closed":
        session.status = "closed"
        _advance(session)
    else:
        with _guest_token_lock:
            _guest_tokens.pop(session.id, None)
        _clear_session_rows(db, session.id)
        db.delete(session)
    db.commit()


def clear_multiplayer_runtime() -> None:
    with _guest_token_lock:
        _guest_tokens.clear()


def tailscale_readiness(companion_port: int) -> dict[str, Any]:
    executable = shutil.which("tailscale")
    dns_name: str | None = None
    if executable:
        try:
            result = subprocess.run(  # noqa: S603 - resolved executable and constant argv
                [executable, "status", "--json"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            payload = json.loads(result.stdout) if result.returncode == 0 else {}
            self_state = payload.get("Self") if isinstance(payload, dict) else None
            candidate = self_state.get("DNSName") if isinstance(self_state, dict) else None
            if isinstance(candidate, str) and candidate:
                dns_name = candidate.rstrip(".")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            dns_name = None
    return {
        "tailscale_installed": executable is not None,
        "tailnet_ready": dns_name is not None,
        "suggested_share_url": f"https://{dns_name}" if dns_name else None,
        "serve_command": (
            "tailscale serve --bg --set-path /api/v1/federation "
            f"http://127.0.0.1:{companion_port}/api/v1/federation"
        ),
        "stores_project_data": False,
    }
