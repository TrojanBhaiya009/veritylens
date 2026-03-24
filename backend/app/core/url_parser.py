"""
URL article parser — extracts clean text from web pages.
Uses httpx + BeautifulSoup with multiple strategies.
"""

import logging
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Common browser user agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def extract_text_from_url(url: str) -> dict:
    """Extract the main article text and title from a URL. Returns {title, text}."""

    # Strategy 1: Try newspaper3k / newspaper4k
    try:
        try:
            # newspaper4k (newer fork)
            from newspaper import Article
            article = Article(url)
            article.download()
            article.parse()
            if article.text and len(article.text) > 100:
                logger.info(f"newspaper extracted {len(article.text)} chars from {url}")
                return {"title": getattr(article, 'title', '') or '', "text": article.text}
        except ImportError:
            pass

        try:
            # newspaper3k style
            import newspaper
            art = newspaper.article(url)
            if art.text and len(art.text) > 100:
                logger.info(f"newspaper.article extracted {len(art.text)} chars from {url}")
                return {"title": getattr(art, 'title', '') or '', "text": art.text}
        except (ImportError, AttributeError, Exception) as e:
            logger.warning(f"newspaper failed: {e}")
    except Exception as e:
        logger.warning(f"newspaper methods all failed for {url}: {e}")

    # Strategy 2: Direct fetch with BeautifulSoup
    html_text = None
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            verify=False,  # Some sites have SSL issues
        ) as client:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html_text = resp.text
    except Exception as e:
        logger.error(f"httpx fetch failed for {url}: {e}")

    # If direct fetch failed, try with a different approach
    if not html_text:
        try:
            async with httpx.AsyncClient(
                timeout=20,
                follow_redirects=True,
                verify=False,
            ) as client:
                # Try with minimal headers (some sites block complex UA strings)
                resp = await client.get(url, headers={"User-Agent": "curl/8.0"})
                resp.raise_for_status()
                html_text = resp.text
        except Exception as e:
            logger.error(f"httpx fallback fetch also failed for {url}: {e}")

    if not html_text:
        raise ValueError(f"Could not fetch content from URL: {url}")

    # Parse HTML
    soup = BeautifulSoup(html_text, "html.parser")

    # Extract title before removing tags
    page_title = ""
    title_tag = soup.find("title")
    if title_tag:
        page_title = title_tag.get_text(strip=True)
    if not page_title:
        h1_tag = soup.find("h1")
        if h1_tag:
            page_title = h1_tag.get_text(strip=True)

    # Remove unwanted tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                     "iframe", "noscript", "svg", "form", "button"]):
        tag.decompose()

    # Remove elements commonly used for ads, sidebars, etc.
    for selector in [
        '[class*="sidebar"]', '[class*="ad-"]', '[class*="advertisement"]',
        '[class*="social"]', '[class*="share"]', '[class*="comment"]',
        '[class*="related"]', '[class*="recommendation"]',
        '[id*="sidebar"]', '[id*="ad-"]', '[id*="comment"]',
    ]:
        for el in soup.select(selector):
            el.decompose()

    text = ""

    # Strategy 2a: Try <article> tag
    article_el = soup.find("article")
    if article_el:
        text = article_el.get_text(separator="\n", strip=True)

    # Strategy 2b: Try role="main" or <main>
    if len(text) < 100:
        main_el = soup.find("main") or soup.find(attrs={"role": "main"})
        if main_el:
            text = main_el.get_text(separator="\n", strip=True)

    # Strategy 2c: Try common article class patterns
    if len(text) < 100:
        for class_pattern in ["article-body", "article-content", "story-body",
                               "post-content", "entry-content", "content-body",
                               "article__body", "story-content"]:
            el = soup.find(class_=lambda c: c and class_pattern in str(c).lower())
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    break

    # Strategy 2d: Collect all <p> tags (most universal)
    if len(text) < 100:
        paragraphs = soup.find_all("p")
        good_paragraphs = []
        for p in paragraphs:
            p_text = p.get_text(strip=True)
            # Only include substantial paragraphs
            if len(p_text) > 25:
                good_paragraphs.append(p_text)
        text = "\n".join(good_paragraphs)

    # Strategy 2e: Last resort — body text
    if len(text) < 50:
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            # Trim excessive whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)

    if text and len(text) > 50:
        # Truncate if extremely long
        if len(text) > 15000:
            text = text[:15000]
        logger.info(f"Extracted {len(text)} chars from {url}")
        return {"title": page_title, "text": text}

    raise ValueError(f"Could not extract meaningful text from URL: {url}")
