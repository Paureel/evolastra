from __future__ import annotations

from copy import deepcopy

import pytest
from asterism_api.db_models import EventRecord, QuarantineRecord
from asterism_api.event_store import EventStore, make_event
from asterism_api.schemas import RunCreate
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def node_event(run_id: str, title: str = "Original node"):
    return make_event(
        run_id=run_id,
        event_type="galaxy.analysis.node.created.v1",
        subject=f"run/{run_id}/node/node-property",
        data={
            "node": {
                "id": "node_00112233445546668899aabbccddeeff",
                "run_id": run_id,
                "node_type": "test",
                "title": title,
                "status": "created",
                "parent_node_id": None,
            }
        },
    )


@pytest.mark.parametrize("duplicate_count", [1, 2, 7, 31])
def test_repeated_delivery_is_idempotent(duplicate_count: int, session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Duplicate property", objective="Repeat the same event", seed=31)
    )
    event = node_event(run.id)
    first = store.ingest(event.model_dump(mode="json"))
    assert first.accepted and not first.duplicate and first.sequence == 2

    for _ in range(duplicate_count):
        duplicate = store.ingest(event.model_dump(mode="json"))
        assert duplicate.accepted and duplicate.duplicate and duplicate.sequence == 2

    session.refresh(run)
    durable_count = session.scalar(
        select(func.count()).select_from(EventRecord).where(EventRecord.run_id == run.id)
    )
    assert durable_count == 2
    assert run.last_sequence == 2
    assert run.state["event_count"] == 2
    projected = run.state["nodes"]["node_00112233445546668899aabbccddeeff"]
    assert projected["title"] == "Original node"


def test_conflicting_duplicate_id_cannot_rewrite_history(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Immutable duplicate", objective="Reject payload replacement", seed=32)
    )
    original = node_event(run.id)
    assert store.ingest(original.model_dump(mode="json")).accepted
    conflict = node_event(run.id, title="Mutated title").model_copy(update={"id": original.id})
    result = store.ingest(conflict.model_dump(mode="json"))

    assert result.accepted and result.duplicate and result.sequence == 2
    session.refresh(run)
    projected = run.state["nodes"]["node_00112233445546668899aabbccddeeff"]
    assert projected["title"] == "Original node"
    stored = session.get(EventRecord, original.id)
    assert stored is not None
    assert stored.envelope["data"]["node"]["title"] == "Original node"


@pytest.mark.parametrize(
    ("submitted", "accepted"),
    [
        ([3, 2, 4, 3], [2, 3]),
        ([5, 4, 3, 2], [2]),
        ([2, 4, 3, 5, 4], [2, 3, 4]),
    ],
)
def test_only_the_next_expected_sequence_is_accepted(
    submitted: list[int], accepted: list[int], session: Session
) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Sequence property", objective="Accept a contiguous prefix", seed=33)
    )

    accepted_sequences: list[int] = []
    for index, supplied_sequence in enumerate(submitted):
        event = make_event(
            run_id=run.id,
            event_type="galaxy.analysis.metric.recorded.v1",
            subject=f"run/{run.id}/metric/{index}",
            data={
                "metric": {
                    "id": f"metr_{index:08x}000040008000000000000000",
                    "run_id": run.id,
                    "value": index,
                }
            },
        ).model_copy(update={"sequence": supplied_sequence})
        result = store.ingest(event.model_dump(mode="json"))
        if result.accepted:
            accepted_sequences.append(supplied_sequence)

    assert accepted_sequences == accepted
    stored_sequences = session.scalars(
        select(EventRecord.sequence)
        .where(EventRecord.run_id == run.id)
        .order_by(EventRecord.sequence)
    ).all()
    assert stored_sequences == list(range(1, len(accepted) + 2))
    rejected_count = session.scalar(select(func.count()).select_from(QuarantineRecord))
    assert rejected_count == len(submitted) - len(accepted)


def test_unknown_entity_version_is_durable_but_projection_safe(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Unknown event", objective="Tolerate future entities", seed=34)
    )
    event = make_event(
        run_id=run.id,
        event_type="galaxy.extension.future_entity.observed.v99",
        subject=f"run/{run.id}/future/future_1",
        data={"future_entity": {"id": "future_1", "payload": "opaque"}},
    )
    result = store.ingest(event.model_dump(mode="json"))

    assert result.accepted and result.sequence == 2
    session.refresh(run)
    assert run.state["unknown_events"] == [event.id]
    assert event.id == session.get(EventRecord, event.id).id  # type: ignore[union-attr]


def test_unknown_version_of_known_entity_does_not_mutate_projection(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Future version", objective="Ignore unknown node schema", seed=35)
    )
    event = make_event(
        run_id=run.id,
        event_type="galaxy.analysis.node.enriched.v99",
        subject=f"run/{run.id}/node/node-future",
        data={
            "node": {
                "id": "node_ffeeddccbbaa49998877665544332211",
                "run_id": run.id,
                "title": "Future semantics",
            }
        },
    )
    assert store.ingest(event.model_dump(mode="json")).accepted
    session.refresh(run)

    assert run.state["nodes"] == {}
    assert run.state["unknown_events"] == [event.id]


def test_event_reduction_does_not_mutate_previous_projection(session: Session) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Copy on write", objective="Preserve historical state", seed=36)
    )
    before = deepcopy(run.state)
    assert store.ingest(node_event(run.id).model_dump(mode="json")).accepted

    assert before["nodes"] == {}
    assert before["last_sequence"] == 1
    assert run.state is not before
