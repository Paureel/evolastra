# API companion instructions

_Local guidance for the durable event store, semantic projection, and companion_

---

Scope: `apps/api/asterism_api/` and API-owned migrations.

Read [architecture invariants](../../docs/architecture/invariants.md),
[semantic model](../../docs/architecture/semantic-model.md), and
[privacy model](../../docs/security/privacy-model.md) before changing durable
behavior.

## 📍 Ownership

- `schemas.py` defines validated API-domain shapes.
- `event_store.py` owns durable sequencing, idempotency, quarantine, snapshots,
  and projection transactions.
- `reducer.py` is a pure deterministic projection function.
- `db_models.py` and `migrations/` own persistence shape.
- `api.py` and `main.py` are transport and composition layers.
- `service.py`, `access.py`, and `codex_*` own the loopback companion boundary.

## 🛡️ Change rules

- Keep `reducer.py`, `schemas.py`, `security.py`, and `ids.py` free of transport,
  database, and service dependencies.
- Add an Alembic migration for persistent model changes.
- Add deterministic reducer/replay coverage for projection changes.
- Validate and redact before persistence, logging, or export.
- Never bind the Local Private companion to `0.0.0.0`.

Run focused Python tests first, then:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_event_store.py tests/test_reducer.py -q
npm run check
```
