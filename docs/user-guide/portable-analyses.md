# Portable analyses

Use **Advanced → Save / load → Save analysis** to download the active run as a `.evolastra` file. It contains a versioned manifest and the complete redacted semantic event history required to rebuild the viewer.

Use **Load analysis** in any connected Evolastra viewer to restore the file into that user's local companion. Existing event IDs make repeated imports idempotent, and projection snapshots are regenerated locally.

Portable files are data-only ZIP containers. The importer enforces the configured request limit, accepts only `manifest.json` and `events.jsonl`, does not extract paths, and does not execute artifacts or analysis code.
