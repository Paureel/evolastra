# GitHub Copilot instructions

Read and follow the repository-wide [`AGENTS.md`](../AGENTS.md) before changing or operating Evolastra.

For installation requests, use the supported bootstrap:

```powershell
npm run bootstrap:check
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -NoBrowser
```

Preserve Evolastra’s local-private boundary. Never read or expose the root companion token, commit local databases or private datasets, or configure remote analysis storage without explicit authorization.
