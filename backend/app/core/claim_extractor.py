"""
Claim Extractor — decomposes text into discrete verifiable statements.
Uses LLM when available, falls back to NLP heuristics.
"""

import json
import logging
import re
from .llm import ask_llm, extract_claims_local

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a multilingual fact-checking assistant. Extract discrete, specific, verifiable factual claims from the following text.

The text may be in English, Hindi (Devanagari script), or Hinglish (Hindi written in Latin script). You MUST handle all three languages.

Use Chain of Thought reasoning:

**Step 1 — Read the text** and identify all statements that make factual assertions (in any language).
**Step 2 — Filter** out opinions, subjective statements, vague generalizations, and questions.
**Step 3 — Atomize** compound statements into individual, standalone claims.
**Step 4 — Verify extractability** — each claim must be independently verifiable against real-world data. Remove claims that are too vague.
**Step 5 — Translate if needed** — If the claim is in Hindi or Hinglish, provide the claim in ENGLISH for searchability. Keep the meaning exact.
**Step 6 — Self-check** — review your list. Did you miss any important facts? Did you accidentally include any opinions?

Rules:
- Extract ONLY factual claims that can be verified against real-world data
- Each claim should be a single, atomic statement
- Output all claims in ENGLISH (translate Hindi/Hinglish claims to English)
- Preserve the original meaning and context exactly
- For temporal claims (e.g., "the current CEO"), include the time reference
- Return between 3 and 15 claims maximum

TEXT:
\"\"\"{text}\"\"\"

Return ONLY a JSON array of strings:
["claim 1 in English", "claim 2 in English", ...]"""


async def extract_claims(text: str) -> list[str]:
    """Extract verifiable claims from input text."""
    # Truncate very long texts
    if len(text) > 6000:
        text = text[:6000] + "..."

    # Try LLM first
    try:
        prompt = EXTRACTION_PROMPT.format(text=text)
        response = await ask_llm(prompt)

        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            claims = json.loads(match.group())
            if isinstance(claims, list) and all(isinstance(c, str) for c in claims):
                result = [c.strip() for c in claims if c.strip() and len(c.strip()) > 10]
                if result:
                    logger.info(f"Extracted {len(result)} claims via LLM")
                    return result[:15]
    except Exception as e:
        logger.info(f"LLM extraction unavailable ({e}), using NLP fallback")

    # Fallback to NLP-based extraction
    claims = extract_claims_local(text)
    if claims:
        logger.info(f"Extracted {len(claims)} claims via NLP")
        return claims

    raise ValueError("Could not extract any verifiable claims from the text")
