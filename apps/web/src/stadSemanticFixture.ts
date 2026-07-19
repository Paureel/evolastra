import type { SemanticSystem } from "./semanticLayout";
import type { SemanticSignature } from "./types";

const signature = (values: Partial<SemanticSignature> & Pick<SemanticSignature, "program" | "alterationDirection">): SemanticSignature => ({
  genes: [],
  cytobands: [],
  mechanisms: [],
  therapeuticModalities: [],
  validationModalities: [],
  ...values,
});

export const STAD_SEMANTIC_FIXTURE: SemanticSystem[] = [
  { id: "node_11111111111141118111111111111111", semanticSignature: signature({ program: "amplification-dependency", alterationDirection: "gain", genes: ["MYC"], cytobands: ["8q24.21"], mechanisms: ["replication-stress", "transcriptional-stress", "ATR"], therapeuticModalities: ["ATR-inhibition"], validationModalities: ["focality", "dosage", "CRISPR", "drug-response"] }) },
  { id: "node_2222222222224222a222222222222222", semanticSignature: signature({ program: "amplification-dependency", alterationDirection: "gain", genes: ["CCNE1"], cytobands: ["19q12"], mechanisms: ["replication-stress", "cell-cycle", "ATR"], therapeuticModalities: ["CDK2-inhibition", "PKMYT1-inhibition"], validationModalities: ["focality", "dosage", "CRISPR", "drug-response"] }) },
  { id: "node_3333333333334333b333333333333333", semanticSignature: signature({ program: "deletion-vulnerability", alterationDirection: "loss", genes: ["CDKN2A"], cytobands: ["9p21.3"], mechanisms: ["cell-cycle", "checkpoint-loss"], therapeuticModalities: ["checkpoint-dependency"], validationModalities: ["focality", "dosage", "restoration", "drug-response"] }) },
  { id: "node_44444444444444448444444444444444", semanticSignature: signature({ program: "deletion-vulnerability", alterationDirection: "loss", genes: ["ARID1A"], cytobands: ["1p36.11"], mechanisms: ["chromatin-remodeling", "synthetic-lethality"], therapeuticModalities: ["ATR-inhibition"], validationModalities: ["focality", "dosage", "restoration", "CRISPR"] }) },
  { id: "node_55555555555545559555555555555555", semanticSignature: signature({ program: "co-alteration-combination", alterationDirection: "co-gain", genes: ["ERBB2", "CCNE1"], cytobands: ["17q12", "19q12"], mechanisms: ["receptor-signaling", "cell-cycle", "combination-dependency"], therapeuticModalities: ["HER2-blockade", "CDK2-inhibition"], validationModalities: ["burden-adjustment", "dosage", "combination-response"] }) },
  { id: "node_6666666666664666a666666666666666", semanticSignature: signature({ program: "co-alteration-combination", alterationDirection: "co-gain", genes: ["TERT", "RICTOR"], cytobands: ["5p15.33", "5p13.1"], mechanisms: ["telomere-maintenance", "mTORC2-signaling", "combination-dependency"], therapeuticModalities: ["mTORC2-inhibition", "telomerase-strategy"], validationModalities: ["burden-adjustment", "dosage", "combination-response"] }) },
];
