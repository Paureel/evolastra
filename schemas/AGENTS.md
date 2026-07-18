# Event schema instructions

_Local guidance for versioned durable analytical event contracts_

---

Scope: `schemas/events/` and `schemas/examples/`.

Read the [shared contract](../docs/architecture/shared-contract.md),
[CloudEvents protocol](../docs/event-protocol/cloud-events.md), and
[architecture invariants](../docs/architecture/invariants.md).

## 🛡️ Change rules

- Treat a schema filename and `$id` as a versioned public contract.
- Add a representative example for every concrete event schema.
- Keep visualization-owned camera, animation, viewport, and coordinate fields
  out of durable event envelopes.
- Preserve strict top-level validation and per-run sequence semantics.
- Update reducer support, protocol documentation, and integration fixtures when
  an event contract changes.

Run:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/contracts tests/property -q
npm run harness
```
