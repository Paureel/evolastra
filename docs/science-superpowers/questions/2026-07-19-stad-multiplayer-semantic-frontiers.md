# Three-empire semantic exploration of STAD copy-number alterations

**Research question:** Can the previously inspected TCGA-STAD copy-number landscape be organized into three mechanistically distinct, experimentally falsifiable research programs—amplification dependencies, deletion/collateral-loss vulnerabilities, and co-alteration combination strategies—such that spatial distance between claimed systems monotonically reflects a declared semantic distance rather than decorative map placement?

**Background / motivation:** Evolastra multiplayer should let collaborators explore one project from different angles while preserving scientific meaning. This simulation tests that interaction model on the existing STAD CNA analysis. Because the dataset and its earlier summaries have already been inspected, this is an exploratory hypothesis-generation and interface-validation exercise, not a preregistered confirmatory discovery analysis.

**Hypotheses:**

- H0 (scientific): The three programs do not yield hypotheses distinguishable by alteration direction, nominated mechanism, or validation strategy beyond arbitrary relabeling.
- H1 (scientific): Each program yields at least two directional, falsifiable hypotheses whose defining genes, alteration direction, proposed vulnerability, and required validation differ from the other programs.
- H0 (spatial): Pairwise map distances between claimed systems do not preserve their declared semantic-distance ordering.
- H1 (spatial): Systems sharing alteration direction, mechanism, gene/cytoband, or validation modality are placed closer than systems with no declared semantic overlap; deliberately orthogonal programs occupy separated frontier sectors.

**Population & unit of analysis:** The biological population is the 438 TCGA-STAD tumors represented in `stad_data/data_log2_cna.txt`. The observational unit remains a tumor-by-gene CNA value. The multiplayer simulation unit is a claimed hypothesis system: one bounded research direction assigned to one empire and linked to its source evidence.

**Key variables (operationalized):**

- Amplification program (gold): recurrent gain or high-level gain of an oncogene or dosage-sensitive pathway, paired with a predicted dependency and a CNA-matched perturbation experiment.
- Deletion program (cyan): recurrent loss or deep loss of a tumor suppressor or neighboring essential gene, paired with a restoration, synthetic-lethal, or collateral-vulnerability experiment.
- Co-alteration program (purple): a statistically evaluated pair or module of alterations, paired with a combination-treatment prediction and a test separating biological cooperation from physical co-segregation or global CNA burden.
- Semantic signature: normalized alteration direction, genes, cytobands, mechanisms/pathways, therapeutic modality, and validation modality recorded for each hypothesis system.
- Semantic distance: a deterministic weighted dissimilarity over semantic signatures. Shared genes/cytobands and mechanisms contribute the strongest proximity; shared alteration direction and validation modality contribute weaker proximity; no overlap or opposing mechanisms produce larger distance.
- Map distance: normalized 3D Euclidean distance between deterministic rendered system coordinates.
- Territory: a multiplayer claim linking one empire identity and color to a semantic hypothesis system. It remains an overlay and does not rewrite canonical scientific events.

**What counts as an answer:** The simulation succeeds if three distinct empire identities are visible, each owns at least two hypothesis systems, all systems contain a falsifiable prediction and validation requirement, and every tested semantic-distance ordering is preserved spatially: close-related pairs are nearer than deliberately orthogonal pairs. Exact coordinates are disposable, but repeated rendering from the same run seed and semantic signatures must be deterministic. A scientific program fails if its hypotheses merely restate another program or cannot be falsified with a named comparison.

**Scope & exclusions:** This exercise demonstrates exploratory collaboration and semantic geography. It does not infer causality, treatment response, survival benefit, or clinical utility from CNA data alone. It does not represent actual independent human players, transmit raw project data, or make novelty claims. No map position becomes canonical analytical evidence. External expression, dependency, pharmacology, and independent-cohort validation remain required before biological promotion.

**Open questions for prior-work survey:** Which lightweight semantic-distance formulation is most interpretable for a deterministic browser map; how to distinguish same-arm physical co-gain from functional co-dependency; which collateral-loss and synthetic-lethal mechanisms are independently supported in gastric cancer; and which validation modalities best separate dosage effects from passenger CNAs.
