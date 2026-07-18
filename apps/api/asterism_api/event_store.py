from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .db_models import AuditRecord, EventRecord, QuarantineRecord, RunRecord, SnapshotRecord
from .ids import new_id
from .reducer import SUPPORTED_ACTIONS, initial_state, public_state, reduce_event
from .schemas import ID_PATTERN, CloudEvent, IngestResult, RunCreate
from .security import redact

_ingest_lock = threading.RLock()


def utcnow() -> datetime:
    return datetime.now(UTC)


class EventStore:
    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()

    def create_run(self, payload: RunCreate) -> tuple[RunRecord, dict[str, Any]]:
        from random import SystemRandom

        now = utcnow()
        run_id = new_id("run")
        seed = payload.seed if payload.seed is not None else SystemRandom().randint(1, 2**31 - 1)
        run_data: dict[str, Any] = {
            "id": run_id,
            "schema_version": 1,
            "title": payload.title,
            "objective": payload.objective,
            "description": "",
            "status": "created",
            "created_time": now.isoformat(),
            "start_time": None,
            "completion_time": None,
            "update_time": now.isoformat(),
            "root_node_id": None,
            "trace_ids": [],
            "trace_group_id": None,
            "source_adapters": ["api"],
            "tags": payload.tags,
            "run_seed": seed,
            "privacy_classification": payload.privacy_class,
            "retention_policy": "local-default",
            "token_metrics": {"input": 0, "output": 0, "total": 0},
            "cost_metrics": {"currency": "USD", "total": 0.0},
            "timing_metrics": {"runtime_ms": 0},
            "final_claim_ids": [],
            "final_finding_ids": [],
            "final_artifact_ids": [],
            "reproduction_bundle_id": None,
            "summary": "",
            "error_summary": None,
            "archive_state": "active",
        }
        state = initial_state(run_data)
        record = RunRecord(
            id=run_id,
            title=payload.title,
            objective=payload.objective,
            status="created",
            seed=seed,
            privacy_class=payload.privacy_class,
            source_adapters=["api"],
            state=state,
            last_sequence=0,
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        self.session.flush()
        event = make_event(
            run_id=run_id,
            event_type="galaxy.analysis.run.created.v1",
            subject=f"run/{run_id}",
            data={"run": run_data},
            source="urn:galaxy:api",
            privacy_class=payload.privacy_class,
        )
        result = self._ingest_validated(event)
        if not result.accepted:
            raise RuntimeError(result.reason or "failed to create run event")
        self.session.commit()
        self.session.refresh(record)
        return record, event.model_copy(update={"sequence": result.sequence}).model_dump(
            mode="json"
        )

    def ingest(self, raw: dict[str, Any]) -> IngestResult:
        safe_raw = redact(raw, capture_content=self.settings.capture_content)
        try:
            event = CloudEvent.model_validate(safe_raw)
        except ValidationError as exc:
            return self.quarantine(
                safe_raw, f"schema validation failed: {exc.errors(include_url=False)}"
            )
        with _ingest_lock:
            try:
                result = self._ingest_validated(event)
                self.session.commit()
                return result
            except IntegrityError:
                self.session.rollback()
                duplicate = self.session.get(EventRecord, event.id)
                if duplicate:
                    return IngestResult(
                        accepted=True,
                        duplicate=True,
                        event_id=duplicate.id,
                        run_id=duplicate.run_id,
                        sequence=duplicate.sequence,
                    )
                return self.quarantine(safe_raw, "sequence conflict during concurrent ingestion")

    def _ingest_validated(self, event: CloudEvent) -> IngestResult:
        duplicate = self.session.get(EventRecord, event.id)
        if duplicate:
            return IngestResult(
                accepted=True,
                duplicate=True,
                event_id=duplicate.id,
                run_id=duplicate.run_id,
                sequence=duplicate.sequence,
            )
        payload_problem = self._validate_registered_payload(event)
        if payload_problem:
            return self.quarantine(event.model_dump(mode="json"), payload_problem)
        run = self.session.get(RunRecord, event.runid)
        if run is None:
            if event.type != "galaxy.analysis.run.created.v1":
                return self.quarantine(event.model_dump(mode="json"), "run does not exist")
            run_data = event.data.get("run", event.data)
            now = utcnow()
            run = RunRecord(
                id=event.runid,
                title=str(run_data.get("title", "Imported analysis"))[:300],
                objective=str(run_data.get("objective", "Imported analysis run"))[:5_000],
                status="created",
                seed=int(run_data.get("run_seed", 1)),
                privacy_class=event.privacyclass,
                source_adapters=[event.source],
                state=initial_state(dict(run_data)),
                last_sequence=0,
                created_at=now,
                updated_at=now,
            )
            self.session.add(run)
            self.session.flush()

        expected = run.last_sequence + 1
        if event.sequence is not None and event.sequence != expected:
            return self.quarantine(
                event.model_dump(mode="json"),
                f"out-of-order sequence: expected {expected}, received {event.sequence}",
            )
        sequence = expected
        stored = event.model_copy(update={"sequence": sequence})
        envelope = stored.model_dump(mode="json")
        now = utcnow()
        self.session.add(
            EventRecord(
                id=stored.id,
                run_id=stored.runid,
                sequence=sequence,
                type=stored.type,
                source=stored.source,
                subject=stored.subject,
                event_time=stored.time,
                ingested_at=now,
                trace_id=stored.traceid,
                span_id=stored.spanid,
                correlation_id=stored.correlationid,
                causation_id=stored.causationid,
                privacy_class=stored.privacyclass,
                envelope=envelope,
            )
        )
        run.state = reduce_event(run.state, envelope)
        projected_run = run.state.get("run", {})
        run.title = str(projected_run.get("title", run.title))[:300]
        run.objective = str(projected_run.get("objective", run.objective))[:5_000]
        run.status = str(projected_run.get("status", run.status))[:40]
        run.last_sequence = sequence
        run.updated_at = now
        should_snapshot = (
            sequence % 50 == 0 or stored.type.endswith("run.completed.v1")
        ) and stored.type != "galaxy.analysis.snapshot.created.v1"
        if should_snapshot:
            snapshot_id = new_id("snap")
            self.session.add(
                SnapshotRecord(
                    id=snapshot_id,
                    run_id=run.id,
                    sequence=sequence,
                    state=run.state,
                    created_at=now,
                )
            )
            snapshot_event = make_event(
                run_id=run.id,
                event_type="galaxy.analysis.snapshot.created.v1",
                subject=f"run/{run.id}/snapshot/{snapshot_id}",
                data={
                    "snapshot": {
                        "id": snapshot_id,
                        "run_id": run.id,
                        "base_sequence": sequence,
                    }
                },
                source="urn:galaxy:projection",
                causation_id=stored.id,
            )
            self._ingest_validated(snapshot_event)
        self.session.flush()
        return IngestResult(
            accepted=True,
            event_id=stored.id,
            run_id=stored.runid,
            sequence=sequence,
        )

    @staticmethod
    def _validate_registered_payload(event: CloudEvent) -> str | None:
        parts = event.type.split(".")
        if len(parts) != 5 or parts[1] != "analysis":
            return None
        entity, action, version = parts[2], parts[3], parts[4]
        if version != "v1" or action not in SUPPORTED_ACTIONS.get(entity, frozenset()):
            return None
        payload = event.data.get(entity)
        if not isinstance(payload, dict):
            return f"registered {entity}.{action} event requires data.{entity}"
        entity_id = payload.get("id")
        if not isinstance(entity_id, str) or not ID_PATTERN.fullmatch(entity_id):
            return f"data.{entity}.id must be a prefixed UUIDv4"
        if int(payload.get("schema_version", 0)) != 1:
            return f"data.{entity}.schema_version must equal 1"
        if entity == "run":
            if entity_id != event.runid:
                return "data.run.id must match runid"
            if action == "created" and (
                not payload.get("title") or not payload.get("objective")
            ):
                return "run.created requires title and objective"
        else:
            if payload.get("run_id") != event.runid:
                return f"data.{entity}.run_id must match runid"
        if entity == "node" and action == "created" and (
            not payload.get("title") or not payload.get("node_type")
        ):
            return "node.created requires title and node_type"
        if entity == "artifact" and action == "created" and (
            not payload.get("title")
            or not payload.get("artifact_type")
            or not payload.get("mime_type")
        ):
            return "artifact.created requires title, artifact_type, and mime_type"
        return None

    def quarantine(self, payload: dict[str, Any], reason: str) -> IngestResult:
        quarantine_id = new_id("quar")
        run_id = payload.get("runid") if isinstance(payload.get("runid"), str) else None
        self.session.add(
            QuarantineRecord(
                id=quarantine_id,
                run_id=run_id,
                reason=reason[:4_000],
                payload=redact(payload, capture_content=self.settings.capture_content),
                received_at=utcnow(),
            )
        )
        self.session.commit()
        return IngestResult(
            accepted=False,
            run_id=run_id,
            quarantine_id=quarantine_id,
            reason=reason[:500],
        )

    def state_at(self, run: RunRecord, sequence: int | None = None) -> dict[str, Any]:
        if sequence is None or sequence >= run.last_sequence:
            return public_state(run.state)
        snapshot = self.session.scalar(
            select(SnapshotRecord)
            .where(SnapshotRecord.run_id == run.id, SnapshotRecord.sequence <= sequence)
            .order_by(SnapshotRecord.sequence.desc())
            .limit(1)
        )
        if snapshot:
            state = snapshot.state
            after = snapshot.sequence
        else:
            state = initial_state(
                {
                    "id": run.id,
                    "title": run.title,
                    "objective": run.objective,
                    "status": "created",
                    "run_seed": run.seed,
                    "privacy_classification": run.privacy_class,
                }
            )
            after = 0
        events = self.session.scalars(
            select(EventRecord)
            .where(
                EventRecord.run_id == run.id,
                EventRecord.sequence > after,
                EventRecord.sequence <= sequence,
            )
            .order_by(EventRecord.sequence)
        ).all()
        for record in events:
            state = reduce_event(state, record.envelope)
        return public_state(state)

    def rebuild(self, run: RunRecord) -> dict[str, Any]:
        events = self.session.scalars(
            select(EventRecord).where(EventRecord.run_id == run.id).order_by(EventRecord.sequence)
        ).all()
        base = initial_state(
            {
                "id": run.id,
                "title": run.title,
                "objective": run.objective,
                "status": "created",
                "run_seed": run.seed,
                "privacy_classification": run.privacy_class,
            }
        )
        for record in events:
            base = reduce_event(base, record.envelope)
        run.state = base
        run.last_sequence = events[-1].sequence if events else 0
        run.updated_at = utcnow()
        self.session.commit()
        return public_state(base)

    def audit(self, action: str, target: str, details: dict[str, Any] | None = None) -> None:
        self.session.add(
            AuditRecord(
                id=new_id("audit"),
                action=action,
                target=target,
                occurred_at=utcnow(),
                details=redact(details or {}, capture_content=False),
            )
        )

    def reset(self) -> None:
        for model in (EventRecord, SnapshotRecord, QuarantineRecord, AuditRecord, RunRecord):
            self.session.execute(delete(model))
        self.session.commit()

    def integrity(self) -> dict[str, Any]:
        runs = self.session.scalars(select(RunRecord)).all()
        gaps: list[dict[str, Any]] = []
        for run in runs:
            count = self.session.scalar(
                select(func.count()).select_from(EventRecord).where(EventRecord.run_id == run.id)
            )
            maximum = (
                self.session.scalar(
                    select(func.max(EventRecord.sequence)).where(EventRecord.run_id == run.id)
                )
                or 0
            )
            state_sequence = int(run.state.get("last_sequence", 0))
            if (
                count != maximum
                or maximum != run.last_sequence
                or state_sequence != run.last_sequence
            ):
                gap = {
                    "run_id": run.id,
                    "event_count": count,
                    "max_sequence": maximum,
                    "projected": run.last_sequence,
                }
                if state_sequence != run.last_sequence:
                    gap["state_sequence"] = state_sequence
                gaps.append(gap)
        return {"ok": not gaps, "runs_checked": len(runs), "gaps": gaps}


def make_event(
    *,
    run_id: str,
    event_type: str,
    subject: str,
    data: dict[str, Any],
    source: str = "urn:galaxy:simulator",
    privacy_class: str = "internal",
    trace_id: str | None = None,
    span_id: str | None = None,
    causation_id: str | None = None,
    event_id: str | None = None,
    event_time: datetime | None = None,
) -> CloudEvent:
    enriched_data = json.loads(json.dumps(data))
    for value in enriched_data.values():
        if isinstance(value, dict) and "id" in value:
            value.setdefault("schema_version", 1)
    effective_trace = trace_id or uuid.uuid4().hex
    effective_span = span_id or uuid.uuid4().hex[:16]
    effective_causation = causation_id or run_id
    return CloudEvent(
        id=event_id or new_id("evt"),
        source=source,
        type=event_type,
        subject=subject,
        runid=run_id,
        time=event_time or utcnow(),
        traceid=effective_trace,
        spanid=effective_span,
        correlationid=run_id,
        causationid=effective_causation,
        privacyclass=privacy_class,  # type: ignore[arg-type]
        data=enriched_data,
    )


def event_json(record: EventRecord) -> str:
    return json.dumps(record.envelope, separators=(",", ":"), ensure_ascii=False)
