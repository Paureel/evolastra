# Durable CloudEvents profile

_Version 1 profile for ingestion, persistence, replay, export, and browser delivery_

---

## 📋 Profile rules

Every durable semantic event is CloudEvents-compatible structured JSON.[^1] The server accepts a missing `sequence` only at ingestion and allocates it transactionally per run. Every persisted, exported, and streamed event has a positive `sequence`.

The endpoints are:

- `POST /api/v1/events` for one event
- `POST /api/v1/events/batch` for an ordered batch
- `GET /api/v1/runs/{run_id}/events/stream?after=<sequence>` for the resumable SSE feed

Stored events are immutable. A correction is a new event with its own ID and sequence. Unknown event types are persisted and ignored by projections. Invalid envelopes enter quarantine with a redacted reason.

## ⚙️ Envelope fields

| Field | Type | Requirement |
| --- | --- | --- |
| `specversion` | String | Required; `1.0` |
| `id` | String | Required; globally unique prefixed UUIDv4 |
| `source` | URI-reference | Required; stable producer identity |
| `type` | String | Required; `galaxy.<area>.<entity>.<action>.v1` |
| `subject` | String | Required; stable path scoped to the affected entity |
| `time` | UTC RFC 3339 string | Required; event time |
| `datacontenttype` | String | Required; `application/json` |
| `dataschema` | URI-reference | Required; local path such as `/schemas/events/artifact-created.v1.schema.json` |
| `runid` | String | Required; prefixed UUIDv4 |
| `sequence` | Integer | Required after ingestion; monotonically allocated per run |
| `traceid` | String | Required; non-zero 32-character W3C trace ID |
| `spanid` | String | Required; non-zero 16-character W3C span ID |
| `correlationid` | String | Required; stable prefixed ID grouping a logical workflow |
| `causationid` | String | Required; stable prefixed ID of the direct triggering event or root entity |
| `producerversion` | String | Required; adapter or simulator version |
| `privacyclass` | String | Required; `public`, `internal`, `confidential`, or `restricted` |
| `data` | Object | Required; type-specific payload |

The event schema is strict about envelope fields. Type-specific payload schemas use the canonical entity key, for example `data.run`, `data.node`, or `data.artifact`. Large binary data is stored as an artifact and referenced by opaque ID.

Internal producers default to `/schemas/events/semantic-event-v1.json`, the local generic envelope schema. A producer may select a registered type-specific path such as `/schemas/events/artifact-created.v1.schema.json` for stronger payload validation. Both forms resolve through the read-only local schema route and require no external schema host.

## 📦 Representative event

This artifact event uses a local schema path and includes every required extension.

```json
{
  "specversion": "1.0",
  "id": "evt_a45bb1a3-1df5-481f-9e98-601e393f24ce",
  "source": "urn:galaxy:adapter:simulator",
  "type": "galaxy.analysis.artifact.created.v1",
  "subject": "run/run_33bd8a55-5154-4233-bfc3-1c327b2398e6/artifact/art_1591ab40-a089-4191-8508-3f99d951bb5e",
  "time": "2026-07-17T14:20:30.123Z",
  "datacontenttype": "application/json",
  "dataschema": "/schemas/events/artifact-created.v1.schema.json",
  "runid": "run_33bd8a55-5154-4233-bfc3-1c327b2398e6",
  "sequence": 3,
  "traceid": "0af7651916cd43dd8448eb211c80319c",
  "spanid": "b7ad6b7169203331",
  "correlationid": "corr_b5827dc7-2765-4b70-94d8-953ae7bece9f",
  "causationid": "evt_41f5a55c-2e3c-4078-8d4a-2d76e6595d53",
  "producerversion": "simulator/1.0.0",
  "privacyclass": "internal",
  "data": {
    "artifact": {
      "id": "art_1591ab40-a089-4191-8508-3f99d951bb5e",
      "schema_version": 1,
      "run_id": "run_33bd8a55-5154-4233-bfc3-1c327b2398e6",
      "node_id": "node_4639b2f6-c02a-4cef-a10b-2a59d9137e93",
      "artifact_type": "vega_lite",
      "title": "Churn by customer tenure",
      "mime_type": "application/vnd.vegalite.v5+json",
      "content_hash": "sha256:7b7e4dd8f8d40de8b97a18fc19b3d23ecfb37f2d1eeef24d7c12b58e46c99baf",
      "created_at": "2026-07-17T14:20:30.123Z",
      "privacy_classification": "internal"
    }
  }
}
```

