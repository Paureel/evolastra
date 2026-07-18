from __future__ import annotations

from asterism_api.database import SessionLocal, init_database
from asterism_api.event_store import EventStore, make_event
from asterism_api.schemas import RunCreate


def setup_function() -> None:
    init_database()
    with SessionLocal() as session:
        EventStore(session).reset()


def test_event_ingestion_is_idempotent_and_sequenced() -> None:
    with SessionLocal() as session:
        store = EventStore(session)
        run, _ = store.create_run(RunCreate(title="A durable run", objective="Verify idempotency"))
        event = make_event(
            run_id=run.id,
            event_type="galaxy.analysis.node.created.v1",
            subject=f"run/{run.id}/node/node_00112233445546668899aabbccddeeff",
            data={
                "node": {
                    "id": "node_00112233445546668899aabbccddeeff",
                    "run_id": run.id,
                    "title": "A branch",
                    "node_type": "test",
                    "parent_node_id": None,
                }
            },
        )
        first = store.ingest(event.model_dump(mode="json"))
        second = store.ingest(event.model_dump(mode="json"))
        assert first.accepted and first.sequence == 2
        assert second.accepted and second.duplicate and second.sequence == 2
        session.refresh(run)
        assert run.last_sequence == 2
        assert run.state["nodes"]["node_00112233445546668899aabbccddeeff"]["title"] == "A branch"


def test_ingestion_refreshes_a_run_loaded_before_another_session_commits() -> None:
    with SessionLocal() as creating_session:
        run, _ = EventStore(creating_session).create_run(
            RunCreate(title="Concurrent run", objective="Serialize independent writers")
        )
        run_id = run.id

    with SessionLocal() as stale_session, SessionLocal() as fresh_session:
        stale_run = stale_session.get(type(run), run_id)
        assert stale_run is not None and stale_run.last_sequence == 1
        first_metric_id = "metr_11111111111141118111111111111111"
        second_metric_id = "metr_2222222222224222a222222222222222"

        first = EventStore(fresh_session).ingest(
            make_event(
                run_id=run_id,
                event_type="galaxy.analysis.metric.recorded.v1",
                subject=f"run/{run_id}/metric/{first_metric_id}",
                data={
                    "metric": {
                        "id": first_metric_id,
                        "run_id": run_id,
                        "name": "writers",
                        "value": 1,
                    }
                },
            ).model_dump(mode="json")
        )
        second = EventStore(stale_session).ingest(
            make_event(
                run_id=run_id,
                event_type="galaxy.analysis.metric.recorded.v1",
                subject=f"run/{run_id}/metric/{second_metric_id}",
                data={
                    "metric": {
                        "id": second_metric_id,
                        "run_id": run_id,
                        "name": "writers",
                        "value": 2,
                    }
                },
            ).model_dump(mode="json")
        )

        assert first.accepted and first.sequence == 2
        assert second.accepted and second.sequence == 3
        assert second.quarantine_id is None


def test_out_of_order_event_is_quarantined() -> None:
    with SessionLocal() as session:
        store = EventStore(session)
        run, _ = store.create_run(RunCreate(title="Ordered run", objective="Reject a gap"))
        event = make_event(
            run_id=run.id,
            event_type="galaxy.analysis.metric.recorded.v1",
            subject=f"run/{run.id}/metric/metr_00112233445546668899aabbccddeeff",
            data={
                "metric": {
                    "id": "metr_00112233445546668899aabbccddeeff",
                    "run_id": run.id,
                    "name": "tokens",
                    "value": 2,
                }
            },
        ).model_copy(update={"sequence": 4})
        result = store.ingest(event.model_dump(mode="json"))
        assert not result.accepted
        assert result.quarantine_id
        assert "expected 2" in (result.reason or "")


def test_compact_toolcall_event_projects_to_canonical_tool_call() -> None:
    with SessionLocal() as session:
        store = EventStore(session)
        run, _ = store.create_run(RunCreate(title="Codex run", objective="Project tool hooks"))
        tool_id = "tool_00112233445546668899aabbccddeeff"
        result = store.ingest(
            make_event(
                run_id=run.id,
                event_type="galaxy.analysis.toolcall.completed.v1",
                subject=f"run/{run.id}/tool/{tool_id}",
                data={
                    "tool_call": {
                        "id": tool_id,
                        "run_id": run.id,
                        "tool_name": "Bash",
                    }
                },
            ).model_dump(mode="json")
        )

        assert result.accepted
        session.refresh(run)
        assert run.state["tool_calls"][tool_id]["status"] == "completed"
        assert run.state["unknown_events"] == []


def test_projection_rebuild_is_equivalent() -> None:
    with SessionLocal() as session:
        store = EventStore(session)
        run, _ = store.create_run(RunCreate(title="Replay run", objective="Rebuild equivalently"))
        for index in range(3):
            store.ingest(
                make_event(
                    run_id=run.id,
                    event_type="galaxy.analysis.metric.recorded.v1",
                    subject=f"run/{run.id}/metric/{index}",
                    data={
                        "metric": {
                            "id": f"metr_{index:08d}",
                            "run_id": run.id,
                            "name": "tokens",
                            "value": index,
                        }
                    },
                ).model_dump(mode="json")
            )
        session.refresh(run)
        before = store.state_at(run)
        after = store.rebuild(run)
        assert after == before
