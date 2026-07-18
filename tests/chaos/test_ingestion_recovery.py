from __future__ import annotations

from copy import deepcopy

from asterism_api import api as api_module
from asterism_api.db_models import EventRecord, QuarantineRecord
from asterism_api.event_store import EventStore, make_event
from asterism_api.schemas import EventBatch, RunCreate
from sqlalchemy import func, select
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


def test_mixed_batch_quarantines_bad_item_and_keeps_contiguous_progress(
    session: Session,
) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Mixed batch", objective="Isolate a malformed event", seed=41)
    )
    first = metric_event(run.id, 1).model_dump(mode="json")
    malformed = deepcopy(metric_event(run.id, 2).model_dump(mode="json"))
    malformed.pop("traceid")
    third = metric_event(run.id, 3).model_copy(update={"sequence": 3}).model_dump(mode="json")

    report = api_module.ingest_batch(
        EventBatch(events=[first, malformed, third]),
        session,
    )

    assert report["accepted"] == 2
    assert report["quarantined"] == 1
    assert [item["accepted"] for item in report["results"]] == [True, False, True]
    stored_sequences = session.scalars(
        select(EventRecord.sequence)
        .where(EventRecord.run_id == run.id)
        .order_by(EventRecord.sequence)
    ).all()
    assert stored_sequences == [1, 2, 3]
    session.refresh(run)
    assert run.last_sequence == 3
    assert store.integrity()["ok"] is True


def test_metric_flood_keeps_durable_fidelity_with_bounded_projection(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Metric flood", objective="Coalesce only the projection", seed=42)
    )
    samples = 510
    for index in range(1, samples + 1):
        assert store.ingest(metric_event(run.id, index).model_dump(mode="json")).accepted

    durable_metrics = session.scalar(
        select(func.count())
        .select_from(EventRecord)
        .where(
            EventRecord.run_id == run.id,
            EventRecord.type == "galaxy.analysis.metric.recorded.v1",
        )
    )
    session.refresh(run)
    assert durable_metrics == samples
    assert len(run.state["metrics"]) == 500
    assert run.state["metrics"][-1]["value"] == samples
    assert run.state["last_sequence"] == run.last_sequence
    assert store.integrity()["ok"] is True


def test_failed_quarantine_retry_preserves_attempt_history(session: Session) -> None:
    store = EventStore(session)
    first = store.ingest({"not": "a CloudEvent"})
    assert first.quarantine_id is not None
    original = session.get(QuarantineRecord, first.quarantine_id)
    assert original is not None

    retried = api_module.retry_quarantine(first.quarantine_id, session)

    preserved = session.get(QuarantineRecord, first.quarantine_id)
    assert retried["accepted"] is False
    assert preserved is not None
    assert preserved.retry_count == 1
