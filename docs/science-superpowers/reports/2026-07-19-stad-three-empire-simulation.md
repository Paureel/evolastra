# STAD three-empire multiplayer simulation report

**Status:** Complete, exploratory
**Question:** [Three-empire semantic exploration](../questions/2026-07-19-stad-multiplayer-semantic-frontiers.md)
**Plan:** [Execution plan](../plans/2026-07-19-stad-multiplayer-semantic-frontiers.md)
**Original method registration:** [600-iteration registration](../preregistrations/2026-07-19-stad-multiplayer-semantic-frontiers.md)
**Product revision:** [1,200-iteration design freeze](../preregistrations/2026-07-19-stad-semantic-layout-product-revision.md)

## Input and boundary

- Private source: gene-level TCGA-STAD log2 CNA matrix
- SHA-256: `75de2036e7fa12025a32176a5d7fc0639472a4371d19cf20fb7a00f098630fa2`
- Aggregate dimensions: 25,128 genes × 438 tumors
- Fixed simulation seed: `874049`
- The raw matrix, sample identifiers, SQLite database, result JSON, browser
  captures, and pairing state remain ignored local files.

The biological outputs below reuse outcomes inspected during the earlier STAD
analysis. They are exploratory hypotheses, not confirmatory findings, causal
effects, treatment recommendations, or claims of novelty.

## Exploratory empires and directions

| Empire | Program | Claimed hypothesis systems |
| --- | --- | --- |
| Amplification Dominion | Dosage-driven amplification dependencies | MYC–ATR stress; CCNE1 replication stress |
| Loss Cartographers | Deletion and collateral/synthetic vulnerabilities | CDKN2A checkpoint loss; ARID1A chromatin synthetic lethality |
| Constellation Pact | Co-alteration combination strategies | ERBB2–CCNE1 dual program; TERT–RICTOR co-gain |

Each system records a directional prediction, an explicit falsifier, and a
required validation path. The completed local simulation contains three running
mothership agents, six running hypothesis systems, six hypothesis territory
claims, one host-capital claim, and six bounded publications. Synthetic-player
status is explicit in the federation console.

## Semantic geography result

Semantic distance is weighted Jaccard dissimilarity over program, alteration
direction, genes, cytobands, mechanisms, therapeutic modalities, and validation
modalities. A deterministic 3D stress layout derives coordinates from those
distances. Coordinates and colored influence corridors are disposable browser
projection state.

The original frozen 600-iteration implementation failed its conjunctive method
criterion:

- Spearman semantic/map distance correlation: `0.7365686641` (required ≥ 0.80)
- Same-program nearest neighbors: `5/6`

Root-cause investigation reproduced incomplete convergence. The documented
exploratory product revision fixed the iteration count at 1,200 before changing
the application implementation. A fresh rerun produced:

- Spearman correlation: `0.8454848325`
- Mean within-program map distance: `514.6963`
- Mean between-program map distance: `797.0183`
- Same-program nearest neighbors: `6/6`
- Pairwise comparisons: `15/15` included

These values validate the revised product behavior on this fixed fixture. They
do not independently confirm the method, because the fixture was used during
the convergence investigation.

## Threats to validity

- Category weights are declared design choices, not learned biological effect
  sizes or expert-consensus ontologies.
- Three-dimensional embedding necessarily distorts some pairwise distances.
- The synthetic empires are not independent human analysts; the exercise tests
  collaboration mechanics and framing separation.
- Gene-level CNA values cannot resolve focality, purity, ploidy, allelic state,
  expression dosage, physical co-segregation, or drug response.
- TERT and RICTOR share chromosome 5p; their association may be one broad event.
- Every therapeutic hypothesis requires independent molecular and perturbational
  validation before promotion.

## Reproduction

From the repository root with the pinned environments installed:

```powershell
.\.venv\Scripts\python.exe scripts\simulate_stad_multiplayer.py --check
.\.venv\Scripts\python.exe scripts\simulate_stad_multiplayer.py --database data\live-test\evolastra.db --summary data\live-test\stad_cna_live_summary.json --output data\live-test\stad_multiplayer_simulation.json
.\apps\web\node_modules\.bin\vite-node.cmd apps\web\scripts\stadSemanticLayoutReport.ts data\live-test\stad_multiplayer_simulation.json
npm run check
```

The complete isolated release gate is `npm run verify`. The live local viewer is
served by the Evolastra companion; no analysis content is sent to Netlify.
