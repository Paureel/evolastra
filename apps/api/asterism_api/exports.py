from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from .db_models import EventRecord, RunRecord

SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")
PORTABLE_FORMAT = "evolastra.analysis"
PORTABLE_VERSION = 1


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8")


def cloudevents_jsonl(events: Iterable[EventRecord]) -> bytes:
    return (
        "\n".join(json.dumps(event.envelope, ensure_ascii=False) for event in events) + "\n"
    ).encode("utf-8")


def portable_events_jsonl(events: Iterable[EventRecord]) -> tuple[bytes, int]:
    """Serialize source events so a fresh store can assign its own projection sequences."""

    envelopes: list[dict[str, Any]] = []
    for event in events:
        if event.type == "galaxy.analysis.snapshot.created.v1":
            continue
        envelope = dict(event.envelope)
        envelope.pop("sequence", None)
        envelopes.append(envelope)
    body = ("\n".join(json.dumps(item, ensure_ascii=False) for item in envelopes) + "\n").encode(
        "utf-8"
    )
    return body, len(envelopes)


def portable_bundle(run: RunRecord, events: Iterable[EventRecord]) -> bytes:
    event_body, event_count = portable_events_jsonl(events)
    manifest = {
        "format": PORTABLE_FORMAT,
        "version": PORTABLE_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "run_id": run.id,
        "title": run.title,
        "event_count": event_count,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json_bytes(manifest))
        archive.writestr("events.jsonl", event_body)
    return buffer.getvalue()


def read_portable_bundle(body: bytes, *, max_bytes: int) -> tuple[dict[str, Any], bytes]:
    """Read a bounded, non-executable portable bundle without extracting files."""

    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if sorted(names) != ["events.jsonl", "manifest.json"]:
                raise ValueError("Portable bundle must contain only manifest.json and events.jsonl")
            if len(set(names)) != len(names):
                raise ValueError("Portable bundle contains duplicate members")
            if any(item.flag_bits & 0x1 for item in infos):
                raise ValueError("Encrypted portable bundles are not supported")
            if any(item.file_size > max_bytes for item in infos):
                raise ValueError("Portable bundle expands beyond the configured limit")

            def bounded_read(name: str, limit: int) -> bytes:
                with archive.open(name, "r") as member:
                    value = member.read(limit + 1)
                if len(value) > limit:
                    raise ValueError(f"{name} exceeds the configured limit")
                return value

            manifest_body = bounded_read("manifest.json", min(max_bytes, 64 * 1024))
            events_body = bounded_read("events.jsonl", max_bytes)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("File is not a valid Evolastra analysis") from exc

    try:
        manifest = json.loads(manifest_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Portable bundle manifest is invalid") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Portable bundle manifest must be an object")
    if manifest.get("format") != PORTABLE_FORMAT or manifest.get("version") != PORTABLE_VERSION:
        raise ValueError("Portable bundle format or version is unsupported")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("Portable bundle is missing its run identifier")
    event_count = manifest.get("event_count")
    if not isinstance(event_count, int) or isinstance(event_count, bool):
        raise ValueError("Portable bundle event count is invalid")
    if event_count != sum(
        1 for line in events_body.splitlines() if line.strip()
    ):
        raise ValueError("Portable bundle event count does not match its manifest")
    return manifest, events_body


def openlineage_export(run: RunRecord) -> dict[str, Any]:
    state = run.state
    datasets = list(state.get("datasets", {}).values())
    versions = list(state.get("dataset_versions", {}).values())
    nodes = list(state.get("nodes", {}).values())
    return {
        "eventType": "COMPLETE" if run.status == "completed" else "OTHER",
        "eventTime": run.updated_at.isoformat(),
        "producer": "https://local.evolastra.invalid",
        "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json",
        "run": {
            "runId": run.id,
            "facets": {"evolastra": {"schema_version": 1, "status": run.status}},
        },
        "job": {
            "namespace": "evolastra",
            "name": run.title,
            "facets": {"documentation": {"description": run.objective}},
        },
        "inputs": [
            {
                "namespace": str(dataset.get("namespace", "evolastra")),
                "name": str(dataset.get("name", dataset.get("id"))),
                "facets": {"evolastra": {"dataset_id": dataset.get("id")}},
            }
            for dataset in datasets
        ],
        "outputs": [
            {
                "namespace": "evolastra://dataset-version",
                "name": str(version.get("id")),
                "facets": {"schema": {"fields": version.get("schema", [])}},
            }
            for version in versions
        ],
        "evolastraSemanticNodes": [
            {"id": node.get("id"), "title": node.get("title"), "status": node.get("status")}
            for node in nodes
        ],
    }


