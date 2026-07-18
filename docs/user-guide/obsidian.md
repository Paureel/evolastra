# Obsidian export

Choose **Export → obsidian** to download a ZIP containing:

- a run overview;
- one note per finding and claim;
- stable wikilinks;
- frontmatter with Evolastra IDs and validation state; and
- `export-manifest.json` mapping entity IDs to vault-relative paths.

Filenames are sanitized, collision-proofed with ID suffixes, and never absolute or traversal-bearing. Extract the `Evolastra` folder into a chosen vault. The application never writes directly to an arbitrary vault path in the verified local profile.
