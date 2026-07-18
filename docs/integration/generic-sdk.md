# Generic instrumentation SDKs

## Python

The stdlib-only package under `sdk/python/galaxy_sdk` provides run/node/tool context managers, a node decorator, claim creation, content-hashed artifact registration, and list, JSONL, and HTTP sinks. Every semantic lifecycle event carries canonical `data.run`, `data.node`, `data.tool_call`, `data.artifact`, or `data.claim` identity fields, including completion and failure events. It emits opaque artifact IDs and metadata; it never uploads a local path. `GalaxyClient(..., deduplication_key=callable)` can supply shared native identity material for overlap with another adapter; the returned material is hashed before persistence.

Run the checked example from the repository root:

```powershell
python examples/integrations/python_sdk_demo.py
```

The command prints the temporary JSONL path. HTTP instrumentation is synchronous, so use JSONL or another buffered sink on latency-sensitive paths.

## TypeScript

`sdk/typescript/src/index.ts` contains a typed envelope, `entityData` helper, canonical semantic-entity validation, redaction, and callback sink. The sink rejects semantic events missing `data.<entity>.id`, `run_id`, or `schema_version`. The standalone source is checked with TypeScript strict mode, but there is no package manifest or published package in this workstream.

```powershell
npx --no-install tsc --noEmit --strict --target ES2022 --module ESNext sdk/typescript/src/index.ts
```

## JSONL

`integrations.jsonl.JsonlWriter` validates, re-redacts, flushes, and fsyncs each record. `JsonlTailer` resumes from a byte offset, yields complete newline-terminated objects only, and rejects oversized lines. A tailer offset should be checkpointed only after downstream acknowledgement.
