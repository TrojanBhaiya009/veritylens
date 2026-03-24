/**
 * TypeScript interfaces matching the backend API schemas.
 */

export interface EvidenceItem {
  title: string;
  url: string;
  snippet: string;
}

export interface ClaimResult {
  claim: string;
  verdict: 'True' | 'False' | 'Partially True' | 'Unverifiable';
  confidence: number;
  reasoning: string;
  evidence: EvidenceItem[];
  accuracy_score: number;
  is_heading: boolean;
  index: number;
}

export interface AIDetectionResult {
  ai_probability: number;
  confidence: number;
  indicators: Record<string, number>;
  summary: string;
}

export interface AnalysisResponse {
  success: boolean;
  input_text: string;
  source_type: 'text' | 'url';
  total_claims: number;
  overall_score: number;
  claims: ClaimResult[];
  ai_detection: AIDetectionResult;
  error?: string;
}

export interface ProgressEvent {
  stage: string;
  message: string;
  progress: number;
}

export type PipelineStage = 
  | 'idle'
  | 'parsing'
  | 'ai_detection'
  | 'extracting'
  | 'searching'
  | 'searching_done'
  | 'verifying'
  | 'complete'
  | 'error';
