# Repository map

_Ownership, verification, and change routes for humans and coding agents_

---

Use this map to find the authoritative home for a change before editing. The
nearest `AGENTS.md` adds local instructions for each major surface.

| Path | Owns | Primary verification |
| --- | --- | --- |
| `apps/api/asterism_api/` | Local companion, durable event store, semantic projection, access and exports | Python domain, API, security, replay tests |
| `apps/web/src/` | Browser transport, accessible UI, deterministic layouts, 3D Canvas renderer | TypeScript, Vitest, Playwright, axe |
| `apps/web/public/demo/` | The single allowlisted aggregate-only public showcase | ARCH-008 harness, privacy fixture test, Playwright |
| `integrations/` | Narrow protocol-to-CloudEvent adapters | Fixture-driven integration tests |
| `schemas/` | Versioned durable event contracts and examples | JSON Schema contract and property tests |
| `migrations/` | Forward persistence evolution | Migration plus rebuild/replay tests |
| `sdk/` | External Python and TypeScript client surfaces | Contract/integration tests |
| `skills/evolastra/` | Codex operating workflow for the local companion | Skill contract and local-private tests |
| `scripts/` | Bootstrap, developer feedback, release and security automation | Harness tests and CI |
| `tests/` | Cross-surface behavioral and architectural evidence | Pytest and Playwright |
| `docs/` | Product, architecture, security, operation, plans, and decisions | Harness link and plan checks |

## 🔄 Change routes

| Change | Expected companion changes |
| --- | --- |
| New durable event | Versioned schema and example, Pydantic shape, reducer behavior, contract/property tests, protocol docs |
| Persistent field | SQLAlchemy model, Alembic migration, restore/rebuild coverage, export review |
| Projection behavior | Pure reducer change, deterministic replay test, semantic model update if meaning changes |
| Map geometry or camera | Deterministic web module, Vitest assertions, user guide, Playwright interaction when visible |
| New integration | Narrow adapter, sanitized fixture, support-matrix status, integration test |
| Companion or hook behavior | Service/access code, local-private tests, getting-started and integration docs |
| Architecture boundary | Decision record, invariant, harness rule, regression test, completed plan evidence |

## 📍 Source-of-truth order

When sources disagree, resolve them in this order:

1. Durable schemas and executable tests
2. Executable harness rules
3. Accepted architecture decisions and invariants
4. Surface-specific documentation
5. Examples and screenshots

Fix stale lower-priority material in the same change. Do not silently preserve a
contradiction for the next agent.
