# Contributing

Preserve the three-layer boundary in `docs/architecture/shared-contract.md`. Operational spans do not automatically become semantic nodes, and galaxy coordinates never enter canonical payloads.

Use prefixed compact UUIDv4 IDs, five-segment versioned event types, UTC timestamps, and local schema paths. Corrections are new events. Add a migration for database changes and a deterministic reducer test for projection changes.

Before handing off a change, run:

```powershell
npm run verify
```

Never add a third-party visual asset without a primary-source license record, checksum, attribution decision, and entry in `docs/assets/asset-manifest.json`.
