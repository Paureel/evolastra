# Executable architecture invariants

_Stable constraints and the checks that keep them true_

---

These invariants are the stable constraints Evolastra optimizes around. The
implementation may evolve, but crossing one of these boundaries requires an
explicit architecture decision, updated documentation, and updated enforcement.

| ID | Invariant | Mechanical enforcement |
| --- | --- | --- |
| `ARCH-001` | Low-level API modules point inward and remain free of transport/service dependencies. The database composition root may import model registration lazily. | `scripts/harness.py` parses Python imports. |
| `ARCH-002` | Protocol adapters are portable and do not depend on the FastAPI companion implementation. | Imports under `integrations/` may not reference `asterism_api`. |
| `ARCH-003` | Deterministic browser-domain modules do not depend on React components, hooks, or API clients. | The harness checks TypeScript import direction. |
| `ARCH-004` | Durable event schemas contain semantic and operational facts, never visualization state. | Event schema properties are checked for camera, animation, viewport, and coordinate fields. |
| `ARCH-005` | The Local Private runtime binds loopback only. | Runtime Python and PowerShell sources reject `0.0.0.0`. |
| `ARCH-006` | Codex ship missions use local stdio, a fixed workspace-write sandbox, protocol-level developer guardrails, filtered child-process environment, disabled command network/web search, and no approval escalation. Imported analysis context remains lower-authority untrusted data. | The harness checks the app-server argv, developer-instruction separation, offline turn policy, environment filter, and thread-start policy, and rejects network transports or danger-full-access. |
| `ARCH-007` | Multiplayer shares only a bounded collaboration overlay through authenticated Tailscale federation routes. Remote targets must be HTTPS `.ts.net`, federation routes require a tailnet gate plus scoped bearer, and raw member grants stay in memory. | The harness checks transport, route, and persistence source boundaries; API tests verify replay isolation and authorization. |
| `ARCH-008` | Hosted analysis content is limited to the single versioned, explicitly public three-empire showcase. It contains bounded aggregate previews and synthetic display identities, never patient/sample identifiers, prompts, tool content, credentials, or private run exports. | The harness allowlists one static JSON path, validates public markers and size/row bounds, rejects extra demo files and private-shaped fields, and the browser loader accepts only the fixed showcase identity. |

Repository-operability rules use `HARNESS-*` IDs:

| ID | Invariant |
| --- | --- |
| `HARNESS-001` | Required navigation, local instructions, plans, and harness documents exist. |
| `HARNESS-002` | Relative Markdown links resolve, so agents can follow progressive documentation. |
| `HARNESS-003` | Versioned plans have a lifecycle, owner, update date, and validation record. |
| `HARNESS-004` | Supported Mermaid diagrams expose screen-reader titles and descriptions. |

## 🔄 Changing an invariant

1. Explain why the old boundary no longer serves the product in the
   [decision log](decision-log.md) or a new ADR.
2. Update the invariant and the [repository map](repository-map.md).
3. Change the harness rule and add a regression that proves the new boundary.
4. Run `npm run check` and `npm run verify`.
5. Record the validation evidence in the active plan before moving it to
   `docs/plans/completed/`.

Do not add an allowlist merely because a check is inconvenient. An allowlist is
itself an architecture decision and should name the narrow exception.
