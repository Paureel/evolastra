# GitHub Copilot instructions

Read and follow the repository-wide [`AGENTS.md`](../AGENTS.md), then the nearest
nested `AGENTS.md` for the files you change. Use the
[repository map](../docs/architecture/repository-map.md) to locate ownership and
the [harness guide](../docs/development/harness.md) for the feedback loop.

For installation requests, use the supported bootstrap:

```powershell
npm run bootstrap:check
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -NoBrowser
```

Preserve Evolastra's local-private boundary. Never read or expose the root
companion token, commit local databases or private datasets, or configure remote
analysis storage without explicit authorization.

During development run focused tests followed by `npm run check`. Run
`npm run verify` before handoff or push. Cross-cutting or multi-session work uses
a versioned plan under `docs/plans/active/`.
