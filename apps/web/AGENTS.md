# Web observatory instructions

_Local guidance for browser state, accessible interaction, and 3D rendering_

---

Scope: `apps/web/`.

Read the [visualization model](../../docs/architecture/visualization-model.md),
[map user guide](../../docs/user-guide/galaxy.md), and
[testing strategy](../../docs/development/testing.md).

## 📍 Ownership

- `types.ts` carries browser-side contracts.
- `layout.ts`, `spatial.ts`, `galaxyFrontier.ts`, `mapGraph.ts`, `replay.ts`,
  `techTree.ts`, and `mapBrief.ts` are deterministic browser-domain modules.
- `api.ts`, `connection.ts`, and `hooks/` own transport and live state.
- `components/` and `App.tsx` own accessible interaction and presentation.
- `GalaxyCanvas.tsx` renders a disposable projection; it is never canonical
  analytical storage.
- `public/demo/stad-three-empires-v1.json` is the sole hosted analysis fixture.
  It is explicitly public, bounded, aggregate-only, and read-only under ARCH-008.

## 🛡️ Change rules

- Keep deterministic modules independent from React components, hooks, and API
  clients.
- Preserve unrestricted 3D rotation, connected galaxy topology, keyboard
  controls, reduced motion, and the textual accessibility surface.
- Put testable geometry and state transitions outside React components.
- Do not add another hosted analysis, private export, dynamic demo URL, upload,
  or mutation surface. Changing the public showcase boundary requires its ADR,
  invariant, harness rule, privacy review, and regression tests together.
- Update unit coverage for deterministic behavior and Playwright coverage for
  user-visible interaction changes.

Run:

```powershell
npm --prefix apps/web run typecheck
npm --prefix apps/web run test
npm run check
```
