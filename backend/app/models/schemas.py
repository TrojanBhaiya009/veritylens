"""
Pydantic models for the VerityLens API.
"""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request body for the /api/analyze endpoint."""
    text: str = Field(default="", description="Plain text to analyze")
    url: str = Field(default="", description="URL of article to analyze")


class EvidenceItem(BaseModel):
    """A single piece of web evidence."""
    title: str
    url: str
    snippet: str


class ClaimResult(BaseModel):
    """Verification result for a single claim."""
    claim: str
    verdict: str  # True, False, Partially True, Unverifiable
    confidence: int  # 0-100
    reasoning: str
    evidence: list[EvidenceItem]


class AIDetectionResult(BaseModel):
    """Result of AI-generated text detection."""
    ai_probability: float
    confidence: float
    indicators: dict[str, float]
    summary: str


class AnalysisResponse(BaseModel):
    """Full analysis response."""
    success: bool
    input_text: str
    source_type: str  # "text" or "url"
    total_claims: int
    overall_score: float  # Overall accuracy score 0-100
    claims: list[ClaimResult]
    ai_detection: AIDetectionResult
    error: str = ""
