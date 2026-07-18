# Artifact guide

Artifacts are semantic records with type, MIME metadata, provenance, integrity metadata, bounded preview information, producing node, and related dataset version. Open **Advanced → Figures** to browse every figure produced by the selected run, or select an artifact elsewhere and choose **Open safe preview**.

The safe renderer recognizes numeric series, structured tables, text, and CNA-frequency rows. CNA figures use a zero-centered loss/gain scale with separate high-level event overlays and exact percentages, so color is never the only encoding. Unsupported or metadata-only artifacts show an explanatory empty state instead of a blank panel.

These figures are generated locally in the browser from bounded artifact data; they are not uploaded images and execute no artifact-provided code. The preview declares whether data is complete, sampled, or truncated. DuckDB-Wasm, Parquet, Arrow, PDF, notebook, and sanitized active-format viewers remain deferred and are not implied by the current renderer.
