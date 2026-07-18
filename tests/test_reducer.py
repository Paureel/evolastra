from __future__ import annotations

from asterism_api.reducer import initial_state, reduce_event


def test_reducer_projects_entity_and_edge_deterministically() -> None:
    state = initial_state({"id": "run_12345678", "title": "Test", "objective": "Test"})
    event = {
        "id": "evt_12345678",
        "type": "galaxy.analysis.node.created.v1",
        "sequence": 1,
        "data": {
            "node": {"id": "node_12345678", "title": "Branch", "parent_node_id": "node_parent00"}
        },
    }
    first = reduce_event(state, event)
    second = reduce_event(
        initial_state({"id": "run_12345678", "title": "Test", "objective": "Test"}), event
    )
    assert first == second
    assert first["nodes"]["node_12345678"]["schema_version"] == 1
    assert first["edges"]["edge_node_parent00_node_12345678"]["edge_type"] == "contains"


def test_metric_projection_coalesces_without_losing_sequence() -> None:
    state = initial_state({"id": "run_12345678", "title": "Test", "objective": "Test"})
    for sequence in range(1, 701):
        state = reduce_event(
            state,
            {
                "id": f"evt_{sequence:08d}",
                "type": "galaxy.analysis.metric.recorded.v1",
                "sequence": sequence,
                "data": {
                    "metric": {"id": f"metr_{sequence:08d}", "name": "tokens", "value": sequence}
                },
            },
        )
    assert state["last_sequence"] == 700
    assert state["event_count"] == 700
    assert len(state["metrics"]) == 500
    assert state["metrics"][-1]["value"] == 700
