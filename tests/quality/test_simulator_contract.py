from __future__ import annotations

from collections import Counter

from asterism_api.schemas import EVENT_TYPE_PATTERN, ID_PATTERN
from asterism_api.simulator import BRANCHES, DEMO_SEED, build_demo_events

RUN_ID = "run_33bd8a5551544233bfc31c327b2398e6"


def test_demo_has_required_semantic_counts_and_lifecycle_events() -> None:
    events = build_demo_events(RUN_ID, DEMO_SEED)
    types = Counter(event.type for event in events)

    assert len(BRANCHES) == 8
    assert len(events) == 213
    assert types["galaxy.analysis.node.proposed.v1"] == 2
    assert types["galaxy.analysis.node.created.v1"] == 9
    assert types["galaxy.analysis.agent.created.v1"] == 9
    assert types["galaxy.analysis.tool_call.requested.v1"] == 32
    assert types["galaxy.analysis.tool_call.completed.v1"] == 32
    assert types["galaxy.analysis.tool_call.failed.v1"] == 1
    assert types["galaxy.analysis.artifact.created.v1"] == 8
    assert types["galaxy.analysis.claim.created.v1"] == 8
    assert types["galaxy.analysis.claim.validated.v1"] == 6
    assert types["galaxy.analysis.claim.disputed.v1"] == 2
    assert types["galaxy.analysis.finding.promoted.v1"] == 8
    assert types["galaxy.analysis.anomaly.created.v1"] == 2
    assert types["galaxy.analysis.anomaly.resolved.v1"] == 1
    assert types["galaxy.analysis.approval.requested.v1"] == 1
    assert types["galaxy.analysis.metric.recorded.v1"] == 6


def test_demo_events_satisfy_required_envelope_and_entity_identity_contract() -> None:
    events = build_demo_events(RUN_ID, DEMO_SEED)

    for event in events:
        assert event.runid == RUN_ID
        assert event.sequence is None
        assert ID_PATTERN.fullmatch(event.id)
        assert EVENT_TYPE_PATTERN.fullmatch(event.type)
        assert event.traceid != "0" * 32
        assert event.spanid != "0" * 16
        assert event.correlationid
        assert event.causationid
        assert event.producerversion
        assert event.privacyclass == "internal"
        assert event.dataschema.startswith("/schemas/events/")
        for entity in event.data.values():
            if isinstance(entity, dict) and "id" in entity:
                assert entity["schema_version"] == 1


def test_demo_generation_is_identical_for_a_fixed_run_and_seed() -> None:
    first = [event.model_dump(mode="json") for event in build_demo_events(RUN_ID, DEMO_SEED)]
    second = [event.model_dump(mode="json") for event in build_demo_events(RUN_ID, DEMO_SEED)]

    assert second == first


def test_demo_event_ids_are_disjoint_across_runs() -> None:
    other_run_id = "run_769420023b78427ea58b6b515ae37793"
    first_ids = {event.id for event in build_demo_events(RUN_ID, DEMO_SEED)}
    second_ids = {event.id for event in build_demo_events(other_run_id, DEMO_SEED)}

    assert first_ids.isdisjoint(second_ids)
