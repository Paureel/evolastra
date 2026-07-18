from __future__ import annotations

from copy import deepcopy

from asterism_api.db_models import EventRecord, SnapshotRecord
from asterism_api.event_store import EventStore, make_event
from asterism_api.reducer import initial_state, public_state, reduce_event
from asterism_api.schemas import RunCreate
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


def metric_event(run_id: str, index: int):
    return make_event(
        run_id=run_id,
        event_type="galaxy.analysis.metric.recorded.v1",
        subject=f"run/{run_id}/metric/{index}",
        data={
            "metric": {
                "id": f"metr_{index:08x}000040008000000000000000",
                "run_id": run_id,
                "name": "tokens.total",
                "value": index,
            }
        },
    )


def test_snapshot_restore_matches_independent_full_replay(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Snapshot equivalence", objective="Compare replay paths", seed=17)
    )
    for index in range(1, 50):
        result = store.ingest(metric_event(run.id, index).model_dump(mode="json"))
        assert result.accepted

    session.refresh(run)
    snapshot = session.scalar(
        select(SnapshotRecord)
        .where(SnapshotRecord.run_id == run.id, SnapshotRecord.sequence == 50)
        .limit(1)
    )
    assert snapshot is not None

    ordered = session.scalars(
        select(EventRecord)
        .where(EventRecord.run_id == run.id, EventRecord.sequence <= 50)
        .order_by(EventRecord.sequence)
    ).all()
    replayed = initial_state(
        {
            "id": run.id,
            "title": run.title,
            "objective": run.objective,
            "status": "created",
            "run_seed": run.seed,
            "privacy_classification": run.privacy_class,
        }
    )
    for record in ordered:
        replayed = reduce_event(replayed, record.envelope)

    assert snapshot.state == replayed
    assert store.state_at(run, 50) == public_state(replayed)

    before_rebuild = deepcopy(store.state_at(run))
    after_rebuild = store.rebuild(run)
    assert after_rebuild == before_rebuild
    assert store.integrity() == {"ok": True, "runs_checked": 1, "gaps": []}


def test_projection_integrity_reports_a_durable_sequence_gap(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Integrity gap", objective="Detect missing durable records", seed=18)
    )
    for index in range(1, 4):
        assert store.ingest(metric_event(run.id, index).model_dump(mode="json")).accepted

    session.execute(
        delete(EventRecord).where(EventRecord.run_id == run.id, EventRecord.sequence == 2)
    )
    session.commit()

    report = store.integrity()
    assert report["ok"] is False
    assert report["gaps"] == [
        {
            "run_id": run.id,
            "event_count": 3,
            "max_sequence": 4,
            "projected": 4,
        }
    ]


def test_projection_integrity_reports_embedded_projection_lag(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Projection lag", objective="Detect stale projected state", seed=19)
    )
    assert store.ingest(metric_event(run.id, 1).model_dump(mode="json")).accepted
    session.refresh(run)
    stale_state = deepcopy(run.state)
    stale_state["last_sequence"] = 1
    run.state = stale_state
    session.commit()

    report = store.integrity()
    assert report["ok"] is False
    assert report["gaps"][0]["state_sequence"] == 1
