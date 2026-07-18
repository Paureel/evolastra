# Recurrent focal CNA drivers and therapeutic vulnerabilities in TCGA-STAD

**Research question:** In the 438 TCGA-STAD tumor samples represented in `stad_data/data_log2_cna.txt`, which gene-containing genomic intervals show recurrent focal copy-number gains or losses beyond broad chromosome-arm and sample-level aneuploidy background, and which interval-resident genes support testable therapeutic-vulnerability hypotheses after independent biological annotation?

**Background / motivation:** Recurrent focal copy-number alterations can mark positively selected oncogenes, tumor suppressors, and collateral dependencies. The purpose is to produce a short, evidence-ranked set of gastric-cancer hypotheses suitable for experimental validation, not to infer causality or clinical benefit from copy-number data alone.

**Hypotheses:**
- H0 (null): Once broad chromosome-arm shifts, sample-specific CNA burden, locus coverage, and multiple testing are accounted for, no genomic interval has focal alteration recurrence greater than expected under a burden-preserving null model.
- H1 (primary): At least one genomic interval has amplification or deletion recurrence, amplitude, and focality greater than expected under the burden-preserving null model and remains robust to reasonable event thresholds and leave-subset-out sensitivity checks.
- H2 (translation): For at least one robust focal interval, an interval-resident or mechanistically linked gene has independent cancer-driver, perturbational-dependency, or druggability evidence that yields a directional, experimentally falsifiable therapeutic-vulnerability hypothesis.

**Population & unit of analysis:** The population is the TCGA stomach adenocarcinoma cohort represented by the file. The primary observational unit is a tumor sample for event recurrence; the tested feature is a gene locus, consolidated into cytoband/genomic intervals where possible. Results apply to this cohort and require independent-cohort validation before generalization.

**Key variables (operationalized):**
- CNA value: gene-level log2 copy-number value for each tumor from the input matrix.
- Focal event: a contiguous, same-direction gain or loss affecting substantially less than a chromosome arm; exact segmentation proxy and width rules will be fixed in the analysis plan before values are examined.
- Event amplitude: absolute log2 CNA magnitude, evaluated at pre-specified primary and sensitivity thresholds.
- Recurrence: fraction of eligible tumors carrying a concordant event at a locus or consolidated interval.
- Broad-event background: chromosome-arm/cytoband-level shift estimated within each tumor and removed or modeled before focal-event scoring.
- Sample CNA burden: fraction and magnitude of the assayed genome altered in each tumor, preserved or conditioned on in null simulations.
- Driver priority: a pre-specified composite of statistical recurrence, focality, amplitude, robustness, and independent biological evidence; external evidence will not change the primary CNA significance calculation.
- Therapeutic-vulnerability hypothesis: a directional prediction linking a CNA-defined subgroup to sensitivity to perturbing a nominated target or pathway, supported by an independent dependency or pharmacology source and stated with a falsifying experiment.

**What counts as an answer:** A confirmatory discovery requires at least one interval that passes the pre-specified false-discovery criterion under a burden-aware null, is stable across threshold and resampling analyses, and is not explainable solely by a broad arm-level event. A therapeutic nomination additionally requires independent target/dependency evidence and a concrete validation experiment. If no interval satisfies these criteria, the answer is that this dataset does not support a robust focal-driver discovery under the chosen design.

**Scope & exclusions:** This is an association and prioritization study. It does not establish causality, treatment efficacy, patient prognosis, or a Nobel-level discovery. Clinical-outcome modeling, expression-mediated dosage effects, mutation integration, and wet-lab validation are outside the primary analysis unless suitable external datasets are added explicitly. Previously known loci will be labeled as rediscoveries; novelty claims require a documented literature search.

**Open questions for prior-work survey:** Which focal CNA methods are defensible for gene-level rather than segmented data; which TCGA-STAD CNA peaks are already established; which chromosome-arm definitions and centromere mappings should be used; and which dependency/drug sources can independently test nominated vulnerabilities.