def prov_export(run: RunRecord) -> dict[str, Any]:
    state = run.state
    entities: dict[str, Any] = {}
    activities: dict[str, Any] = {}
    agents: dict[str, Any] = {}
    used: dict[str, Any] = {}
    generated: dict[str, Any] = {}
    for dataset in state.get("datasets", {}).values():
        entities[f"evolastra:{dataset['id']}"] = {
            "prov:type": "Dataset",
            "prov:label": dataset.get("name"),
        }
    for artifact in state.get("artifacts", {}).values():
        key = f"evolastra:{artifact['id']}"
        entities[key] = {"prov:type": "Artifact", "prov:label": artifact.get("title")}
        node_id = artifact.get("node_id")
        if node_id:
            generated[f"gen:{artifact['id']}"] = {
                "prov:entity": key,
                "prov:activity": f"evolastra:{node_id}",
            }
    for node in state.get("nodes", {}).values():
        activities[f"evolastra:{node['id']}"] = {
            "prov:type": "AnalysisOperation",
            "prov:label": node.get("title"),
        }
        for dataset_id in node.get("dataset_ids", []):
            used[f"use:{node['id']}:{dataset_id}"] = {
                "prov:activity": f"evolastra:{node['id']}",
                "prov:entity": f"evolastra:{dataset_id}",
            }
    for agent in state.get("agents", {}).values():
        agents[f"evolastra:{agent['id']}"] = {
            "prov:type": "SoftwareAgent",
            "prov:label": agent.get("name"),
        }
    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "evolastra": "https://local.evolastra.invalid/ns/",
        },
        "@id": f"evolastra:{run.id}",
        "prefix": {"evolastra": "https://local.evolastra.invalid/id/"},
        "entity": entities,
        "activity": activities,
        "agent": agents,
        "used": used,
        "wasGeneratedBy": generated,
    }


def obsidian_zip(run: RunRecord) -> bytes:
    state = run.state
    buffer = io.BytesIO()
    manifest: list[dict[str, Any]] = []
    run_title = SAFE_NAME.sub("", run.title).strip()[:100] or run.id
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        overview_path = f"Evolastra/{run_title}/Overview.md"
        findings = list(state.get("findings", {}).values())
        claims = list(state.get("claims", {}).values())
        overview = [
            "---",
            f"evolastra_run_id: {run.id}",
            f"status: {run.status}",
            "---",
            f"# {run.title}",
            "",
            run.objective,
            "",
            "## Findings",
            "",
        ]

        def note_name(item: dict[str, Any]) -> str:
            safe = SAFE_NAME.sub("", str(item.get("title", item["id"]))).strip()[:88]
            return f"{safe or 'Untitled'}--{str(item['id'])[-8:]}"

        for finding in findings:
            safe = note_name(finding)
            overview.append(f"- [[Findings/{safe}]]")
        overview.extend(["", "## Claims", ""])
        for claim in claims:
            safe = note_name(claim)
            overview.append(f"- [[Claims/{safe}]]")
        archive.writestr(overview_path, "\n".join(overview) + "\n")
        manifest.append({"entity_id": run.id, "path": overview_path, "kind": "run"})

        for kind, values in (("Findings", findings), ("Claims", claims)):
            for item in values:
                safe = note_name(item)
                path = f"Evolastra/{run_title}/{kind}/{safe}.md"
                body = [
                    "---",
                    f"evolastra_id: {item['id']}",
                    f"status: {item.get('status', item.get('validation_status', 'unknown'))}",
                    "---",
                    f"# {item.get('title', item['id'])}",
                    "",
                    str(item.get("summary", item.get("statement", ""))),
                    "",
                    f"Source run: [[../Overview|{run.title}]]",
                ]
                archive.writestr(path, "\n".join(body) + "\n")
                manifest.append({"entity_id": item["id"], "path": path, "kind": kind.lower()})
        archive.writestr(
            f"Evolastra/{run_title}/export-manifest.json",
            json_bytes({"version": 1, "files": manifest}),
        )
    return buffer.getvalue()


def reproduction_zip(run: RunRecord, events: Iterable[EventRecord]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "run.json",
            json_bytes(
                {"id": run.id, "title": run.title, "objective": run.objective, "seed": run.seed}
            ),
        )
        archive.writestr("events.jsonl", cloudevents_jsonl(events))
        archive.writestr(
            "environment.json",
            json_bytes({"schema_version": 1, "profile": "local", "python": "3.12"}),
        )
        archive.writestr(
            "README.md",
            "# Reproduction bundle\n\nImport `events.jsonl` through the documented JSONL import endpoint. The bundle contains metadata and event history, not executable code.\n",
        )
    return buffer.getvalue()
