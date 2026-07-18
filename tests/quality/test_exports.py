from __future__ import annotations

import io
import json
import zipfile
from types import SimpleNamespace

from asterism_api.db_models import EventRecord, RunRecord, SnapshotRecord
from asterism_api.event_store import EventStore, make_event
from asterism_api.exports import (
    cloudevents_jsonl,
    obsidian_zip,
    portable_bundle,
    read_portable_bundle,
    reproduction_zip,
)
from asterism_api.schemas import RunCreate
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_exports_preserve_order_and_never_reintroduce_redacted_content(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Safe export", objective="Verify redaction before export", seed=23)
    )
    event = make_event(
        run_id=run.id,
        event_type="galaxy.analysis.node.created.v1",
        subject=f"run/{run.id}/node/node-safe",
        data={
            "node": {
                "id": "node_00112233445546668899aabbccddeeff",
                "run_id": run.id,
                "node_type": "quality_check",
                "title": "Sanitized node",
                "status": "created",
                "parent_node_id": None,
                "prompt": "private prompt",
                "authorization": "Bearer abcdefghijklmnop",
                "note": "sk-abcdefghijklmnop",
            }
        },
    )
    assert store.ingest(event.model_dump(mode="json")).accepted
    session.refresh(run)
    records = session.scalars(
        select(EventRecord).where(EventRecord.run_id == run.id).order_by(EventRecord.sequence)
    ).all()

    jsonl = cloudevents_jsonl(records).decode("utf-8")
    exported = [json.loads(line) for line in jsonl.splitlines()]
    assert [item["sequence"] for item in exported] == list(range(1, len(exported) + 1))
    assert "private prompt" not in jsonl
    assert "abcdefghijklmnop" not in jsonl
    assert "[CONTENT_CAPTURE_DISABLED]" in jsonl
    assert "[REDACTED]" in jsonl

    bundle = reproduction_zip(run, records)
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert set(archive.namelist()) == {
            "README.md",
            "environment.json",
            "events.jsonl",
            "run.json",
        }
        bundled_events = archive.read("events.jsonl").decode("utf-8")
        assert bundled_events == jsonl
        assert "private prompt" not in bundled_events
        assert "abcdefghijklmnop" not in bundled_events

    portable = portable_bundle(run, records)
    manifest, portable_events = read_portable_bundle(portable, max_bytes=5 * 1024 * 1024)
    assert manifest["run_id"] == run.id
    assert manifest["event_count"] == len(records)
    assert all("sequence" not in json.loads(line) for line in portable_events.splitlines())


def test_obsidian_export_member_paths_are_unique_after_sanitization() -> None:
    run = SimpleNamespace(
        id="run_33bd8a5551544233bfc31c327b2398e6",
        title="Collision fixture",
        objective="Ensure every exported object has a unique path",
        status="completed",
        state={
            "findings": {
                "find_00112233445546668899aabbccddeeff": {
                    "id": "find_00112233445546668899aabbccddeeff",
                    "title": "Same/title",
                    "summary": "First",
                    "status": "promoted",
                },
                "find_ffeeddccbbaa49998877665544332211": {
                    "id": "find_ffeeddccbbaa49998877665544332211",
                    "title": "Same?title",
                    "summary": "Second",
                    "status": "promoted",
                },
            },
            "claims": {},
        },
    )

    with zipfile.ZipFile(io.BytesIO(obsidian_zip(run))) as archive:
        members = archive.namelist()
    assert len(members) == len(set(members))


def test_portable_round_trip_regenerates_projection_snapshots(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Long portable run", objective="Cross the snapshot boundary", seed=31)
    )
    for index in range(55):
        result = store.ingest(
            make_event(
                run_id=run.id,
                event_type="galaxy.telemetry.metric.recorded.v1",
                subject=f"run/{run.id}/metric/{index}",
                data={"metric": index},
            ).model_dump(mode="json")
        )
        assert result.accepted
    records = session.scalars(
        select(EventRecord).where(EventRecord.run_id == run.id).order_by(EventRecord.sequence)
    ).all()
    assert any(record.type == "galaxy.analysis.snapshot.created.v1" for record in records)
    bundle = portable_bundle(run, records)
    manifest, event_body = read_portable_bundle(bundle, max_bytes=5 * 1024 * 1024)
    assert manifest["event_count"] == 56

    session.query(EventRecord).filter(EventRecord.run_id == run.id).delete()
    session.query(SnapshotRecord).filter(SnapshotRecord.run_id == run.id).delete()
    session.delete(run)
    session.commit()
    restored_store = EventStore(session)
    for line in event_body.splitlines():
        result = restored_store.ingest(json.loads(line))
        assert result.accepted, result.reason
    restored = session.get(RunRecord, manifest["run_id"])
    assert restored is not None
    assert restored.title == "Long portable run"
    assert restored.last_sequence == len(records)
