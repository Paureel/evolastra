# Asset verification guidance

The release gate must fail closed: a visual file found in a shipped asset root is an error until a manifest record explains its origin, license, checksum, and use. The current manifest is validly empty because the reviewed repository shipped no visual files.

## Scope

The roots and extensions in [asset-manifest.json](./asset-manifest.json) define discovery. This includes images, SVG, fonts, audio, 3D sources, texture containers, glTF buffers, and atlas metadata. Add a scan root before placing a shippable asset elsewhere; do not use an unscanned directory as an escape hatch.

First-party procedural output is also recorded so every shipped file has a checksum and reproducible origin. Third-party records additionally require all fields represented by [asset-ledger.csv](./asset-ledger.csv).

## Required record shape

Each `assets[]` object must contain:

- `internalAssetId`, `filename`, `assetType`, `title`, `creator`, and `origin` (`first-party` or `third-party`);
- `primarySource`, `directSourcePage`, `licenseId`, `licenseVersion`, and `licenseEvidence`;
- booleans `commercialUseAllowed`, `modificationAllowed`, `redistributionAllowed`, and `attributionRequired`;
- `requiredAttributionText`, `downloadDate`, `originalSha256`, `modifiedSha256`, and `modificationsMade`;
- `applicationLocations`, `reviewer`, and `approvalState`;
- for generated first-party work: `generatorPath`, `generatorVersion`, and deterministic `seedPolicy`.

Use repository-relative forward-slash paths and lowercase 64-character SHA-256 values. If one source produces multiple shipped files, create one record per shipped file or provide a verifier-supported `shippedFiles[]` expansion; never hide derivative files behind one unchecked source record.

## Automated checks

`verify-assets` should:

1. Parse the manifest and reject an unknown schema version.
2. Discover every matching file under every scan root.
3. Require an exact one-to-one match between discovered files and manifest filenames.
4. Reject duplicate IDs, duplicate filenames, missing files, path traversal, and files outside the repository.
5. Recompute every shipped SHA-256 and compare it with `modifiedSha256`.
6. Validate the original checksum and transformation description for modified third-party work.
7. Reject licenses outside the approved list and require explicit approval for case-by-case entries.
8. Require a primary source page and exact license evidence for each third-party file.
9. Require all commercial-use/modification/redistribution booleans to be true for an approved modified asset.
10. Require the exact attribution text to appear in `THIRD_PARTY_ASSETS.md` when attribution is required.
11. Require every third-party manifest ID to appear exactly once in the CSV ledger.
12. Reject unapproved or pending records in production builds.
13. Scan CSS, HTML, and source for runtime visual-asset URLs and reject unmanifested remote product artwork.
14. Sanitize SVG separately, reject scripts/external references, and verify no embedded raster escapes the manifest.
15. Emit a deterministic summary with discovered count, first-party count, third-party count, and failures.

The included [verify-assets.ps1](./verify-assets.ps1) is a repository-local baseline for items 1–12. The integration lead should wire it into the root release command and extend source-URL/SVG checks in the normal test stack.

## Commands

From the repository root:

```powershell
pwsh -NoProfile -File docs/assets/verify-assets.ps1
```

If `pwsh` is not installed, Windows PowerShell can run the current baseline:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/assets/verify-assets.ps1
```

Do not convert a failure to a warning for release. A deliberately absent optional asset should be removed from the manifest and all application references, not marked missing-but-approved.

## Reviewer procedure for a new external asset

1. Open the exact primary source page; save the license URL/file and review any author notes or included-license exceptions.
2. Download from that source and hash the untouched original immediately.
3. Quarantine the original outside shipped roots until approved.
4. Record the ledger and manifest fields before transformation.
5. Transform through a pinned, documented pipeline; hash each output.
6. Add required attribution verbatim and identify where users can open it.
7. Run the verifier, visual regression, accessibility check, and originality review.
8. Approve with a named reviewer. Self-authored first-party work still requires a second-person originality review before release when possible.
