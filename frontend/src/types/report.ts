export type ClaimVerdict = "True" | "False" | "Partially True" | "Unverifiable";

export interface SourceEvidence {
  title: string;
  url: string;
  snippet: string;
  relevance_score: number;
}

export interface ClaimResult {
  claim: string;
  verdict: ClaimVerdict;
  confidence: number;
  rationale: string;
  evidence: SourceEvidence[];
}

export interface AccuracyReport {
  overall_accuracy: number;
  summary: string;
  claim_count: number;
  claims: ClaimResult[];
  conflicting_claims: string[];
  ai_generated_probability: number;
}

export interface VerifyResponse {
  input_preview: string;
  extracted_claims: string[];
  report: AccuracyReport;
}
