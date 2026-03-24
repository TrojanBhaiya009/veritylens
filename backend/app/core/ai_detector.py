"""
AI-Generated Text Detector — statistical analysis approach.
No external API keys needed.

Analyzes text characteristics that differ between human and AI writing:
- Sentence length variance (AI tends to be uniform)
- Vocabulary richness (type-token ratio)
- Average word length patterns
- Punctuation diversity
- Burstiness (variation in sentence complexity)
"""

import re
import math
import logging

logger = logging.getLogger(__name__)


def _tokenize_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def _tokenize_words(text: str) -> list[str]:
    """Split text into words."""
    return re.findall(r'\b[a-zA-Z]+\b', text.lower())


def _sentence_length_variance(sentences: list[str]) -> float:
    """
    AI text tends to have more uniform sentence lengths.
    Returns normalized variance (0-1, lower = more AI-like).
    """
    if len(sentences) < 3:
        return 0.5

    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.5

    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    # Normalize: human text typically has CV > 0.4
    cv = math.sqrt(variance) / mean
    # Score: higher CV = more human-like
    return min(cv / 0.8, 1.0)


def _vocabulary_richness(words: list[str]) -> float:
    """
    Type-Token Ratio — AI tends to have lower diversity.
    Returns score (0-1, lower = more AI-like).
    """
    if len(words) < 20:
        return 0.5

    unique_words = set(words)
    ttr = len(unique_words) / len(words)

    # Hapax legomena ratio (words appearing only once)
    word_counts = {}
    for w in words:
        word_counts[w] = word_counts.get(w, 0) + 1
    hapax = sum(1 for c in word_counts.values() if c == 1)
    hapax_ratio = hapax / len(words)

    # Combine TTR and hapax ratio
    return min((ttr * 0.6 + hapax_ratio * 0.4) / 0.5, 1.0)


def _burstiness_score(sentences: list[str]) -> float:
    """
    Measures variation in sentence complexity.
    Human writing is 'burstier' — mixing short and long sentences.
    AI writing tends to be more consistent.
    """
    if len(sentences) < 4:
        return 0.5

    complexities = []
    for s in sentences:
        words = s.split()
        # Simple complexity: word count + comma count + long word count
        commas = s.count(',')
        long_words = sum(1 for w in words if len(w) > 6)
        complexity = len(words) + commas * 2 + long_words
        complexities.append(complexity)

    # Calculate consecutive differences
    diffs = [abs(complexities[i+1] - complexities[i]) for i in range(len(complexities)-1)]
    mean_diff = sum(diffs) / len(diffs) if diffs else 0
    mean_complexity = sum(complexities) / len(complexities) if complexities else 1

    # Normalize
    burstiness = mean_diff / mean_complexity if mean_complexity > 0 else 0
    return min(burstiness / 0.6, 1.0)


def _punctuation_diversity(text: str) -> float:
    """
    AI text often uses a narrower range of punctuation.
    """
    all_punct = re.findall(r'[^\w\s]', text)
    if len(all_punct) < 5:
        return 0.5

    unique_punct = set(all_punct)
    # Human text typically uses 5+ different punctuation marks
    return min(len(unique_punct) / 8, 1.0)


def detect_ai_text(text: str) -> dict:
    """
    Analyze text and return AI-generation probability.

    Returns:
        dict with:
        - ai_probability: float (0-100, higher = more likely AI)
        - confidence: float (0-100)
        - indicators: dict of individual metric scores
        - summary: str explanation
    """
    sentences = _tokenize_sentences(text)
    words = _tokenize_words(text)

    if len(words) < 30 or len(sentences) < 3:
        return {
            "ai_probability": 5.0,
            "confidence": 10.0,
            "indicators": {},
            "summary": "Text is too short for AI detection — insufficient data to analyze writing patterns. Not flagged as AI-generated.",
        }

    # Calculate metrics (higher = more human-like)
    sent_var = _sentence_length_variance(sentences)
    vocab = _vocabulary_richness(words)
    burst = _burstiness_score(sentences)
    punct = _punctuation_diversity(text)

    # Weighted human-likeness score
    human_score = (
        sent_var * 0.30
        + vocab * 0.25
        + burst * 0.30
        + punct * 0.15
    )

    # Convert to AI probability (invert human score)
    ai_probability = round((1 - human_score) * 100, 1)
    ai_probability = max(5, min(95, ai_probability))  # Clamp

    # Confidence based on text length
    length_factor = min(len(words) / 200, 1.0)
    confidence = round(40 + length_factor * 45, 1)

    indicators = {
        "sentence_uniformity": round((1 - sent_var) * 100, 1),
        "vocabulary_repetitiveness": round((1 - vocab) * 100, 1),
        "low_burstiness": round((1 - burst) * 100, 1),
        "punctuation_uniformity": round((1 - punct) * 100, 1),
    }

    # Generate summary
    high_indicators = [k for k, v in indicators.items() if v > 60]
    if ai_probability > 70:
        summary = f"Text shows strong AI-generation signals ({ai_probability}% probability). "
        if high_indicators:
            summary += f"Key indicators: {', '.join(h.replace('_', ' ') for h in high_indicators)}."
    elif ai_probability > 40:
        summary = f"Text shows mixed signals ({ai_probability}% AI probability). Could be human-written with AI assistance or heavily edited AI text."
    else:
        summary = f"Text appears likely human-written ({ai_probability}% AI probability). Shows natural writing patterns including varied sentence structure and vocabulary."

    return {
        "ai_probability": ai_probability,
        "confidence": confidence,
        "indicators": indicators,
        "summary": summary,
    }
