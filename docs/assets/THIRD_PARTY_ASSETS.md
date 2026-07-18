# Third-party visual assets

Status: complete for the repository snapshot reviewed on 2026-07-17.

## Shipped inventory

**No third-party visual assets are currently shipped.** The repository contained no raster images, SVG artwork, fonts, audio, 3D models, textures, or sprite atlases at review time. There is therefore no attribution text to display.

| Internal asset ID | Title | Creator | Primary source | Exact license | Required attribution | Shipped file | SHA-256 |
|---|---|---|---|---|---|---|---|
| _None_ | — | — | — | — | — | — | — |

The renderer packages discussed in the benchmark are software dependencies, not visual assets, and were only researched—not installed or shipped. Browser/system fonts named in the visual direction are not redistributed by this project.

## Admission policy

Prefer, in order:

1. project-created procedural or commissioned first-party work;
2. the exact asset released under CC0 1.0 or a clearly evidenced public-domain dedication;
3. the exact asset released under CC BY 4.0, when product attribution is acceptable;
4. SIL OFL 1.1 font files, only after reserved-name and redistribution terms are reviewed;
5. another commercial/redistribution-compatible license only after explicit legal and project approval.

The following are rejected by default: noncommercial, no-derivatives, share-alike without explicit approval, editorial-only, unclear or site-wide-only terms, fan art, screenshots, extracted game files, image-search results, franchise-adjacent designs, and generated work with unknown provenance.

For each proposed asset, the reviewer must open the asset's own primary source page, preserve the exact license evidence URL or file, record both original and shipped SHA-256 checksums, and verify commercial use, modification, redistribution, attribution, trademarks, and included third-party material. A marketplace's reputation or a phrase such as “free download” is not evidence.

The machine-readable source of truth is [asset-manifest.json](./asset-manifest.json); the tabular review record is [asset-ledger.csv](./asset-ledger.csv). This page must contain the exact human-readable attribution for every approved third-party record whose license requires it.

## Runtime remote assets

Runtime fetching of unmanifested images, fonts, models, textures, audio, or icons is prohibited. If remote content is an analytical artifact supplied by a user, it belongs to the sanitized artifact pipeline and must not be silently reused as product artwork.