The checked fixture is [`schemas/examples/artifact-created.v1.json`](../../schemas/examples/artifact-created.v1.json), validated by [`schemas/events/artifact-created.v1.schema.json`](../../schemas/events/artifact-created.v1.schema.json).

## 🔄 Ingestion and ordering

1. Parse structured JSON and apply size limits
2. Redact known secret-shaped content before persistence or logging
3. Validate the envelope and registered payload schema
4. Enforce globally unique `id`
5. Allocate `sequence` under the run's write transaction when absent
6. Append event and apply supported projection changes transactionally
7. Return the canonical persisted event, including its sequence

Client-supplied sequences are accepted only when they satisfy the import policy and do not violate the run's monotonic order. Gaps and out-of-order imports are detected, not silently renumbered. Repeated event IDs are idempotent; the stored event remains unchanged.

Batch ingestion preserves the submitted order within each run. A batch containing several runs is ordered independently per run. The API reports item-level validation failures and does not expose unredacted rejected payloads.

## 📤 SSE representation

Each durable event is sent as one SSE frame:

```text
id: 3
event: semantic
data: {"specversion":"1.0","id":"evt_a45bb1a31df5481f9e98601e393f24ce","source":"urn:galaxy:adapter:simulator","type":"galaxy.analysis.artifact.created.v1","subject":"run/run_33bd8a5551544233bfc31c327b2398e6/artifact/art_1591ab40a089419185083f99d951bb5e","time":"2026-07-17T14:20:30.123Z","datacontenttype":"application/json","dataschema":"/schemas/events/artifact-created.v1.schema.json","runid":"run_33bd8a5551544233bfc31c327b2398e6","sequence":3,"traceid":"0af7651916cd43dd8448eb211c80319c","spanid":"b7ad6b7169203331","correlationid":"corr_b5827dc727654b7094d8953ae7bece9f","causationid":"evt_41f5a55c2e3c40788d4a2d76e6595d53","producerversion":"simulator/1.0.0","privacyclass":"internal","data":{"artifact":{"id":"art_1591ab40a089419185083f99d951bb5e","schema_version":1,"run_id":"run_33bd8a5551544233bfc31c327b2398e6","node_id":"node_4639b2f6c02a4cefa10b2a59d9137e93","artifact_type":"vega_lite","title":"Churn by customer tenure","mime_type":"application/vnd.vegalite.v5+json"}}}

```

Clients resume with `after` or `Last-Event-ID`; if both are valid, the larger sequence wins. A request after the current tail stays open and receives heartbeats until a durable event is available.

## 📊 Initial type registry

The initial projector recognizes these v1 type values. A schema may be added for each payload without changing the envelope profile. `snapshot.created` is reserved by the shared contract but snapshots are currently internal projection records rather than emitted events.

| Area | Entity | Actions |
| --- | --- | --- |
| `analysis` | `run` | `created`, `started`, `updated`, `completed`, `failed` |
| `analysis` | `node` | `created`, `promoted`, `started`, `progress`, `completed`, `failed` |
| `analysis` | `agent` | `created`, `started`, `status_changed`, `handed_off`, `completed`, `failed` |
| `analysis` | `tool_call` | `requested`, `started`, `completed`, `failed` |
| `analysis` | `dataset` | `registered` |
| `analysis` | `dataset_version` | `created` |
| `analysis` | `artifact` | `created`, `preview_created` |
| `analysis` | `claim` | `created`, `validated`, `disputed` |
| `analysis` | `evidence` | `attached` |
| `analysis` | `finding` | `created`, `promoted` |
| `analysis` | `anomaly` | `created`, `resolved` |
| `analysis` | `approval` | `requested`, `recorded` |
| `analysis` | `annotation` | `created` |
| `analysis` | `metric` | `recorded` |

For example, the first row expands to `galaxy.analysis.run.created.v1`. Type matching is exact and case-sensitive.

SSE heartbeats are transport messages with `{runid, sequence, time}`. They are not durable CloudEvents, do not have an event ID, and do not advance the run sequence.

## 🔐 Privacy and failure behavior

`privacyclass` governs storage, preview, export, and logging policy; it is not a substitute for authorization. The event receiver treats all imported content as untrusted data. It never executes code or active document content.

Validation errors return a safe JSON result with a redacted reason and quarantine ID. Quarantine stores the raw payload only under the configured restricted policy; operator-facing lists expose identifiers, timestamps, source, and redacted failure summaries. Retry creates a new processing attempt, not an edited event.

## 🔗 References

[^1]: Cloud Native Computing Foundation. "CloudEvents Specification." https://github.com/cloudevents/spec
