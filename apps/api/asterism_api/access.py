from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def ensure_private_token(path: Path) -> str:
    destination = path.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        token = destination.read_text(encoding="utf-8").strip()
        if len(token) < 32:
            raise RuntimeError("Configured Evolastra token file is invalid")
        return token
    token = secrets.token_urlsafe(48)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.write_text(token, encoding="utf-8")
    os.chmod(temporary, 0o600)
    try:
        temporary.replace(destination)
    except FileExistsError:
        temporary.unlink(missing_ok=True)
    return destination.read_text(encoding="utf-8").strip()


def configured_root_token(settings: Settings | None = None) -> str | None:
    active = settings or get_settings()
    if active.api_token is not None:
        token = active.api_token.get_secret_value().strip()
        return token or None
    if active.deployment_profile == "local-private":
        return ensure_private_token(active.token_file)
    return None


def validate_security_configuration(settings: Settings | None = None) -> None:
    active = settings or get_settings()
    if active.production and active.deployment_profile != "local-private":
        raise RuntimeError("Production Evolastra APIs must use the loopback-only local-private profile")
    root = configured_root_token(active)
    if active.auth_required and root is None:
        raise RuntimeError("The local-private companion requires a private access token")
    if root is not None and len(root) < 32:
        raise RuntimeError("The configured Evolastra access token must contain 32 characters")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SessionGrant:
    origin: str
    expires_at: datetime


class PairingBroker:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._codes: dict[str, datetime] = {}
        self._sessions: dict[str, SessionGrant] = {}

    def create_code(self, ttl_seconds: int) -> tuple[str, datetime]:
        code = "-".join(
            (secrets.token_hex(2).upper(), secrets.token_hex(2).upper(), secrets.token_hex(2).upper())
        )
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        with self._lock:
            self._purge()
            self._codes[_digest(code)] = expires_at
        return code, expires_at

    def exchange(self, code: str, origin: str, ttl_seconds: int) -> tuple[str, datetime] | None:
        normalized = code.strip().upper()
        digest = _digest(normalized)
        now = datetime.now(UTC)
        with self._lock:
            self._purge(now)
            code_expiry = self._codes.pop(digest, None)
            if code_expiry is None or code_expiry <= now:
                return None
            token = secrets.token_urlsafe(48)
            expires_at = now + timedelta(seconds=ttl_seconds)
            self._sessions[_digest(token)] = SessionGrant(origin=origin, expires_at=expires_at)
            return token, expires_at

    def validate(self, token: str, origin: str | None) -> bool:
        now = datetime.now(UTC)
        with self._lock:
            self._purge(now)
            grant = self._sessions.get(_digest(token))
            if grant is None or grant.expires_at <= now:
                return False
            return origin is None or hmac.compare_digest(grant.origin, origin)

    def _purge(self, now: datetime | None = None) -> None:
        current = now or datetime.now(UTC)
        self._codes = {key: expiry for key, expiry in self._codes.items() if expiry > current}
        self._sessions = {
            key: grant for key, grant in self._sessions.items() if grant.expires_at > current
        }


pairing_broker = PairingBroker()


def token_is_authorized(token: str, request: Request, settings: Settings | None = None) -> bool:
    active = settings or get_settings()
    root = configured_root_token(active)
    if root is not None and hmac.compare_digest(token, root):
        return True
    return pairing_broker.validate(token, request.headers.get("origin"))


def require_api_access(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    settings = get_settings()
    if not settings.auth_required:
        return
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not token_is_authorized(credentials.credentials, request, settings)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pair with this Evolastra companion to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )
