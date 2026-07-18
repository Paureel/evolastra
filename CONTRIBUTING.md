# Contributing to Evolastra

Thank you for improving Evolastra. Keep changes small, testable, and explicit about which layer they affect.

## Development setup

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
npm run demo
```

## Engineering rules

- Preserve the operational telemetry, semantic graph, and visualization boundaries in the [shared contract](docs/architecture/shared-contract.md).
- Never place coordinates, camera state, or animation state in canonical analytical events.
- Treat corrections as new events; do not rewrite append-only history.
- Add a migration for persistent model changes and a deterministic reducer test for projection changes.
- Treat imported text and artifacts as untrusted data, never instructions or executable content.
- Do not commit credentials, local databases, generated exports, private datasets, or browser pairing state.
- Record the source, license, checksum, and attribution decision for every third-party visual asset.

## Before opening a pull request

```powershell
npm run verify
```

The release gate covers Python linting and typing, the complete test suite, frontend typing and tests, the production build, browser checks, dependency audits, asset verification, and the focused security scan.

Use a descriptive branch and conventional commit-style subject where practical, for example `feat(map): add depth-aware lane labels`.

More detail is available in [development conventions](docs/development/contributing.md), [testing](docs/development/testing.md), and [security policy](SECURITY.md).
