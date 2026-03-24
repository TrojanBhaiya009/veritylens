"""
VerityLens — Fact & Claim Verification System
FastAPI backend with SSE streaming for per-claim pipeline progress.
"""

import asyncio
import json
import logging
import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .core.url_parser import extract_text_from_url
from .core.claim_extractor import extract_claims
from .core.evidence_retriever import retrieve_evidence
from .core.verifier import verify_claim
from .core.ai_detector import detect_ai_text
from .core.media_detector import detect_ai_media
from .core.deepfake_detector import detect_deepfake
from .core.llm import validate_input
from .models.schemas import (
    AnalyzeRequest,
    EvidenceItem,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VerityLens API",
    description="Fact & Claim Verification System — RL-Enhanced LLM Engine, No API Keys Required",
    version="4.0.0",
)


def _parse_cors_origins() -> list[str]:
    """Parse comma-separated CORS_ORIGINS env var; fall back to local dev origins."""
    default_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    raw = os.getenv("CORS_ORIGINS", "")
    env_origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return env_origins or default_origins

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_origin_regex=os.getenv(
        "CORS_ORIGIN_REGEX",
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0.0", "engine": "VerityLens RL-Enhanced Engine (free, no API keys)"}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Full fact-checking pipeline with SSE streaming.
    Streams per-claim results as each claim is verified.
    """

    async def event_stream():
        try:
            # Step 1: Get input text
            source_type = "text"
            input_text = request.text.strip()
            article_title = ""

            if request.url and request.url.strip():
                source_type = "url"
                yield _sse_event("progress", {
                    "stage": "parsing",
                    "message": "Extracting article text from URL...",
                    "progress": 5,
                })
                try:
                    result = await extract_text_from_url(request.url.strip())
                    if isinstance(result, dict):
                        input_text = result.get("text", "")
                        article_title = result.get("title", "")
                    else:
                        input_text = result
                except Exception as e:
                    yield _sse_event("error", {"message": f"Failed to extract text from URL: {str(e)}"})
                    return

            if not input_text or len(input_text.strip()) < 3:
                yield _sse_event("error", {"message": "Please provide text or a valid URL."})
                return

            # Validate input is a proper sentence
            is_valid, validation_error = validate_input(input_text)
            if not is_valid:
                yield _sse_event("error", {"message": validation_error})
                return

            # Step 2: AI Detection
            yield _sse_event("progress", {
                "stage": "ai_detection",
                "message": "Analyzing text for AI-generation signals...",
                "progress": 10,
            })
            ai_result = detect_ai_text(input_text)
            yield _sse_event("ai_detection", ai_result)

            # Step 3: Extract claims
            yield _sse_event("progress", {
                "stage": "extracting",
                "message": "Extracting verifiable claims from text...",
                "progress": 20,
            })
            try:
                claims = await extract_claims(input_text)
            except Exception as e:
                yield _sse_event("error", {"message": f"Claim extraction failed: {str(e)}"})
                return

            # Prepend the article title as the first claim to verify (if URL mode)
            if article_title and source_type == "url":
                # Clean up the title (remove site name suffixes like "| Times of India")
                clean_title = article_title.split("|")[0].split(" - ")[0].strip()
                if clean_title and len(clean_title) > 10:
                    claims.insert(0, clean_title)

            total_claims = len(claims)
            yield _sse_event("claims_extracted", {
                "count": total_claims,
                "claims": claims,
                "progress": 25,
            })

            # Step 4+5: Per-claim evidence retrieval + verification (streamed)
            yield _sse_event("progress", {
                "stage": "verifying",
                "message": f"RL-enhanced verification of {total_claims} claims (debate + self-critique)...",
                "progress": 30,
            })

            all_claim_results = []

            for i, claim_text in enumerate(claims):
                claim_progress = 30 + int((i / total_claims) * 60)
                is_heading = (i == 0 and source_type == "url" and article_title)

                yield _sse_event("progress", {
                    "stage": "verifying",
                    "message": f"Verifying claim {i+1}/{total_claims}...",
                    "progress": claim_progress,
                    "current_claim": i,
                })

                # Retrieve evidence for this claim
                try:
                    evidence = await retrieve_evidence(claim_text)
                except Exception as e:
                    logger.error(f"Evidence retrieval failed for claim {i}: {e}")
                    evidence = []

                # Verify this claim
                try:
                    verification = await verify_claim(claim_text, evidence)
                except Exception as e:
                    logger.error(f"Verification failed for claim {i}: {e}")
                    verification = {
                        "verdict": "Unverifiable",
                        "confidence": 0,
                        "reasoning": f"Verification error: {str(e)}",
                    }

                # Calculate per-claim accuracy score
                verdict_scores = {"True": 100, "Partially True": 60, "False": 0, "Unverifiable": 40}
                accuracy_score = round(
                    verdict_scores.get(verification["verdict"], 40) * (verification["confidence"] / 100),
                    1
                )

                evidence_items = [
                    {
                        "title": e.get("title", ""),
                        "url": e.get("url", ""),
                        "snippet": e.get("snippet", ""),
                    }
                    for e in evidence
                ]

                claim_result = {
                    "claim": claim_text,
                    "verdict": verification["verdict"],
                    "confidence": verification["confidence"],
                    "reasoning": verification["reasoning"],
                    "evidence": evidence_items,
                    "accuracy_score": accuracy_score,
                    "is_heading": bool(is_heading),
                    "index": i,
                    "rl_method": verification.get("method", "nlp-fallback"),
                }

                all_claim_results.append(claim_result)

                # Stream this claim result immediately
                yield _sse_event("claim_result", claim_result)

                # Small delay between claims
                if i < total_claims - 1:
                    await asyncio.sleep(0.3)

            # Final complete signal
            yield _sse_event("progress", {
                "stage": "complete",
                "message": "Analysis complete!",
                "progress": 100,
            })

            yield _sse_event("done", {
                "total_claims": total_claims,
                "source_type": source_type,
                "input_text": input_text[:2000],
            })

        except Exception as e:
            logger.exception("Pipeline error")
            yield _sse_event("error", {"message": f"Unexpected error: {str(e)}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/analyze-media")
async def analyze_media(file: UploadFile = File(...)):
    """
    Analyze an uploaded image for AI-generation signals.
    Accepts JPEG, PNG, WebP images.
    """
    # Validate file type
    allowed_types = [
        "image/jpeg", "image/png", "image/webp",
        "image/jpg", "image/gif", "image/bmp",
    ]
    content_type = file.content_type or ""
    if content_type not in allowed_types:
        # Also check by extension
        ext = (file.filename or "").lower().split(".")[-1]
        if ext not in ("jpg", "jpeg", "png", "webp", "gif", "bmp"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. Please upload JPEG, PNG, or WebP images.",
            )

    # Read file (limit to 20MB)
    image_data = await file.read()
    if len(image_data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 20MB.")

    if len(image_data) < 100:
        raise HTTPException(status_code=400, detail="File is too small to analyze.")

    # Run both detections in parallel
    import asyncio
    ai_gen_result = detect_ai_media(image_data, filename=file.filename or "")
    deepfake_result = await detect_deepfake(image_data, filename=file.filename or "")

    return {
        "success": True,
        "filename": file.filename,
        **ai_gen_result,
        "deepfake": deepfake_result,
    }
