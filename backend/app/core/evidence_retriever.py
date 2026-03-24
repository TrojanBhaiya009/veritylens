"""
Evidence Retriever — searches the web for evidence to verify claims.
Uses DuckDuckGo Search (free, no API key) with smart query generation.

Enhanced with:
- More results per query (6 instead of 4)
- Source diversity enforcement (evidence from 2+ domains)
- Relevance ranking before passing to verifier
"""

import asyncio
import logging
import re
from .llm import generate_queries_local

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger(__name__)


LOW_CRED_DOMAINS = [
    'facebook.com', 'twitter.com', 'x.com', 'reddit.com', 'quora.com',
    'instagram.com', 'tiktok.com', 'pinterest.com', 'blogspot.com',
    'wordpress.com', 'medium.com',
]

HIGH_CRED_DOMAINS = [
    'wikipedia.org', 'britannica.com', 'reuters.com', 'apnews.com',
    'bbc.com', 'bbc.co.uk', 'nature.com', 'science.org', 'nasa.gov',
    'who.int', 'snopes.com', 'factcheck.org', 'politifact.com',
]


def _generate_search_queries(claim: str) -> list[str]:
    """Generate search queries using fast NLP — no LLM round-trip needed."""
    return generate_queries_local(claim)


def _extract_domain(url: str) -> str:
    """Extract the base domain from a URL."""
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    return match.group(1).lower() if match else ""


def _relevance_score(claim: str, evidence: dict) -> float:
    """
    Quick relevance score for ranking evidence.
    Higher = more relevant to the claim.
    """
    claim_lower = claim.lower()
    claim_words = set(re.findall(r'\b\w+\b', claim_lower))
    claim_words -= {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'of', 'to', 'and', 'it'}

    snippet = (evidence.get('snippet', '') + ' ' + evidence.get('title', '')).lower()
    snippet_words = set(re.findall(r'\b\w+\b', snippet))

    if not claim_words:
        return 0.0

    overlap = len(claim_words & snippet_words) / len(claim_words)

    # Bonus for proper nouns matching
    proper_nouns = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim))
    for pn in proper_nouns:
        if pn.lower() in snippet:
            overlap += 0.15

    # Bonus for number matching
    claim_nums = set(re.findall(r'\b\d+\b', claim))
    snippet_nums = set(re.findall(r'\b\d+\b', snippet))
    if claim_nums and claim_nums & snippet_nums:
        overlap += 0.1

    # Credibility adjustment
    url = evidence.get('url', '').lower()
    if any(d in url for d in HIGH_CRED_DOMAINS):
        overlap += 0.1
    elif any(d in url for d in LOW_CRED_DOMAINS):
        overlap *= 0.45

    return min(overlap, 1.5)


async def _search_web(query: str, max_results: int = 6) -> list[dict]:
    """Search the web using DuckDuckGo."""
    if DDGS is None:
        logger.warning("ddgs package not installed; web evidence retrieval is disabled")
        return []

    try:
        ddgs = DDGS()
        results = await asyncio.to_thread(
            ddgs.text, query, max_results=max_results
        )
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", "")),
            }
            for r in results
            if r.get("body") or r.get("snippet")
        ]
    except Exception as e:
        logger.error(f"Web search failed for query '{query}': {e}")
        return []


async def retrieve_evidence(claim: str) -> list[dict]:
    """
    Retrieve web evidence for a single claim.

    Improvements over v1:
    - 6 results per query (up from 4)
    - De-duplicated by URL
    - Ranked by relevance score
    - Diversity enforced: caps at 3 results per domain
    """
    queries = _generate_search_queries(claim)
    all_evidence = []
    seen_urls = set()

    # Run search queries concurrently for this one claim
    search_tasks = [_search_web(q, max_results=6) for q in queries]
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    for results in search_results:
        if isinstance(results, Exception):
            continue
        for r in results:
            if r["url"] and r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_evidence.append(r)

    # --- Relevance ranking ---
    scored = [(e, _relevance_score(claim, e)) for e in all_evidence]
    scored.sort(key=lambda x: x[1], reverse=True)

    # --- Domain diversity: cap at 3 per domain ---
    domain_counts: dict[str, int] = {}
    diverse_evidence = []

    for e, score in scored:
        domain = _extract_domain(e.get("url", ""))
        count = domain_counts.get(domain, 0)
        if count < 3:
            diverse_evidence.append(e)
            domain_counts[domain] = count + 1

    # Prefer credible sources first; keep low-cred sources only as supplemental context.
    preferred = []
    low_cred_tail = []
    for e in diverse_evidence:
        domain = _extract_domain(e.get("url", ""))
        if any(d in domain for d in LOW_CRED_DOMAINS):
            low_cred_tail.append(e)
        else:
            preferred.append(e)

    # Cap low-cred evidence to avoid social-media-only verdicts.
    final_evidence = preferred[:8]
    if len(final_evidence) < 8:
        final_evidence.extend(low_cred_tail[: max(0, 8 - len(final_evidence))])

    return final_evidence[:8]
