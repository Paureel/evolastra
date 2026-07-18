# OpenLineage

`integrations.openlineage.ingest_run_event` maps an OpenLineage `RunEvent` state to an Evolastra run event and maps input/output dataset identities to dataset registration events. Job/run/dataset facets are preserved after redaction; the mapper does not force every Job to become a semantic analysis node.

Supported run states follow the current specification: `START`, `RUNNING`, `COMPLETE`, `ABORT`, `FAIL`, and `OTHER`. Import requires `run.runId` plus `job.namespace` and `job.name`.

`export_run_event` exports the compatible run/dataset subset. The caller must provide `producer` and `schema_url`, deliberately pinning the OpenLineage version it validates against. Rich Evolastra claims, evidence, approvals, and visualization state are not representable and are not discarded from the canonical store; they simply do not appear in this subset export.

Sources: official OpenLineage [object model](https://openlineage.io/docs/spec/object-model) and [run cycle](https://openlineage.io/docs/spec/run-cycle).
