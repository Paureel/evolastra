from __future__ import annotations

import asyncio
import ipaddress
import json
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .access import validate_security_configuration
from .api import public_router, router
from .config import Settings, get_settings
from .database import SessionLocal, init_database
from .event_store import EventStore

settings = get_settings()


class RequestSizeLimitMiddleware:
    def __init__(self, application: ASGIApp, settings_object: Settings):
        self.application = application
        self.settings = settings_object

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.application(scope, receive, send)
            return
        limit = self.settings.max_request_bytes
        messages: list[Message] = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message.get("type") == "http.request":
                total += len(message.get("body", b""))
                if total > limit:
                    response = JSONResponse(
                        status_code=413, content={"detail": "Request exceeds configured limit"}
                    )
                    await response(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            else:
                break
        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return await receive()

        await self.application(scope, replay_receive, send)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    validate_security_configuration(settings)
    init_database()
    Path(settings.artifact_root).resolve().mkdir(parents=True, exist_ok=True)
    drain_task: asyncio.Task[None] | None = None
    if settings.drain_codex_spool:
        from .codex_outbox import drain_outbox_loop

        drain_task = asyncio.create_task(drain_outbox_loop(settings))
    try:
        yield
    finally:
        if drain_task is not None:
            drain_task.cancel()
            try:
                await drain_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Evolastra Observatory API",
    version="0.1.0",
    description="Operational telemetry, semantic analysis graph, and Evolastra spatial projections.",
    debug=False,
    docs_url=None if settings.production else "/docs",
    redoc_url=None if settings.production else "/redoc",
    openapi_url=None if settings.production else "/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_private_network=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Authorization",
        "Content-Type",
        "Last-Event-ID",
        "Traceparent",
        "Tracestate",
    ],
)
app.add_middleware(RequestSizeLimitMiddleware, settings_object=settings)


@app.middleware("http")
async def security_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if settings.production and settings.deployment_profile == "local-private":
        client_host = request.client.host if request.client else ""
        try:
            loopback_client = ipaddress.ip_address(client_host).is_loopback
        except ValueError:
            loopback_client = False
        if not loopback_client:
            return JSONResponse(
                status_code=403,
                content={"detail": "The Evolastra companion accepts loopback clients only"},
            )
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site", "")
        if (origin and origin not in settings.allowed_origins) or (
            not origin and fetch_site == "cross-site"
        ):
            return JSONResponse(
                status_code=403, content={"detail": "Cross-origin state change denied"}
            )
    content_length = request.headers.get("content-length")
    if (
        content_length
        and content_length.isdigit()
        and int(content_length) > settings.max_request_bytes
    ):
        return JSONResponse(status_code=413, content={"detail": "Request exceeds configured limit"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if (
        request.headers.get("access-control-request-private-network") == "true"
        and request.headers.get("origin") in settings.allowed_origins
    ):
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    if settings.serve_web and not request.url.path.startswith(("/api/", "/health/", "/schemas/")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data: blob:; connect-src 'self' http://127.0.0.1:* "
            "http://localhost:*; worker-src 'self' blob:; font-src 'self'; "
            "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    return response


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/service")
def health_service() -> dict[str, object]:
    return {
        "status": "alive",
        "application": "Evolastra",
        "profile": settings.deployment_profile,
        "instance_id": settings.instance_id,
        "pid": os.getpid(),
        "local_data": settings.local_data,
    }


@app.get("/health/ready")
def health_ready() -> dict[str, str]:
    init_database()
    return {"status": "ready"}


@app.get("/health/database")
def health_database() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/health/storage")
def health_storage() -> dict[str, str]:
    root = Path(settings.artifact_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "root": root.name}


@app.get("/health/projection")
def health_projection() -> dict[str, object]:
    with SessionLocal() as session:
        return EventStore(session).integrity()


@app.get("/health/adapters")
def health_adapters() -> dict[str, object]:
    return {
        "status": "ok",
        "core": ["http", "jsonl", "simulator"],
        "optional": ["codex", "openai-agents", "otlp", "openlineage"],
    }


@app.get("/health/telemetry")
def health_telemetry() -> dict[str, object]:
    return {"status": "degraded", "local": True, "external_exporter_configured": False}


app.include_router(public_router)
app.include_router(router)


@app.get("/schemas/events/{schema_name}", include_in_schema=False)
def read_event_schema(schema_name: str) -> JSONResponse:
    if not schema_name.endswith(".json") or any(part in schema_name for part in ("/", "\\", "..")):
        return JSONResponse(status_code=404, content={"detail": "Schema not found"})
    root = (Path(__file__).resolve().parents[3] / "schemas" / "events").resolve()
    path = (root / schema_name).resolve()
    if path.parent != root or not path.is_file():
        return JSONResponse(status_code=404, content={"detail": "Schema not found"})
    return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))


if settings.serve_web and settings.web_root.expanduser().is_dir():
    app.mount("/", StaticFiles(directory=settings.web_root.expanduser(), html=True), name="web")
