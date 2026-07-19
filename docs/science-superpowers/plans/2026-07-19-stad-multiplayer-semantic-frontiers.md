# Three-empire STAD semantic-frontier analysis plan

> **For agentic workers:** REQUIRED SUB-SKILL: pre-register this plan with science-superpowers:preregistering-analysis BEFORE execution. Then use science-superpowers:subagent-driven-analysis (recommended) or science-superpowers:executing-analysis to run it step-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Question:** Can six exploratory STAD CNA hypotheses be divided among three multiplayer empires so deterministic 3D map distance preserves declared mechanistic similarity?

**Design:** Exploratory re-use of an already inspected observational CNA summary plus deterministic method validation on a fixed six-system semantic fixture.

**Data:** Aggregate results for 438 TCGA-STAD tumors and 25,128 gene rows in `data/live-test/stad_cna_live_summary.json`; no sample identifiers or raw matrix values enter the simulation artifact.

**Primary analysis:** Weighted Jaccard semantic distance followed by deterministic three-dimensional stress minimization; compare the 15 pairwise semantic distances with normalized rendered Euclidean distances.

**Decision rule:** The spatial contract passes only if Spearman rank correlation is at least 0.80, mean within-empire map distance is below mean between-empire distance, and every system's nearest neighbor belongs to the same empire.

---

### Task 1: Implement semantic signatures and distance

**Artifacts:**
- Create: `apps/web/src/semanticLayout.ts`
- Create: `apps/web/src/semanticLayout.test.ts`
- Modify: `apps/web/src/types.ts`

- [x] Define signatures with program, alteration direction, genes, cytobands, mechanisms, therapeutic modalities, and validation modalities.
- [x] Normalize tokens by trimming and case folding; deduplicate within fields.
- [x] Compute weighted Jaccard distance with weights: program 5, genes 5, cytobands 4, mechanisms 4, therapeutic modalities 3, alteration direction 2, validation modalities 1.
- [x] Validate identity distance = 0, symmetry, range [0,1], and a same-program/shared-mechanism pair closer than an orthogonal pair.

### Task 2: Derive deterministic semantic coordinates

**Artifacts:**
- Modify: `apps/web/src/semanticLayout.ts`
- Modify: `apps/web/src/layout.ts`
- Modify: `apps/web/src/layout.test.ts`

- [x] Initialize signed deterministic 3D positions from stable hashes and center them.
- [x] Run 1,200 full-batch gradient-descent iterations against target distance `120 + 560 × semantic_distance`, learning rate 0.018 with linear decay, then normalize the field to a maximum radius of 520. This is the documented product-method deviation after the frozen 600-step method failed to converge (`rho=0.7366`); the affected validation remains exploratory.
- [x] Use semantic coordinates only for top-level nodes carrying signatures; retain the existing deterministic layout for all other systems and orbital objects.
- [x] Validate repeatability, finite coordinates, Spearman correlation ≥ 0.80, within-empire separation, and same-empire nearest neighbors on the fixed fixture.

### Task 3: Expose semantic meaning in the interface

**Artifacts:**
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/components/MapBrief.tsx` or `apps/web/src/mapBrief.ts`
- Modify: `apps/web/src/components/GalaxyCanvas.tsx`
- Modify: `apps/web/src/styles.css`
- Modify: `docs/user-guide/galaxy.md`

- [x] Preserve semantic signatures when canonical nodes become disposable scene entities.
- [x] Show research program, alteration direction, genes, and mechanism in the selected-system brief.
- [x] Add a concise map legend stating that proximity encodes shared program/gene/mechanism/validation features.
- [x] Verify the textual accessibility surface contains the same meaning without relying on position or color.

### Task 4: Create the fixed three-empire simulation

**Artifacts:**
- Create: `scripts/simulate_stad_multiplayer.py`
- Write ignored result: `data/live-test/stad_multiplayer_simulation.json`

- [x] Verify the source summary checksum metadata and fixed 438-tumor/25,128-gene dimensions.
- [x] Append six bounded semantic node events, six exploratory finding events, and three agent events without modifying prior history.
- [x] Create three multiplayer identities: Amplification Dominion (gold), Loss Cartographers (cyan), and Constellation Pact (purple).
- [x] Assign two systems to each identity through ordinary multiplayer domain operations; do not place claims in canonical event payloads.
- [x] Write aggregate IDs, signature distances, map-distance validation, and source checksum to the ignored simulation result.

### Task 5: Verify end to end

**Artifacts:**
- Write ignored captures: `output/playwright/stad-three-empires-*.png`
- Update: `docs/audit/final-verification.md`

- [x] Run semantic-layout unit tests, TypeScript typecheck, and Python simulation tests/check mode.
- [x] Execute the simulation once against the private STAD live database with seed 874049.
- [x] Query the API and assert three players, six hypothesis claims, three colors, six falsifiable findings, no projection gaps, and no raw sample identifiers in the result artifact.
- [x] Open the live browser with Playwright CLI, verify empire territories and semantic legend, inspect one system per empire, and capture ignored screenshots.
- [x] Run `npm run check`; retain the private-dataset interaction as a Playwright CLI check so the generic release suite remains isolated from `stad_data/`.
