"""Loss-aware OpenLineage RunEvent ingestion and subset export mappings."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from .core import build_event, entity_payload, stable_prefixed_id

_STATE_TO_EVENT = {
    "START": "galaxy.analysis.run.started.v1",
    "RUNNING": "galaxy.analysis.run.updated.v1",
    "COMPLETE": "galaxy.analysis.run.completed.v1",
    "ABORT": "galaxy.analysis.run.failed.v1",
    "FAIL": "galaxy.analysis.run.failed.v1",
    "OTHER": "galaxy.analysis.run.updated.v1",
}


def ingest_run_event(
    event: Mapping[str, Any], *, capture_content: bool = False
) -> list[dict[str, Any]]:
    """Map one OpenLineage RunEvent plus its dataset identities.

    Rich facets are retained under ``data.openlineage`` after redaction. The
    adapter does not pretend every OpenLineage Job is a semantic analysis node.
    """

    run = event.get("run")
    job = event.get("job")
    if not isinstance(run, Mapping) or not isinstance(job, Mapping):
        raise ValueError("OpenLineage RunEvent requires run and job objects")
    native_run_id = str(run.get("runId") or "")
    namespace = str(job.get("namespace") or "")
    job_name = str(job.get("name") or "")
    if not native_run_id or not namespace or not job_name:
        raise ValueError("OpenLineage run.runId and job namespace/name are required")
    state = str(event.get("eventType") or "OTHER").upper()
    run_event_type = _STATE_TO_EVENT.get(state, "galaxy.analysis.run.updated.v1")
    run_id = stable_prefixed_id("run", "openlineage-run", native_run_id)
    native_id = json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
    result = [
        build_event(
            event_type=run_event_type,
            source="urn:asterism:integration:openlineage",
            subject=run_id,
            run_id=run_id,
            adapter="openlineage/0.1.0",
            native_id=native_id,
            correlation_id=native_run_id,
            event_time=str(event.get("eventTime") or "") or None,
            capture_content=capture_content,
            data={
                **entity_payload(
                    "run",
                    entity_id=run_id,
                    run_id=run_id,
                    status=run_event_type.split(".")[3],
                ),
                "openlineage": dict(event),
                "job": {"namespace": namespace, "name": job_name},
                "run_state": state,
            },
        )
    ]
    for direction in ("inputs", "outputs"):
        datasets = event.get(direction, [])
        if not isinstance(datasets, list):
            continue
        for dataset in datasets:
            if not isinstance(dataset, Mapping):
                continue
            dataset_namespace = str(dataset.get("namespace") or "")
            dataset_name = str(dataset.get("name") or "")
            if not dataset_namespace or not dataset_name:
                continue
            dataset_id = stable_prefixed_id(
                "dataset", "openlineage-dataset", f"{dataset_namespace}:{dataset_name}"
            )
            result.append(
                build_event(
                    event_type="galaxy.data.dataset.registered.v1",
                    source="urn:asterism:integration:openlineage",
                    subject=dataset_id,
                    run_id=run_id,
                    adapter="openlineage/0.1.0",
                    native_id=f"{native_run_id}:{direction}:{dataset_namespace}:{dataset_name}",
                    correlation_id=native_run_id,
                    event_time=str(event.get("eventTime") or "") or None,
                    capture_content=capture_content,
                    data={
                        **entity_payload(
                            "dataset",
                            entity_id=dataset_id,
                            run_id=run_id,
                            namespace=dataset_namespace,
                            name=dataset_name,
                            direction="input" if direction == "inputs" else "output",
                            openlineage_facets=dataset.get("facets", {}),
                        ),
                        "job": {"namespace": namespace, "name": job_name},
                    },
                )
            )
    return result


def export_run_event(
    events: Iterable[Mapping[str, Any]],
    *,
    producer: str,
    schema_url: str,
    job_namespace: str,
    job_name: str,
    native_run_id: str,
) -> dict[str, Any]:
    """Export the compatible run/dataset subset; caller pins the OL schema."""

    event_list = list(events)
    terminal = next(
        (
            e
            for e in reversed(event_list)
            if e.get("type")
            in {"galaxy.analysis.run.completed.v1", "galaxy.analysis.run.failed.v1"}
        ),
        None,
    )
    event_type = "OTHER"
    if terminal:
        event_type = "FAIL" if str(terminal.get("type", "")).endswith("failed.v1") else "COMPLETE"
    elif any(e.get("type") == "galaxy.analysis.run.started.v1" for e in event_list):
        event_type = "START"
    event_time = (
        str(terminal.get("time"))
        if terminal
        else datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    inputs: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for event in event_list:
        if event.get("type") != "galaxy.data.dataset.registered.v1":
            continue
        data = event.get("data")
        if not isinstance(data, Mapping):
            continue
        dataset = data.get("dataset")
        if not isinstance(dataset, Mapping):
            continue
        namespace = str(dataset.get("namespace") or "")
        name = str(dataset.get("name") or "")
        direction = str(dataset.get("direction") or "input")
        if not namespace or not name or (direction, namespace, name) in seen:
            continue
        seen.add((direction, namespace, name))
        target = outputs if direction == "output" else inputs
        target.append({"namespace": namespace, "name": name, "facets": {}})
    return {
        "eventTime": event_time,
        "eventType": event_type,
        "run": {"runId": native_run_id, "facets": {}},
        "job": {"namespace": job_namespace, "name": job_name, "facets": {}},
        "inputs": inputs,
        "outputs": outputs,
        "producer": producer,
        "schemaURL": schema_url,
    }
