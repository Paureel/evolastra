# Pre-registration: STAD multiplayer semantic-frontier method validation

**Frozen at commit:** `ce2bd292a9c1f49d5fb2bd5c37eadd7cbf1f3c48`
**Question doc:** `docs/science-superpowers/questions/2026-07-19-stad-multiplayer-semantic-frontiers.md`
**Analysis plan:** `docs/science-superpowers/plans/2026-07-19-stad-multiplayer-semantic-frontiers.md`

## Status and hypotheses

The biological hypotheses were generated after the STAD outcomes were inspected
and are permanently labeled exploratory. This registration covers only the
deterministic spatial method on the fixed six-signature fixture.

- H0: Rendered map distances do not preserve the declared semantic-distance ordering or empire-local neighborhoods.
- H1 (directional): Rendered map distance increases with semantic distance, and within-empire neighborhoods are closer than between-empire neighborhoods.

## Primary analysis (exact)

- Model/test: calculate all 15 pairwise weighted-Jaccard semantic distances and normalized 3D Euclidean map distances; calculate Spearman rank correlation using average ranks for ties.
- Variables: the six signatures fixed below; category weights and coordinate optimizer are fixed in the linked plan.
- Transformations: map Euclidean distances are divided by the maximum observed pair distance; no pairs are excluded.
- Covariates: none; this is deterministic method validation, not biological estimation.

Fixed systems:

1. Amplification Dominion: MYC–ATR transcription/replication stress.
2. Amplification Dominion: CCNE1–CDK2/PKMYT1 replication stress.
3. Loss Cartographers: CDKN2A loss and cell-cycle checkpoint vulnerability.
4. Loss Cartographers: ARID1A loss and chromatin synthetic lethality.
5. Constellation Pact: ERBB2–CCNE1 co-amplification dual blockade.
6. Constellation Pact: TERT–RICTOR co-amplification combination dependency.

## Prediction and decision rule

- Direction: positive semantic/map distance correlation.
- Confirm the method contract only if Spearman rho ≥ 0.80, mean within-empire map distance < mean between-empire map distance, and all six nearest map neighbors share the focal system's empire.
- Disconfirm the contract if any one of those three criteria fails.

## Sample size and stopping

- N is fixed at six systems and 15 pairs. This is exhaustive deterministic fixture validation; no p-value, confidence interval, optional stopping, or power claim is used.
- Exactly 600 optimizer iterations and seed 874049 are used. No rerunning with alternate seeds to select a better result.

## Multiplicity

- The three spatial criteria form one conjunctive contract: all must pass. No criterion is selected after execution.

## Secondary and exploratory

- Biological recurrence, dependency, and therapeutic interpretations remain exploratory regardless of spatial-method performance.
- Browser aesthetics and individual pair distances are descriptive only.

## Planned deviations handling

Any change to signatures, weights, optimizer, seed, iterations, or thresholds after
execution is documented and renders the affected validation exploratory until a
new fixture is frozen.
