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


async def _search_web_ddgs(query: str, max_results: int = 6) -> list[dict]:
    """Search using the ddgs library (primary method)."""
    if DDGS is None:
        return []
    try:
        ddgs = DDGS()
        results = await asyncio.wait_for(
            asyncio.to_thread(ddgs.text, query, max_results=max_results),
            timeout=10.0
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
    except asyncio.TimeoutError:
        logger.warning(f"DDG library search timed out for '{query}'")
        return []
    except Exception as e:
        logger.warning(f"DDG library search failed for '{query}': {e}")
        return []


async def _search_web_httpx(query: str, max_results: int = 6) -> list[dict]:
    """Fallback: scrape DuckDuckGo HTML search directly via httpx."""
    import httpx
    from urllib.parse import quote_plus

    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        # Parse results from HTML
        results = []
        # DuckDuckGo HTML results have class="result__a" for titles and "result__snippet" for snippets
        title_pattern = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)

        titles = title_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i in range(min(len(titles), max_results)):
            raw_url = titles[i][0]
            # DDG wraps URLs in a redirect — extract the actual URL
            actual_url = raw_url
            uddg_match = re.search(r'uddg=([^&]+)', raw_url)
            if uddg_match:
                from urllib.parse import unquote
                actual_url = unquote(uddg_match.group(1))

            title_text = re.sub(r'<[^>]+>', '', titles[i][1]).strip()
            snippet_text = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""

            if snippet_text and actual_url:
                results.append({
                    "title": title_text,
                    "url": actual_url,
                    "snippet": snippet_text,
                })

        logger.info(f"httpx fallback search returned {len(results)} results for '{query[:50]}'")
        return results
    except Exception as e:
        logger.error(f"httpx fallback search failed for '{query}': {e}")
        return []


async def _search_web(query: str, max_results: int = 6) -> list[dict]:
    """Search the web — tries ddgs library first, falls back to httpx scraping."""
    # Try primary method
    results = await _search_web_ddgs(query, max_results)
    if results:
        return results

    # Fallback to httpx scraping
    return await _search_web_httpx(query, max_results)


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
