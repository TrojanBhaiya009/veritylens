"""
LLM wrapper — multi-provider with automatic fallback.
Priority chain:
  1. User-configured provider (OpenAI, Anthropic, Google, OpenRouter, Custom)
  2. DuckDuckGo Chat (free, multi-model fallback)
  3. Local NLP-based processing (always available, enhanced)

No external API keys required by default.
"""

import asyncio
import json
import logging
import math
import os
import re
import time
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# Multi-provider config (set by main.py per request)
# ============================================================

_llm_config = {
    'provider': 'duckduckgo',  # default
    'api_key': None,
    'base_url': None,
    'model': None,
}


def set_llm_config(provider: str = 'duckduckgo', api_key: Optional[str] = None,
                    base_url: Optional[str] = None, model: Optional[str] = None):
    """Set the LLM provider configuration for subsequent calls."""
    global _llm_config
    _llm_config = {
        'provider': provider,
        'api_key': api_key,
        'base_url': base_url,
        'model': model,
    }
    logger.info(f"LLM config set: provider={provider}, model={model}")


def get_llm_config() -> dict:
    """Get current LLM configuration."""
    return _llm_config.copy()


# ============================================================
# DuckDuckGo Chat — multi-model fallback
# ============================================================

_ddg_chat_available = True
_ddg_disabled_until = 0  # timestamp when to re-enable after failures

# Models to try in order - if one fails, fall back to next
_DDG_MODELS = [
    "gpt-4o-mini",
    "claude-3-haiku",
    "mixtral-8x7b",
    "llama-3.1-70b",
]


async def _try_ddg_chat(prompt: str, max_retries: int = 2) -> str | None:
    """
    Try DuckDuckGo chat with multi-model fallback.
    Tries each model with retries before moving to the next.
    """
    global _ddg_chat_available, _ddg_disabled_until

    if not _ddg_chat_available:
        return None

    # Check if temporarily disabled
    if time.time() < _ddg_disabled_until:
        return None

    try:
        from ddgs import DDGS
    except ImportError:
        _ddg_chat_available = False
        logger.warning("duckduckgo_search not installed - DDG Chat disabled")
        return None

    for model in _DDG_MODELS:
        for attempt in range(max_retries):
            try:
                ddgs = DDGS()
                if not hasattr(ddgs, "chat"):
                    _ddg_chat_available = False
                    return None

                # Strict 15-second timeout per call - prevents hanging on Render
                result = await asyncio.wait_for(
                    asyncio.to_thread(ddgs.chat, prompt, model=model),
                    timeout=15.0
                )
                if result and len(result.strip()) > 5:
                    logger.info(f"DDG Chat response via {model} (attempt {attempt+1})")
                    return result.strip()
            except asyncio.TimeoutError:
                logger.warning(f"DDG {model} attempt {attempt+1} timed out (15s)")
                break  # skip remaining retries for this model
            except Exception as e:
                err_str = str(e).lower()
                if any(kw in err_str for kw in ["rate", "limit", "429", "too many"]):
                    _ddg_disabled_until = time.time() + 10
                    logger.warning(f"DDG {model} rate limited, trying next model")
                    break
                else:
                    logger.warning(f"DDG {model} attempt {attempt+1} failed: {e}")
                    await asyncio.sleep(0.5 * (attempt + 1))

    # All models failed - disable temporarily (shorter cooldown for faster recovery)
    _ddg_disabled_until = time.time() + 15
    logger.warning("All DDG Chat models failed - falling back to NLP")
    return None


# ============================================================
# Main ask_llm
# ============================================================

async def ask_llm(prompt: str, max_retries: int = 2) -> str:
    """
    Try user-configured LLM first, then DuckDuckGo Chat.
    If both unavailable, raises RuntimeError so callers use NLP fallback.
    """
    config = get_llm_config()
    
    # Try user-configured provider first (if not duckduckgo)
    if config['provider'] != 'duckduckgo':
        try:
            from .llm_multi import ask_llm as ask_llm_multi
            result = await ask_llm_multi(
                prompt,
                provider=config['provider'],
                api_key=config['api_key'],
                base_url=config['base_url'],
                model=config['model'],
                max_retries=max_retries
            )
            if result:
                return result
        except Exception as e:
            logger.warning(f"Configured provider '{config['provider']}' failed: {e}")
            logger.info("Falling back to DuckDuckGo Chat...")
    
    # Fallback to DuckDuckGo Chat
    result = await _try_ddg_chat(prompt, max_retries=max_retries)
    if result:
        return result
    
    raise RuntimeError("No LLM available — use NLP fallback pipeline")


# ============================================================
# Language Detection & Hindi Support
# ============================================================

# Hindi ↔ English keyword dictionary for search query translation
_HINDI_TO_ENGLISH = {
    # Countries & places
    'भारत': 'India', 'पाकिस्तान': 'Pakistan', 'चीन': 'China',
    'अमेरिका': 'America', 'रूस': 'Russia', 'जापान': 'Japan',
    'दिल्ली': 'Delhi', 'मुंबई': 'Mumbai', 'कोलकाता': 'Kolkata',
    'चेन्नई': 'Chennai', 'बेंगलुरु': 'Bangalore',
    'लंदन': 'London', 'न्यूयॉर्क': 'New York',
        # Titles & roles
        'प्रधानमंत्री': 'Prime Minister', 'राष्ट्रपति': 'President',
        'मुख्यमंत्री': 'Chief Minister', 'राजा': 'King', 'रानी': 'Queen',
        'सम्राट': 'Emperor', 'नेता': 'leader', 'अध्यक्ष': 'chairman',
    'मंत्री': 'minister', 'सेनापति': 'general',
    # Common subjects
    'पृथ्वी': 'Earth', 'सूर्य': 'Sun', 'चंद्रमा': 'Moon',
    'पानी': 'water', 'आग': 'fire', 'हवा': 'air',
    'नदी': 'river', 'पर्वत': 'mountain', 'समुद्र': 'ocean',
    'जनसंख्या': 'population', 'राजधानी': 'capital',
    'स्वतंत्रता': 'independence', 'आज़ादी': 'independence',
    'संविधान': 'constitution', 'कानून': 'law',
    'युद्ध': 'war', 'शांति': 'peace', 'इतिहास': 'history',
    'विज्ञान': 'science', 'गणित': 'mathematics',
    # People (common in claims)
    'नरेंद्र': 'Narendra', 'मोदी': 'Modi', 'गांधी': 'Gandhi',
    'नेहरू': 'Nehru', 'अंबेडकर': 'Ambedkar', 'सुभाष': 'Subhash',
    'बोस': 'Bose', 'टैगोर': 'Tagore', 'रवींद्रनाथ': 'Rabindranath',
    # Verbs / connectors (strip from search, keep for context)
    'है': '', 'हैं': '', 'था': '', 'थे': '', 'थी': '',
    'हुआ': '', 'हुई': '', 'हुए': '', 'गया': '', 'गई': '', 'गए': '',
    'के': 'of', 'का': 'of', 'की': 'of', 'में': 'in', 'पर': 'on',
    'से': 'from', 'को': 'to', 'ने': '', 'और': 'and',
    # Numbers
    'एक': '1', 'दो': '2', 'तीन': '3', 'चार': '4', 'पांच': '5',
    'छह': '6', 'सात': '7', 'आठ': '8', 'नौ': '9', 'दस': '10',
    'सौ': '100', 'हज़ार': '1000', 'लाख': '100000',
    'करोड़': '10000000', 'अरब': '1000000000',
    'प्रतिशत': 'percent', 'किलोमीटर': 'kilometers',
}

# Hinglish stop words (for query generation)
_HINGLISH_STOP_WORDS = {
    'hai', 'hain', 'tha', 'the', 'thi', 'ho', 'hota', 'hoti', 'hote',
    'ka', 'ki', 'ke', 'ko', 'se', 'me', 'mein', 'par', 'pe',
    'ne', 'aur', 'ya', 'lekin', 'magar', 'agar', 'to', 'toh',
    'ye', 'yeh', 'woh', 'wo', 'kya', 'kaise', 'kab', 'kahan',
    'kyun', 'kyunki', 'isliye', 'iske', 'uske', 'jaise',
    'bahut', 'bohot', 'ek', 'do', 'nahi', 'nhi', 'nahin', 'mat',
}


def _detect_language(text: str) -> str:
    """
    Detect input language.
    Returns: 'hindi' (Devanagari), 'hinglish' (Latin + Hindi loan words), or 'english'.
    """
    text = text.strip()
    # Count Devanagari characters (Unicode range U+0900-U+097F)
    devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    total_alpha = devanagari_chars + latin_chars

    if total_alpha == 0:
        return 'english'

    # If >40% Devanagari characters, it's Hindi
    if devanagari_chars / max(total_alpha, 1) > 0.4:
        return 'hindi'

    # Check for Hinglish markers (Hindi words written in Latin script)
    hinglish_markers = [
        r'\b(?:hai|hain|tha|thi|the|hoga|hogi|nahi|nhi|kya|kaun|kaise|kab)\b',
        r'\b(?:karta|karti|karte|kiya|kiye|karna|karenge|karega)\b',
        r'\b(?:wala|wali|wale|mein|ke|ki|ka|ko|se|par|pe|aur)\b',
        r'\b(?:bohot|bahut|accha|achha|theek|sahi|galat|sachchi|jhootha)\b',
        r'\b(?:pradhan\s*mantri|mukhya\s*mantri|rashtrapati)\b',
        r'\b(?:desh|duniya|log|aadmi|paisa|kaam|ghar)\b',
    ]
    hinglish_count = sum(len(re.findall(p, text, re.I)) for p in hinglish_markers)
    if hinglish_count >= 2:
        return 'hinglish'

    return 'english'


def _translate_hindi_to_english_keywords(text: str) -> str:
    """
    Translate Hindi (Devanagari) text to English keywords for web search.
    Not a full translation - just keyword extraction and mapping.
    """
    words = re.findall(r'[\u0900-\u097F]+', text)
    english_parts = []
    for w in words:
        eng = _HINDI_TO_ENGLISH.get(w, '')
        if eng:
            english_parts.append(eng)
    # Also extract any Latin words already in the text
    latin_words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    english_parts.extend(latin_words)
    # Extract numbers
    numbers = re.findall(r'\b\d+\b', text)
    english_parts.extend(numbers)
    return ' '.join(english_parts)


# ============================================================
# Input Validation
# ============================================================

def _is_valid_sentence(text: str) -> bool:
    """
    Check if input text contains at least one verifiable sentence.
    Supports English, Hindi (Devanagari), and Hinglish.
    """
    text = text.strip()

    # Too short or empty
    if len(text) < 3:
        return False

    lang = _detect_language(text)

    # Count words based on language
    latin_words = re.findall(r'\b[a-zA-Z]+\b', text)
    hindi_words = re.findall(r'[\u0900-\u097F]+', text)
    total_words = len(latin_words) + len(hindi_words)

    # Need at least 2 words for Hindi, 3 for English/Hinglish
    if lang == 'hindi':
        if len(hindi_words) < 2:
            return False
    else:
        if total_words < 3:
            return False

    # Hindi verb patterns (Devanagari)
    hindi_verb_patterns = [
        r'(?:है|हैं|था|थे|थी|थीं)',  # is/are/was/were
        r'(?:होगा|होगी|होंगे|होंगी)',  # will be
        r'(?:हुआ|हुई|हुए)',  # happened/became
        r'(?:गया|गई|गए|जाता|जाती|जाते)',  # went/goes
        r'(?:आया|आई|आए|आता|आती|आते)',  # came/comes
        r'(?:किया|की|किए|करता|करती|करते|करेगा|करेगी)',  # did/does/will do
        r'(?:दिया|दी|दिए|देता|देती|देते)',  # gave/gives
        r'(?:लिया|ली|लिए|लेता|लेती|लेते)',  # took/takes
        r'(?:बना|बनी|बनाया|बनाई|बनाए)',  # made/created
        r'(?:मिला|मिली|मिले|मिलता|मिलती)',  # found/gets
        r'(?:जीता|जीती|हारा|हारी|मारा|मारी)',  # won/lost/killed
        r'(?:लिखा|लिखी|पढ़ा|पढ़ी)',  # wrote/read
        r'(?:कहा|कही|बोला|बोली)',  # said/spoke
        r'(?:रहता|रहती|रहते|रहा|रही|रहे)',  # lives/stayed
        r'(?:सकता|सकती|सकते|चाहिए)',  # can/should
        r'(?:पैदा|जन्म|मृत्यु|स्थित|स्थापित)',  # born/death/located/established
        r'(?:नहीं|नही|क्या|कौन|कैसे|कब|कहाँ|क्यों)',  # negation/question words
    ]

    # English + Hinglish verb patterns
    english_verb_patterns = [
        r'\b(?:is|are|was|were|has|have|had|does|do|did)\b',
        r'\b(?:can|could|will|would|shall|should|may|might|must)\b',
        r'\b\w+(?:ed|es|ing|tion|sion)\b',
        r'\b(?:the|a|an)\b.*\b(?:is|are|was|were)\b',
        r'\b(?:founded|discovered|invented|created|built|established)\b',
        r'\b(?:located|situated|found|born|died|won|lost)\b',
        r'\b(?:became|turned|changed|made|wrote|published)\b',
        r'\b(?:contains?|includes?|consists?|comprises?)\b',
        r'\b(?:orbits?|rotates?|revolves?|boils?|freezes?|melts?)\b',
        r'\b(?:causes?|prevents?|cures?|treats?|affects?)\b',
        r'\b(?:gained|achieved|earned|received|belongs?)\b',
        r'\b(?:runs?|works?|operates?|functions?|produces?)\b',
        # Hinglish verb patterns
        r'\b(?:hai|hain|tha|thi|the|thi[nm]?)\b',
        r'\b(?:hoga|hogi|honge|hogi[nm]?)\b',
        r'\b(?:karta|karti|karte|kiya|kiye|ki|karna|karenge|karega|karegi)\b',
        r'\b(?:bola|boli|bole|bolna|bolta|bolti|bolte|kaha|kahi|kahe|kehna|kehta|kehti)\b',
        r'\b(?:gaya|gayi|gaye|jana|jaata|jaati|jaate|jaayega|jaayegi|jayega|jayegi)\b',
        r'\b(?:aaya|aayi|aaye|aana|aata|aati|aate|aayega|aayegi)\b',
        r'\b(?:diya|diye|dena|deta|deti|dete|dega|degi)\b',
        r'\b(?:liya|liye|lena|leta|leti|lete|lega|legi)\b',
        r'\b(?:raha|rahi|rahe|rehna|rehta|rehti|rehte)\b',
        r'\b(?:bana|bani|banaya|banayi|banaye|banta|banti|bante)\b',
        r'\b(?:mara|mari|marna|maarta|maarti|maarte)\b',
        r'\b(?:jeeta|jeeti|jeete|jeetna|haara|haari|haare|haarna)\b',
        r'\b(?:paida|hua|hui|hue|hona|hota|hoti|hote)\b',
        r'\b(?:likha|likhi|likhe|likhna|likhta|likhti|likhte)\b',
        r'\b(?:padha|padhi|padhe|padhna|padhta|padhti|padhte)\b',
        r'\b(?:nahi|nhi|nahin|mat|kya|kaun|kaise|kab|kaha[an]?|kyun|kyu[nm]?)\b',
        r'\b(?:sakta|sakti|sakte|saka|saki|sake|chahiye|chahte|chahta|chahti)\b',
        r'\b(?:milta|milti|milte|mila|mili|mile|milna|milega|milegi)\b',
    ]

    # Check for verbs based on detected language
    if lang == 'hindi':
        has_verb = any(re.search(p, text) for p in hindi_verb_patterns)
    else:
        has_verb = any(re.search(p, text, re.I) for p in english_verb_patterns)
        if not has_verb:
            # Also check Hindi verb patterns (mixed text)
            has_verb = any(re.search(p, text) for p in hindi_verb_patterns)

    return has_verb


def validate_input(text: str) -> tuple[bool, str]:
    """
    Validate input text for the fact-checking pipeline.
    Supports English, Hindi (Devanagari), and Hinglish.
    Returns (is_valid, error_message).
    """
    text = text.strip()

    if not text:
        return False, "No text provided. Please enter a sentence or paragraph to verify. / कृपया एक वाक्य दर्ज करें।"

    if len(text) < 3:
        return False, "Input is too short. Please enter a complete sentence. / इनपुट बहुत छोटा है।"

    lang = _detect_language(text)

    # Count words - include both Latin and Devanagari
    latin_words = re.findall(r'\b[a-zA-Z0-9]+\b', text)
    hindi_words = re.findall(r'[\u0900-\u097F]+', text)
    total_words = len(latin_words) + len(hindi_words)

    min_words = 2 if lang == 'hindi' else 3
    if total_words < min_words:
        return False, (
            f'No verifiable sentence found. Please enter a full statement. '
            f'/ कोई सत्यापन योग्य वाक्य नहीं मिला। कृपया पूरा वाक्य दर्ज करें।'
        )

    # Check each sentence in multi-sentence input
    # Split on Hindi purna viram (।) too
    sentences = re.split(r'(?<=[.!?।])\s+|\n+', text)
    valid_sentences = [s for s in sentences if _is_valid_sentence(s)]

    if not valid_sentences:
        if _is_valid_sentence(text):
            return True, ""
        return False, (
            f'No verifiable sentence found. Please enter factual statements like '
            f'"The Earth revolves around the Sun" or "भारत 1947 में आज़ाद हुआ". '
            f'/ कृपया तथ्यात्मक कथन दर्ज करें।'
        )

    return True, ""


# ============================================================
# Enhanced NLP - Claim Extraction
# ============================================================

def _extract_entities(text: str) -> dict:
    """
    Extract named entities using regex patterns.
    Returns dict with entity types and their values.
    """
    entities = {
        "numbers": re.findall(r'\b\d[\d,.]*(?:\s*(?:million|billion|trillion|thousand|hundred|percent|%))?(?:\s*(?:degrees?|km|miles?|kg|lbs?|meters?|feet|inches|cm|mm|liters?|gallons?))?\b', text, re.I),
        "years": re.findall(r'\b(?:1[0-9]{3}|2[0-9]{3})\b', text),
        "dates": re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s+\d{4})?\b', text, re.I),
        "proper_nouns": re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text),
        "locations": [],
        "organizations": [],
    }

    # Location patterns
    loc_patterns = [
        r'\b(?:in|at|from|near|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
    ]
    for p in loc_patterns:
        entities["locations"].extend(re.findall(p, text))

    return entities


def _extract_claims_nlp(text: str) -> list[str]:
    """
    Extract factual claims using advanced sentence-level NLP heuristics.
    Returns a list of sentences that are likely factual claims.
    """
    text = text.strip()
    if not text:
        return []

    # Input validation
    if not _is_valid_sentence(text):
        return []

    # Split into sentences - handle missing punctuation too
    chunks = re.split(r'(?<=[.!?])\s+|\n+|;\s*', text)
    # If no split happened and text doesn't end with punctuation, use the whole text
    if len(chunks) <= 1 and not re.search(r'[.!?]\s*$', text):
        chunks = [text]

    sentences = [c.strip().rstrip('.!?').strip() for c in chunks if c.strip()]

    # Split compound sentences on conjunctions
    expanded = []
    for sent in sentences:
        # Split on "and" / "but" / "however" / "while" only if both sides are long enough
        parts = re.split(r'\b(?:and|but|however|while|whereas|although)\b', sent, flags=re.I)
        if len(parts) > 1:
            for part in parts:
                part = part.strip().strip(',').strip()
                if len(part) >= 15:  # minimum viable sub-sentence
                    expanded.append(part)
            # Also keep the original compound sentence
            expanded.append(sent)
        else:
            expanded.append(sent)

    # De-duplicate
    seen = set()
    unique = []
    for s in expanded:
        key = s.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    sentences = unique

    claims = []

    # Patterns that indicate factual statements (English + Hinglish)
    factual_patterns = [
        r'\b(?:is|are|was|were|has|have|had)\b',  # state of being
        r'\b\d+\b',  # contains numbers
        r'\b(?:million|billion|trillion|thousand|hundred|percent|%)\b',
        r'\b(?:founded|discovered|invented|created|built|established)\b',
        r'\b(?:located|situated|found)\b',
        r'\b(?:largest|smallest|highest|lowest|first|last|oldest|newest)\b',
        r'\b(?:according|study|research|report|data|statistics)\b',
        r'\b(?:capital|population|president|ceo|director|king|queen|emperor|prime\s+minister)\b',
        r'\b(?:died|killed|born|lived|ruled|reigned|conquered|invaded)\b',
        r'\b(?:won|lost|defeated|elected|appointed|resigned|removed)\b',
        r'\b(?:became|turned|changed|converted|transformed)\b',
        r'\b(?:wrote|published|released|launched|started|ended|began)\b',
        r'\b(?:contains?|includes?|consists?|comprises?)\b',
        r'\b(?:weighs?|measures?|costs?|earns?|produces?)\b',
        r'\b(?:orbits?|rotates?|revolves?|spins?|travels?)\b',
        r'\b(?:boils?|freezes?|melts?|burns?|evaporates?)\b',
        r'\b(?:causes?|prevents?|cures?|treats?|affects?)\b',
        r'\b(?:gained|achieved|earned|received|signed|ratified)\b',
        r'\b(?:chemical|reaction|element|compound|molecule|atom)\b',
        r'\b(?:planet|star|galaxy|orbit|solar|lunar|meteor)\b',
        r'\b(?:species|genus|family|evolution|extinct|fossil)\b',
        r'\b(?:independence|constitution|amendment|law|treaty)\b',
        # Hinglish factual patterns
        r'\b(?:hai|hain|tha|thi|the)\b',  # is/are/was/were in Hindi
        r'\b(?:hoga|hogi|honge)\b',  # will be
        r'\b(?:karta|karti|karte|kiya|kiye|ki|karna|karenge|karega|karegi)\b',
        r'\b(?:paida|hua|hui|hue|hona|hota|hoti|hote)\b',  # born/happened
        r'\b(?:jeeta|jeeti|haara|haari|mara|mari)\b',  # win/lose/die
        r'\b(?:banaya|banayi|bana|bani)\b',  # made/created
        r'\b(?:likha|likhi|likhna)\b',  # wrote/write
        r'\b(?:sabse|pehla|pehli|aakhri|bada|badi|chhota|chhoti)\b',  # superlatives
        r'\b(?:pradhan\s*mantri|rashtrapati|mukhya\s*mantri|raja|rani|samrat)\b',  # titles
        r'\b(?:desh|rajdhani|jansankhya|shehar|gaon|nadi|parvat|sagar)\b',  # geography
        r'\b(?:kya|kaun|kaise|kab|kahaan|kyun|kyu[nm]?)\b',  # question words
    ]

    # Patterns that suggest opinions/non-factual content
    opinion_patterns = [
        r'\b(?:I think|I believe|in my opinion|probably|maybe|perhaps|might)\b',
        r'\b(?:should|would|could)\b.*\b(?:better|worse)\b',
        r'\?$',  # questions
    ]

    for sent in sentences:
        if len(sent) < 10 or len(sent) > 300:
            continue

        # Must be a valid sentence structure
        if not _is_valid_sentence(sent):
            continue

        # Skip opinions
        is_opinion = any(re.search(p, sent, re.I) for p in opinion_patterns)
        if is_opinion:
            continue

        # Check for factual patterns
        factual_score = sum(1 for p in factual_patterns if re.search(p, sent, re.I))

        # Bonus for named entities
        entities = _extract_entities(sent)
        entity_count = (
            len(entities["numbers"])
            + len(entities["years"])
            + len(entities["dates"])
            + len(entities["proper_nouns"])
        )
        factual_score += min(entity_count, 3)  # cap bonus at 3

        if factual_score >= 1:
            claims.append(sent)

    # If the entire input is short (1-2 sentences) and we found nothing,
    # treat the whole text as a single claim if it looks like a statement
    if not claims and len(text) >= 10 and len(text) <= 500:
        if _is_valid_sentence(text):
            claims.append(text.rstrip('.!?').strip())

    return claims[:15]


# ============================================================
# Enhanced NLP - Search Query Generation
# ============================================================

def _generate_search_queries_nlp(claim: str) -> list[str]:
    """
    Generate smart search queries from a claim using keyword extraction.
    Supports English, Hindi (Devanagari), and Hinglish - always generates
    English queries for web search since most search results are in English.
    """
    lang = _detect_language(claim)

    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'that', 'this', 'these', 'those',
        'it', 'its', 'and', 'or', 'but', 'not', 'no', 'if', 'than',
        'so', 'as', 'very', 'most', 'more', 'also', 'just', 'about',
    }

    queries = []

    if lang == 'hindi':
        # Translate Hindi to English keywords for search
        english_translation = _translate_hindi_to_english_keywords(claim)
        if english_translation.strip():
            queries.append(english_translation)
            queries.append(f'fact check {english_translation}')
            queries.append(f'is it true {english_translation}')
        # Also add the original Hindi claim (some search engines handle it)
        queries.append(claim)
    elif lang == 'hinglish':
        # For Hinglish: extract Latin keywords + translate Hinglish stop words
        words = re.findall(r'\b[A-Za-z][a-z]*(?:[A-Z][a-z]*)*\b', claim)
        keywords = [w for w in words if w.lower() not in stop_words
                    and w.lower() not in _HINGLISH_STOP_WORDS and len(w) > 2]
        if keywords:
            queries.append(' '.join(keywords[:6]))
            queries.append(f'fact check {" ".join(keywords[:4])}')
        queries.append(claim)  # original Hinglish as-is
        if len(claim.split()) > 4:
            queries.append(f'is it true that {" ".join(keywords[:6])}')
    else:
        # English: original logic
        words = re.findall(r'\b[A-Za-z][a-z]*(?:[A-Z][a-z]*)*\b', claim)
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2]

        # Numbers and units
        numbers = re.findall(r'\b\d[\d,.]*%?\b', claim)
        keywords.extend(numbers)

        # Proper nouns first
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim)
        pn_set = set(pn.split()[0] for pn in proper_nouns)
        sorted_kw = [w for w in keywords if w in pn_set] + [w for w in keywords if w not in pn_set]
        keywords = sorted_kw if sorted_kw else keywords

        queries.append(claim)
        if keywords:
            queries.append(' '.join(keywords[:6]))
        queries.append(f'fact check {" ".join(keywords[:4])}')
        if len(claim.split()) > 4:
            queries.append(f'is it true that {claim.lower()}')

    # Extract years for time-scoped queries
    years = re.findall(r'\b(?:1[0-9]{3}|2[0-9]{3})\b', claim)
    if years and queries:
        # Add a time-scoped version of the first query
        queries.append(f'{queries[0]} {years[0]}')

    # Temporal claim handling
    import datetime
    claim_type = _classify_claim_type(claim)
    if claim_type == 'temporal':
        current_year = datetime.datetime.now().year
        queries.append(f'{queries[0]} {current_year}' if queries else claim)

    return queries[:6]  # slightly more queries for better coverage


# ============================================================
# Enhanced NLP - Claim Classification
# ============================================================

def _classify_claim_type(claim: str) -> str:
    """
    Classify a claim into a type to determine verification approach.
    Returns: 'factual', 'temporal', 'supernatural', 'opinion', 'prediction',
    'conspiracy', 'fictional_identity', 'absurd_identity', or 'subjective'
    """
    claim_lower = claim.lower()

    # ── Absurd identity claims: "Person A is Person B" where both are distinct entities ──
    # Works for:
    #   English SVO: "Modi is Oppenheimer", "Elon Musk is Albert Einstein"
    #   Hinglish SOV: "Modi oppenheimer hai", "Narendra modi oppenheimer hain"
    #   Mixed case: "narendra modi is oppenheimer"

    # Identity verbs (English + Hinglish)
    identity_verbs = {'is', 'are', 'was', 'were', 'hai', 'hain', 'he', 'tha', 'thi', 'the', 'hoga', 'hogi'}

    # Words that legitimize identity claims (titles, roles, articles, categories)
    legitimate_words = {
        'the', 'a', 'an', 'ka', 'ki', 'ke', 'ek',
        'president', 'prime', 'minister', 'pm', 'ceo', 'chairman', 'director',
        'king', 'queen', 'emperor', 'empress', 'leader', 'chief', 'head',
        'founder', 'creator', 'inventor', 'author', 'writer', 'singer',
        'actor', 'actress', 'player', 'captain', 'coach', 'manager',
        'father', 'mother', 'son', 'daughter', 'brother', 'sister',
        'pradhan', 'mantri', 'mukhya', 'rashtrapati', 'raja', 'rani',
        'neta', 'adhyaksh', 'sachiv', 'sarpanch',
        'capital', 'city', 'country', 'state', 'river', 'mountain',
        'planet', 'element', 'type', 'kind', 'form', 'part', 'member',
        'largest', 'smallest', 'biggest', 'tallest', 'fastest', 'oldest',
        'first', 'second', 'third', 'last', 'best', 'worst',
        'chemical', 'reaction', 'process', 'known',
    }

    # Words that indicate a descriptive/comparative claim, NOT an identity claim.
    # If ANY of these appear after the identity verb, it's not "X is Y" identity.
    non_identity_words = {
        # Comparatives & superlatives
        'hotter', 'colder', 'bigger', 'smaller', 'larger', 'taller', 'shorter',
        'faster', 'slower', 'heavier', 'lighter', 'stronger', 'weaker',
        'better', 'worse', 'higher', 'lower', 'deeper', 'wider', 'thicker',
        'thinner', 'richer', 'poorer', 'older', 'younger', 'newer', 'closer',
        'farther', 'more', 'less', 'most', 'least',
        # Comparison word
        'than',
        # Common adjectives / descriptors
        'hot', 'cold', 'big', 'small', 'large', 'tall', 'short', 'fast', 'slow',
        'heavy', 'light', 'strong', 'weak', 'important', 'necessary', 'visible',
        'close', 'far', 'rich', 'poor', 'old', 'young', 'new', 'deep', 'wide',
        'thick', 'thin', 'hard', 'soft', 'bright', 'dark', 'loud', 'quiet',
        'wet', 'dry', 'full', 'empty', 'safe', 'dangerous', 'healthy', 'sick',
        'common', 'rare', 'famous', 'popular', 'expensive', 'cheap', 'free',
        'true', 'false', 'correct', 'incorrect', 'right', 'wrong',
        'located', 'situated', 'found', 'made', 'composed', 'based',
        'used', 'called', 'considered', 'regarded', 'seen', 'viewed',
        # Negation & modifiers
        'not', 'also', 'very', 'much', 'really', 'always', 'never', 'often',
        'even', 'still', 'just', 'about', 'actually', 'approximately',
        # Prepositions / connectors that signal description
        'because', 'due', 'since', 'although', 'despite', 'while',
        'where', 'when', 'how', 'why', 'what', 'which',
        # Quantifiers / determiners in predicate
        'one', 'two', 'three', 'many', 'few', 'several', 'some', 'any',
        'every', 'each', 'all', 'both', 'half', 'enough',
        # Common predicate nouns (non-name)
        'place', 'thing', 'way', 'fact', 'case', 'result', 'cause',
        'effect', 'source', 'example', 'problem', 'reason', 'answer',
    }

    # Role/portrayal context words
    role_words = {
        'played', 'portrayed', 'portrays', 'acting', 'role', 'character',
        'film', 'movie', 'series', 'show', 'nicknamed', 'called',
        'alias', 'born', 'née', 'stage', 'pen', 'real', 'name',
    }

    # Check if any role words appear in the claim
    claim_word_set = set(claim_lower.split())
    if not (role_words & claim_word_set):
        # Split claim into words, find identity verb position
        words = claim_lower.split()
        verb_positions = [i for i, w in enumerate(words) if w in identity_verbs]

        for vpos in verb_positions:
            # Get words before and after the verb
            before = [w for w in words[:vpos] if w not in identity_verbs and len(w) > 1]
            after = [w for w in words[vpos+1:] if w not in identity_verbs and len(w) > 1]

            # Check if any legitimate context words appear
            all_non_verb = set(before + after)
            if legitimate_words & all_non_verb:
                continue

            # If any word after the verb is a descriptive/comparative word,
            # this is NOT an identity claim (e.g. "Venus is hotter than Mercury")
            after_set = set(after)
            if non_identity_words & after_set:
                continue

            # Need name-like words on both sides (or SOV: 2+ names before verb, none after)
            if before and after:
                # SVO: "Modi is Oppenheimer" - names on both sides
                return 'absurd_identity'

        # SOV check for Hinglish: "Narendra modi oppenheimer hain"
        # Verb is at the end, everything before it is names
        if words and words[-1] in identity_verbs:
            name_words = [w for w in words[:-1] if w not in identity_verbs and len(w) > 1]
            non_legit = [w for w in name_words if w not in legitimate_words and w not in non_identity_words]
            # If we have 2+ distinct name-like words and no legitimate context
            if len(non_legit) >= 2 and not (legitimate_words & set(name_words)):
                # Check they seem like distinct entities (not "narendra modi" which is one person)
                # Heuristic: if there are 3+ words or two single-word names that appear distinct
                if len(non_legit) >= 3:
                    # Likely "FirstName LastName OtherPerson verb"
                    return 'absurd_identity'
                elif len(non_legit) == 2:
                    # Could be "FirstName LastName verb" (legitimate) or "PersonA PersonB verb"
                    # We'll flag it if neither word is a common first-name/last-name pair
                    # Simple heuristic: if both words are >= 4 chars, likely two entities
                    if all(len(w) >= 4 for w in non_legit):
                        return 'absurd_identity'

    # Fictional identity/metaphor claims (e.g., "X is Batman").
    # These are usually figurative or false unless clearly framed as a role/portrayal.
    fictional_characters = [
        "batman", "superman", "spider-man", "spiderman", "iron man", "ironman",
        "joker", "thor", "hulk", "captain america", "wonder woman", "flash",
        "aquaman", "deadpool", "wolverine", "harry potter", "darth vader",
        "sherlock holmes", "jack sparrow", "elsa", "barbie",
    ]
    has_fictional_entity = any(fc in claim_lower for fc in fictional_characters)
    has_identity_verb = bool(re.search(r'\b(?:is|are|was|were|be|am)\b', claim_lower))
    role_context = bool(re.search(r'\b(?:actor|actress|played|portrayed|portrays|as|role|character|in\s+the\s+film|movie|series)\b', claim_lower))
    if has_fictional_entity and has_identity_verb and not role_context:
        return 'fictional_identity'

    # Supernatural / religious / mythological claims (English + Hindi)
    supernatural_patterns = [
        r'\b(?:god|gods|deity|divine|avatar|incarnation|reincarnation)\b',
        r'\b(?:miracle|supernatural|paranormal|magic|magical|curse|cursed)\b',
        r'\b(?:heaven|hell|afterlife|soul|spirit|angel|demon|devil)\b',
        r'\b(?:prophecy|prophesied|messiah|savior|prophet)\b',
        r'\b(?:vishnu|shiva|brahma|krishna|rama|allah|jesus\s+is\s+god)\b',
        r'\b(?:reborn|rebirth|resurrection|ascend|descended\s+from)\b',
        r'\b(?:chosen\s+one|sent\s+by\s+god|blessed\s+by|holy)\b',
        r'\b(?:zodiac|astrology|horoscope|psychic|telepathy|clairvoyant)\b',
        r'\b(?:ghost|haunted|possessed|exorcis[tm]|witch|witchcraft)\b',
        r'\b(?:alien\s+abduction|ufo\s+(?:cover|conspir)|flat\s+earth)\b',
    ]
    # Hindi supernatural patterns (Devanagari)
    hindi_supernatural_patterns = [
        r'(?:भगवान|देवता|ईश्वर|परमात्मा|अवतार)',
        r'(?:चमत्कार|अलौकिक|जादू|जादुई|श्राप|अभिशाप)',
        r'(?:स्वर्ग|नरक|आत्मा|भूत|प्रेत|पिशाच|राक्षस)',
        r'(?:भविष्यवाणी|मसीहा|पैगंबर|अवतरण)',
        r'(?:विष्णु|शिव|ब्रह्मा|कृष्ण|राम)',
        r'(?:पुनर्जन्म|पुनरुत्थान|दिव्य|पवित्र)',
        r'(?:ज्योतिष|कुंडली|राशि|टोना|टोटका)',
    ]
    if any(re.search(p, claim_lower) for p in supernatural_patterns):
        return 'supernatural'
    if any(re.search(p, claim) for p in hindi_supernatural_patterns):
        return 'supernatural'

    # Conspiracy / unverifiable fringe claims
    conspiracy_patterns = [
        r'\b(?:conspiracy|cover[\s-]?up|illuminati|deep\s+state|new\s+world\s+order)\b',
        r'\b(?:secretly|secret\s+(?:plan|society|agenda)|shadow\s+government)\b',
        r'\b(?:hoax|staged|false\s+flag|crisis\s+actor)\b',
        r'\b(?:chemtrail|mind\s+control|microchip|5g\s+(?:cause|spread|virus))\b',
    ]
    if any(re.search(p, claim_lower) for p in conspiracy_patterns):
        return 'conspiracy'

    # Pure opinion / subjective statements
    opinion_patterns = [
        r'\b(?:best|worst|greatest|most\s+(?:beautiful|important|talented))\b.*\b(?:ever|world|history)\b',
        r'\b(?:should|ought\s+to|need\s+to|must)\b',
        r'\bis\s+(?:better|worse|superior|inferior)\s+(?:than|to)\b',
    ]
    if any(re.search(p, claim_lower) for p in opinion_patterns):
        return 'opinion'

    # Temporal / time-sensitive claims
    temporal_patterns = [
        r'\b(?:current|currently|present|presently|now|today)\b',
        r'\b(?:as\s+of\s+\d{4}|at\s+the\s+time\s+of|at\s+present)\b',
        r'\b(?:latest|recent|recently|newest|this\s+year|this\s+month)\b',
        r'\b(?:still|no\s+longer|anymore|has\s+since|has\s+been)\b',
        r'\b(?:incumbent|reigning|sitting|acting)\s+(?:president|pm|prime\s+minister|ceo|chairman|king|queen|minister)\b',
        r'\b(?:leads?|heads?|runs?|manages?|chairs?)\s',
    ]
    if any(re.search(p, claim_lower) for p in temporal_patterns):
        return 'temporal'

    return 'factual'


# ============================================================
# Enhanced NLP - Source Credibility
# ============================================================

def _get_source_credibility(url: str) -> float:
    """
    Score source credibility based on domain.
    Returns multiplier: 1.5 for authoritative, 1.0 for normal, 0.3 for low quality.
    """
    url_lower = url.lower()

    # High credibility sources
    high_cred = [
        'wikipedia.org', 'britannica.com', 'reuters.com', 'apnews.com',
        'bbc.com', 'bbc.co.uk', 'nature.com', 'science.org', 'sciencedirect.com',
        'pubmed.ncbi', 'pmc.ncbi', 'nih.gov', 'nasa.gov', 'who.int',
        'un.org', 'worldbank.org', 'nytimes.com', 'washingtonpost.com',
        'theguardian.com', 'economist.com', 'nationalgeographic.com',
        'smithsonianmag.com', 'snopes.com', 'factcheck.org', 'politifact.com',
        'scholar.google', 'jstor.org', 'springer.com', 'wiley.com',
        'academic.oup.com', 'cambridge.org', 'merriam-webster.com',
    ]
    if any(domain in url_lower for domain in high_cred):
        return 1.5

    # Medium-high: .edu, .gov domains
    if '.edu' in url_lower or '.gov' in url_lower:
        return 1.3

    # Low credibility signals (blogs, social media, fringe sites)
    low_cred = [
        'facebook.com', 'twitter.com', 'x.com', 'reddit.com', 'quora.com',
        'yahoo.com/answers', 'answers.com', 'blog.', 'wordpress.com',
        'blogspot.com', 'tumblr.com', 'medium.com', 'opindia.com',
        'swarajyamag.com', 'tfipost.com', 'postcard.news', 'kreately.in',
        'tiktok.com', 'instagram.com', 'pinterest.com',
    ]
    if any(domain in url_lower for domain in low_cred):
        return 0.3

    return 1.0


# ============================================================
# Enhanced NLP - TF-IDF-like Keyword Weighting
# ============================================================

def _compute_word_weights(claim_words: list[str], evidence_list: list[dict]) -> dict[str, float]:
    """
    Compute TF-IDF-like weights for claim words.
    Rare words (appearing in fewer evidence snippets) get higher weight.
    """
    if not claim_words or not evidence_list:
        return {w: 1.0 for w in claim_words}

    # Document frequency: how many evidence snippets contain each word
    doc_freq = Counter()
    for e in evidence_list:
        snippet = (e.get('snippet', '') + ' ' + e.get('title', '')).lower()
        snippet_words = set(re.findall(r'\b\w+\b', snippet))
        for w in claim_words:
            if w in snippet_words:
                doc_freq[w] += 1

    N = len(evidence_list)
    weights = {}
    for w in claim_words:
        df = doc_freq.get(w, 0)
        # IDF: log(N / (1 + df)) - rare words are more important
        idf = math.log((N + 1) / (1 + df)) + 1.0
        weights[w] = idf

    return weights


def _extract_ngrams(text: str, n: int) -> set[str]:
    """Extract n-grams from text."""
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < n:
        return set()
    return {' '.join(words[i:i+n]) for i in range(len(words) - n + 1)}


def _extract_numbers(text: str) -> list[float]:
    """Extract numerical values from text."""
    nums = []
    matches = re.findall(r'\b(\d[\d,.]*)\b', text)
    for m in matches:
        try:
            cleaned = m.replace(',', '')
            nums.append(float(cleaned))
        except ValueError:
            pass
    return nums


# ============================================================
# Reward-Model Helper - Platt-style Confidence Calibration
# ============================================================

def _platt_calibrate(raw_score: float, k: float = 6.0, x0: float = 0.5) -> float:
    """
    Apply sigmoid (Platt) calibration to map raw scores [0,1] to
    calibrated probabilities. Prevents overconfidence from heuristics.
    k = steepness, x0 = midpoint.
    """
    import math
    return 1.0 / (1.0 + math.exp(-k * (raw_score - x0)))


def _evidence_verdict_consistency_reward(
    verdict: str,
    support_score: float,
    contradict_score: float,
    supporting_sources: int,
    contradicting_sources: int,
) -> float:
    """
    RL Reward: +reward when chosen verdict is consistent with evidence signals,
    -penalty when it conflicts. Returns adjustment to confidence (-20 to +15).
    """
    reward = 0.0

    if verdict == "True":
        if support_score > contradict_score * 2 and supporting_sources >= 2:
            reward += 12  # strong alignment
        elif support_score > contradict_score:
            reward += 5
        elif contradict_score > support_score:
            reward -= 15  # verdict contradicts evidence!

    elif verdict == "False":
        if contradict_score > support_score * 2 and contradicting_sources >= 2:
            reward += 12
        elif contradict_score > support_score:
            reward += 5
        elif support_score > contradict_score:
            reward -= 15

    elif verdict == "Partially True":
        if support_score > 0 and contradict_score > 0:
            reward += 8  # mixed evidence = correct call
        else:
            reward -= 5  # no real mix

    elif verdict == "Unverifiable":
        total = support_score + contradict_score
        if total < 0.5:
            reward += 5  # genuinely weak evidence
        elif total > 3.0:
            reward -= 10  # plenty of evidence but called unverifiable

    return reward


def _source_diversity_bonus(evidence: list[dict]) -> float:
    """
    RL Reward: bonus for evidence from diverse, independent domains.
    """
    domains = set()
    for e in evidence:
        url = e.get('url', '')
        # Extract domain
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if match:
            domains.add(match.group(1).lower())

    if len(domains) >= 4:
        return 8.0
    elif len(domains) >= 3:
        return 5.0
    elif len(domains) >= 2:
        return 2.0
    return 0.0


# ============================================================
# Enhanced NLP - Claim Verification with Reward Scoring
# ============================================================

def _verify_claim_nlp(claim: str, evidence: list[dict]) -> dict:
    """
    Verify a claim against evidence using enhanced text matching and heuristics,
    enhanced with RL reward-model scoring:
    - Evidence-verdict consistency rewards/penalties
    - Platt-style confidence calibration
    - Source agreement and diversity bonuses
    - Temporal evidence decay
    - Negation detection, n-gram matching, numerical comparison
    """
    # --- Step 0: Classify claim type and generate claim-specific reasoning ---
    claim_type = _classify_claim_type(claim)

    # Extract key entities from the claim for specific reasoning
    _claim_entities = [w for w in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim)]
    _entity_str = ', '.join(_claim_entities[:3]) if _claim_entities else claim[:60]

    if claim_type == 'supernatural':
        return {
            "verdict": "Unverifiable",
            "confidence": 88,
            "reasoning": (
                f"The claim about {_entity_str} involves supernatural, religious, or mythological assertions "
                f"that cannot be objectively verified through empirical evidence. Such claims are matters of "
                f"faith or belief rather than factual statements that can be checked against data. "
                f"No web evidence can conclusively prove or disprove claims of this nature."
            ),
        }

    if claim_type == 'conspiracy':
        return {
            "verdict": "Unverifiable",
            "confidence": 82,
            "reasoning": (
                f"The claim about {_entity_str} involves a conspiracy theory or fringe assertion. "
                f"Such claims typically lack verifiable evidence and are constructed to resist disproof. "
                f"Credible mainstream sources do not support conspiracy-style claims, and the absence of "
                f"evidence is often misinterpreted as evidence of cover-up."
            ),
        }

    if claim_type == 'fictional_identity':
        return {
            "verdict": "False",
            "confidence": 90,
            "reasoning": (
                f"This claim equates {_entity_str} with a fictional character without any role or "
                f"portrayal context. As a literal factual statement, this is incorrect - the fictional "
                f"character and the real entity mentioned are categorically different. The statement "
                f"may be intended metaphorically, but as a factual claim it is false."
            ),
        }

    if claim_type == 'absurd_identity':
        claim_words = [w for w in claim.split() if len(w) > 1 and w.lower() not in {
            'is', 'are', 'was', 'were', 'hai', 'hain', 'he', 'tha', 'thi', 'the',
            'a', 'an', 'the', 'of', 'in', 'and', 'or',
        }]
        ent_a = claim_words[0] if claim_words else 'Entity A'
        ent_b = claim_words[-1] if len(claim_words) > 1 else 'Entity B'
        return {
            "verdict": "False",
            "confidence": 92,
            "reasoning": (
                f"This claim asserts that {ent_a} IS {ent_b}, equating two distinct real-world "
                f"entities. {ent_a} and {ent_b} are different individuals with separate identities, "
                f"histories, and biographies. No credible evidence supports that they are the same "
                f"person or entity. Evidence mentioning both names does not constitute proof of identity."
            ),
        }

    if claim_type == 'opinion':
        return {
            "verdict": "Unverifiable",
            "confidence": 78,
            "reasoning": (
                f"The claim about {_entity_str} expresses a subjective opinion or value judgment "
                f"rather than an objective factual statement. Opinions and preferences cannot be "
                f"verified as true or false through evidence - they reflect personal viewpoints "
                f"rather than measurable facts."
            ),
        }

    is_temporal = claim_type == 'temporal'
    temporal_caveat = ""
    if is_temporal:
        import datetime
        current_year = datetime.datetime.now().year
        temporal_caveat = f" ⚠️ Note: This is a time-sensitive claim. The evidence retrieved may not reflect the most current information (checked in {current_year}). Facts like leadership positions, rankings, and statistics change over time."

    # --- Step 1: Check if we have evidence ---
    if not evidence:
        if is_temporal:
            return {
                "verdict": "Unverifiable",
                "confidence": 30,
                "reasoning": f"No web evidence found to verify this time-sensitive claim. Temporal claims like this require up-to-date sources to verify accurately.",
            }
        return {
            "verdict": "Unverifiable",
            "confidence": 0,
            "reasoning": "No web evidence found to verify this claim.",
        }

    claim_lower = claim.lower()
    claim_words_list = [w for w in re.findall(r'\b\w+\b', claim_lower)
                        if len(w) > 1]
    claim_words = set(claim_words_list)
    claim_words -= {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'of', 'to', 'and', 'it'}

    if not claim_words:
        return {
            "verdict": "Unverifiable",
            "confidence": 10,
            "reasoning": "Could not extract meaningful keywords from the claim.",
        }

    # Extract claim n-grams and numbers
    claim_bigrams = _extract_ngrams(claim, 2)
    claim_trigrams = _extract_ngrams(claim, 3)
    claim_numbers = _extract_numbers(claim)

    # Compute TF-IDF-like weights
    word_weights = _compute_word_weights(list(claim_words), evidence)

    # Key subject/object words for negation proximity checks
    claim_key_words = [w for w in re.findall(r'\b\w+\b', claim_lower)
                       if len(w) > 3 and w not in {
                           'the', 'a', 'an', 'is', 'are', 'was', 'were',
                           'in', 'of', 'to', 'and', 'it', 'that', 'this', 'from', 'with', 'has',
                           'have', 'had', 'for', 'but', 'not', 'been', 'being', 'will', 'would',
                           'could', 'can', 'does', 'did', 'also', 'its', 'they', 'their', 'than',
                           'into', 'only', 'very', 'just', 'about', 'more', 'most', 'some', 'such'}]

    support_score = 0.0
    contradict_score = 0.0
    total_relevance = 0.0
    relevant_sources = []
    credible_source_count = 0
    supporting_sources = 0
    contradicting_sources = 0
    high_cred_supporting_sources = 0
    high_cred_contradicting_sources = 0
    low_cred_supporting_sources = 0

    for e in evidence:
        snippet = (e.get('snippet', '') + ' ' + e.get('title', '')).lower()
        title = e.get('title', '').lower()
        url = e.get('url', '')
        snippet_words = set(re.findall(r'\b\w+\b', snippet))

        # Source credibility multiplier
        credibility = _get_source_credibility(url)
        if credibility >= 1.3:
            credible_source_count += 1

        # === Enhanced relevance: weighted word overlap ===
        weighted_overlap = 0.0
        total_weight = 0.0
        for w in claim_words:
            weight = word_weights.get(w, 1.0)
            total_weight += weight
            if w in snippet_words:
                weighted_overlap += weight

        overlap = weighted_overlap / total_weight if total_weight > 0 else 0
        total_relevance += overlap

        # === N-gram matching bonus ===
        snippet_bigrams = _extract_ngrams(snippet, 2)
        snippet_trigrams = _extract_ngrams(snippet, 3)

        bigram_overlap = len(claim_bigrams & snippet_bigrams) / max(len(claim_bigrams), 1)
        trigram_overlap = len(claim_trigrams & snippet_trigrams) / max(len(claim_trigrams), 1)

        # Boost overlap with n-gram matches
        ngram_bonus = bigram_overlap * 0.15 + trigram_overlap * 0.25
        overlap = min(overlap + ngram_bonus, 1.0)

        # === Numerical matching ===
        snippet_numbers = _extract_numbers(snippet)
        number_match = False
        if claim_numbers and snippet_numbers:
            for cn in claim_numbers:
                for sn in snippet_numbers:
                    if cn == sn or (cn > 0 and abs(cn - sn) / cn < 0.01):
                        number_match = True
                        break

        if overlap < 0.15:
            continue

        relevant_sources.append(e.get('title', 'Unknown source'))

        # --- Contradiction detection ---
        contradiction_patterns = [
            r'\b(?:false|incorrect|wrong|myth|debunk|misleading|inaccurate|untrue)\b',
            r'\b(?:contrary|disproven|refuted|fake|hoax|misconception|misinformation)\b',
            r'\bnot\s+true\b',
            r'\bnot\s+(?:visible|possible|accurate|correct|real|the\s+(?:largest|smallest|biggest))\b',
            r'\b(?:truth\s+behind|behind\s+the\s+myth)\b',
            r'\b(?:actually|reality)\b.*\b(?:not|isn\'t|wasn\'t|aren\'t|weren\'t)\b',
            r'\b(?:no\s+(?:evidence|proof|basis|credible|scientific))\b',
            r'\b(?:lacks?\s+(?:evidence|proof|basis))\b',
            r'\b(?:pseudoscience|unsubstantiated|unfounded|baseless|unproven)\b',
            r'\b(?:claim(?:s|ed)?\s+(?:without|lacks?|no)\s+(?:evidence|proof))\b',
        ]
        has_contradiction = any(re.search(p, snippet) for p in contradiction_patterns)

        # Negation proximity check
        negation_near_keyword = False
        for kw in claim_key_words[:5]:
            neg_prox = re.search(
                rf'\b(?:not|no|never|isn\'t|wasn\'t|aren\'t|cannot|can\'t|impossible|unable)\b.{{0,40}}\b{re.escape(kw)}\b',
                snippet
            )
            neg_prox2 = re.search(
                rf'\b{re.escape(kw)}\b.{{0,40}}\b(?:not|no|never|isn\'t|wasn\'t|aren\'t|cannot|can\'t|impossible)\b',
                snippet
            )
            if neg_prox or neg_prox2:
                negation_near_keyword = True
                break

        # Title debunk detection
        title_debunk_patterns = [
            r'\b(?:myth|debunk|false|wrong|fake|hoax|truth\s+behind|misconception)\b',
            r'\b(?:not\s+(?:visible|true|real|possible|correct))\b',
            r'\b(?:impossible|unproven|baseless)\b',
        ]
        title_has_debunk = any(re.search(p, title) for p in title_debunk_patterns)

        # --- Support detection ---
        support_patterns = [
            r'\b(?:confirmed|verified|proven|established|documented)\b',
            r'\b(?:research\s+(?:shows|confirms|proves|demonstrates))\b',
            r'\b(?:studies?\s+(?:show|confirm|prove|demonstrate|found|indicate))\b',
            r'\b(?:data\s+(?:shows|confirms|demonstrates|indicates))\b',
            r'\b(?:scientists?\s+(?:confirm|prove|found|discovered|determined))\b',
            r'\b(?:evidence\s+(?:shows|confirms|supports|demonstrates|indicates))\b',
            r'\b(?:is\s+(?:a|an|the)\b)',
            r'\b(?:consists?\s+of|composed\s+of|comprising|made\s+(?:up\s+)?of)\b',
            r'\b(?:known\s+(?:as|for|to\s+be))\b',
            r'\b(?:defined\s+as|refers?\s+to|describes?)\b',
            r'\b(?:approximately|roughly|about|around)\s+\d',
            r'\b(?:chemical\s+(?:reaction|process|change))\b',
            r'\b(?:process\s+(?:of|known|called|involving))\b',
            r'\b(?:occurs?\s+(?:when|during|in|at))\b',
            r'\b(?:involves?\s+(?:the|a))\b',
            r'\b(?:produced\s+(?:by|from|through|when))\b',
            r'\b(?:results?\s+(?:in|from))\b',
            r'\b(?:measured\s+(?:in|at|by))\b',
            r'\b(?:located\s+(?:in|at|on|near))\b',
            r'\b(?:discovered\s+(?:in|by|during))\b',
            r'\b(?:founded\s+(?:in|by|on))\b',
            r'\b(?:according\s+to)\b',
            r'\b(?:in\s+fact|actually|indeed)\b',
            r'\b(?:officially|formally|technically)\b',
        ]
        has_support = any(re.search(p, snippet) for p in support_patterns)

        # --- Score calculation with full enhancement ---
        if title_has_debunk:
            contradict_score += overlap * 3.0 * credibility
            contradicting_sources += 1
            if credibility >= 1.3:
                high_cred_contradicting_sources += 1
        elif negation_near_keyword and not has_support:
            contradict_score += overlap * 2.5 * credibility
            contradicting_sources += 1
            if credibility >= 1.3:
                high_cred_contradicting_sources += 1
        elif has_contradiction and not has_support:
            contradict_score += overlap * 2.0 * credibility
            contradicting_sources += 1
            if credibility >= 1.3:
                high_cred_contradicting_sources += 1
        elif has_support:
            base = overlap * 2.0 * credibility
            # Numerical match bonus
            if number_match:
                base *= 1.4
            support_score += base
            supporting_sources += 1
            if credibility >= 1.3:
                high_cred_supporting_sources += 1
            if credibility <= 0.5:
                low_cred_supporting_sources += 1
        elif overlap > 0.25 and credibility >= 1.0:
            base = overlap * 0.7 * credibility
            if number_match:
                base *= 1.3
            support_score += base
            supporting_sources += 1
            if credibility >= 1.3:
                high_cred_supporting_sources += 1
            if credibility <= 0.5:
                low_cred_supporting_sources += 1
        elif has_contradiction:
            contradicting_sources += 1
            if credibility >= 1.3:
                high_cred_contradicting_sources += 1

    # --- Consensus bonus ---
    consensus_bonus = 0
    if supporting_sources >= 3 and contradicting_sources == 0:
        consensus_bonus = min(25, supporting_sources * 6)  # Up to +25%
    elif supporting_sources >= 2 and contradicting_sources == 0:
        consensus_bonus = 10

    # Credible source bonus
    credible_bonus = 0
    if credible_source_count >= 2:
        credible_bonus = 8
    elif credible_source_count >= 1:
        credible_bonus = 4

    # Source diversity bonus (RL reward)
    diversity_bonus = _source_diversity_bonus(evidence)

    # ============================================================
    # COMPOUND CLAIM DETECTION ("or" / "and" claims)
    # ============================================================
    # "Modi is PM of India or USA" → split and verify each alternative
    compound_penalty = 0.0
    compound_note = ""

    # Simple regex: capture 1-2 words directly adjacent to "or"
    or_match = re.search(r'\b(\w+(?:\s+\w+)?)\s+or\s+(\w+(?:\s+\w+)?)\b', claim_lower)
    if or_match:
        alt1 = or_match.group(1).strip()
        alt2 = or_match.group(2).strip()
        # Skip trivial words (e.g., "true or false")
        skip_words = {'true', 'false', 'not', 'yes', 'no', 'more', 'less'}
        if alt1 not in skip_words and alt2 not in skip_words and len(alt1) >= 2 and len(alt2) >= 2:
            alt1_found = 0
            alt2_found = 0
            for e in evidence:
                snip = (e.get('snippet', '') + ' ' + e.get('title', '')).lower()
                if alt1 in snip:
                    alt1_found += 1
                if alt2 in snip:
                    alt2_found += 1

            if alt1_found > 0 and alt2_found == 0:
                # One part is supported, the other isn't → mild penalty, mark as partially true
                support_score *= 0.85  # only 15% penalty - the supported part IS correct
                compound_note = f"The claim mentions '{alt1}' (found in {alt1_found} source(s)) and '{alt2}' (not found in any source). Only part of this compound claim is supported by evidence."
            elif alt2_found > 0 and alt1_found == 0:
                support_score *= 0.85
                compound_note = f"The claim mentions '{alt2}' (found in {alt2_found} source(s)) and '{alt1}' (not found in any source). Only part of this compound claim is supported by evidence."
            elif alt1_found == 0 and alt2_found == 0:
                support_score *= 0.5  # heavier penalty: neither alternative found
                compound_note = f"The claim mentions '{alt1}' and '{alt2}' but neither was found in evidence."

    # ============================================================
    # KEY-TERM SPECIFICITY CHECK
    # ============================================================
    # Ensure ALL important claim terms appear in evidence, not just some.
    important_claim_words = set()
    for w in claim_key_words:
        if len(w) >= 3:  # lowered from 4 to catch 'usa', 'uk', etc.
            important_claim_words.add(w)

    all_evidence_text = ''
    if evidence:
        all_evidence_text = ' '.join(
            (e.get('snippet', '') + ' ' + e.get('title', '')).lower()
            for e in evidence
        )

    if important_claim_words and all_evidence_text:
        missing_terms = [w for w in important_claim_words if w not in all_evidence_text]

        if missing_terms and len(missing_terms) / len(important_claim_words) > 0.2:
            specificity_penalty = 0.5 * (len(missing_terms) / len(important_claim_words))
            support_score *= (1.0 - specificity_penalty)
            if not compound_note:
                compound_note = f"Key claim terms not found in any evidence: {', '.join(missing_terms[:5])}."
            else:
                compound_note += f" Missing terms: {', '.join(missing_terms[:5])}."

    # ============================================================
    # ENTITY MISMATCH DETECTION (Critical for accuracy)
    # ============================================================
    # Catches: "Modi is PM of USA" when evidence says "PM of India"
    # If claim says "of/in/from X" but evidence says "of/in/from Y",
    # evidence actually CONTRADICTS the claim.
    entity_mismatch_detected = False
    if all_evidence_text and support_score > 0:
        # Extract context entities after prepositions in the claim
        prep_contexts = re.findall(
            r'\b(?:of|in|from|for)\s+(\w+(?:\s+\w+)?)\b', claim_lower
        )
        for ctx in prep_contexts:
            ctx_word = ctx.strip().split()[-1]  # last word (e.g., 'usa', 'india')
            # Skip generic/stop words
            if ctx_word in {'the', 'a', 'an', 'this', 'that', 'its', 'all', 'some',
                            'many', 'most', 'any', 'each', 'every', 'world'}:
                continue
            if len(ctx_word) < 2:
                continue

            # Check if this entity appears in evidence
            # Also check common equivalents (usa/united states, uk/united kingdom)
            equivalents = {
                'usa': ['usa', 'united states', 'u.s.', 'u.s.a', 'america'],
                'uk': ['uk', 'united kingdom', 'britain', 'u.k.'],
                'us': ['united states', 'u.s.', 'america', 'usa'],
            }
            search_terms = equivalents.get(ctx_word, [ctx_word])

            found_in_evidence = any(
                term in all_evidence_text for term in search_terms
            )

            if not found_in_evidence:
                # The key context entity is MISSING from ALL evidence.
                # Check if evidence mentions a COMPETING entity instead.
                # e.g., claim says "of usa" but evidence says "of india"
                # This is a strong contradiction signal.
                entity_mismatch_detected = True
                support_score *= 0.1  # devastating penalty
                contradict_score += 2.0  # boost contradiction
                contradicting_sources += 1
                compound_note = (
                    f"Entity mismatch: claim asserts '{ctx_word}' but this term "
                    f"was not found in any of the {len(evidence)} evidence sources. "
                    f"The evidence may describe a different entity/location."
                )
                break  # one mismatch is enough

    # --- Determine verdict ---
    avg_relevance = total_relevance / len(evidence) if evidence else 0

    # Collect useful data for reasoning
    top_sources = relevant_sources[:3]
    src_list = ', '.join(top_sources) if top_sources else 'no relevant sources'

    # Extract top 2 matching evidence snippets for reasoning
    best_snippet = ""
    best_snippet_score = 0
    second_snippet = ""
    second_snippet_score = 0
    best_snippet_source = ""
    for e in evidence:
        snip = e.get('snippet', '').strip()
        title = e.get('title', '').strip()
        if not snip:
            continue
        snip_lower = snip.lower()
        snip_words = set(re.findall(r'\b\w+\b', snip_lower))
        score = len(claim_words & snip_words)
        if score > best_snippet_score:
            # Demote current best to second
            second_snippet = best_snippet
            second_snippet_score = best_snippet_score
            best_snippet_score = score
            best_snippet = snip[:180].rsplit(' ', 1)[0] + ('...' if len(snip) > 180 else '')
            best_snippet_source = title[:60] if title else 'web source'
        elif score > second_snippet_score:
            second_snippet_score = score
            second_snippet = snip[:150].rsplit(' ', 1)[0] + ('...' if len(snip) > 150 else '')

    # Key claim entities for reasoning
    claim_entities = [w for w in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim)]
    entity_str = ', '.join(claim_entities[:3]) if claim_entities else claim[:50]

    # Count matched keywords for transparency
    matched_keywords = []
    for e in evidence:
        snip = (e.get('snippet', '') + ' ' + e.get('title', '')).lower()
        for w in claim_words:
            if w in snip and w not in matched_keywords:
                matched_keywords.append(w)
    kw_str = ', '.join(matched_keywords[:6])

    # --- Build evidence citation string for reasoning ---
    evidence_cite = ""
    if best_snippet:
        evidence_cite = f'According to {best_snippet_source}: "{best_snippet}"'
        if second_snippet:
            evidence_cite += f' Additional source confirms: "{second_snippet}"'

    if avg_relevance < 0.12:
        verdict = "Unverifiable"
        raw_conf = 25
        reasoning = (
            f"The claim '{claim[:80]}' could not be verified. "
            f"Analyzed {len(evidence)} web sources but none directly address this specific assertion about {entity_str}. "
            f"The retrieved evidence discusses related topics but does not contain information "
            f"that would confirm or deny the specific claim being made."
        )
    elif contradict_score > 0 and support_score == 0:
        verdict = "False"
        raw_conf = min(92, int(45 + contradict_score * 15))
        reasoning = (
            f"The claim '{claim[:80]}' is contradicted by evidence. "
            f"{contradicting_sources} source(s) including {src_list} contain information "
            f"that directly disputes this assertion about {entity_str}. "
        )
        if best_snippet:
            reasoning += f'Key finding: "{best_snippet}" '
        reasoning += f"No supporting evidence was found among the {len(evidence)} sources analyzed."
    elif contradict_score > support_score * 1.2 and contradict_score > 0.8:
        verdict = "False"
        raw_conf = min(88, int(40 + contradict_score * 12))
        reasoning = (
            f"The claim about {entity_str} is predominantly contradicted by available evidence. "
            f"After analyzing {len(relevant_sources)} relevant sources, {contradicting_sources} "
            f"source(s) dispute the claim while only {supporting_sources} provide any support. "
        )
        if best_snippet:
            reasoning += f'Evidence states: "{best_snippet}" '
        if second_snippet:
            reasoning += f'Additional context: "{second_snippet}" '
    elif support_score > contradict_score * 1.3 and support_score > 0.5:
        verdict = "True"
        base_conf = int(45 + support_score * 12)
        raw_conf = min(92, base_conf + consensus_bonus + credible_bonus)
        reasoning = (
            f"The claim about {entity_str} is supported by evidence. "
            f"Verified against {supporting_sources} source(s) including {src_list}. "
        )
        if best_snippet:
            reasoning += f'Evidence confirms: "{best_snippet}" '
        if second_snippet and supporting_sources >= 2:
            reasoning += f'Further corroboration: "{second_snippet}" '
        elif not best_snippet:
            reasoning += f"Multiple sources confirm the assertion, matching key terms: [{kw_str}]."
    elif support_score > 0 and contradict_score > 0:
        verdict = "Partially True"
        raw_conf = min(72, int(30 + (support_score + contradict_score) * 6))
        reasoning = (
            f"The claim about {entity_str} is partially supported by evidence. "
            f"{supporting_sources} source(s) support aspects of the claim while "
            f"{contradicting_sources} source(s) contradict other parts. "
        )
        if best_snippet:
            reasoning += f'Key evidence: "{best_snippet}" '
        reasoning += (
            f"The mixed evidence suggests the claim contains both accurate and inaccurate elements. "
            f"Analyzed {len(relevant_sources)} relevant sources total."
        )
    elif support_score > 0.3:
        verdict = "True"
        base_conf = int(40 + support_score * 10)
        raw_conf = min(88, base_conf + consensus_bonus + credible_bonus)
        reasoning = (
            f"The claim about {entity_str} finds support in available evidence. "
            f"{len(relevant_sources)} source(s) contain information consistent with this assertion. "
        )
        if best_snippet:
            reasoning += f'Supporting evidence: "{best_snippet}" '
        reasoning += f"Matched key terms: [{kw_str}]."
    else:
        verdict = "Unverifiable"
        raw_conf = 30
        reasoning = (
            f"The claim '{claim[:80]}' could not be conclusively verified. "
            f"Found {len(relevant_sources)} sources mentioning {entity_str}, but none "
            f"explicitly confirm or deny this specific assertion. "
            f"Insufficient direct evidence exists to determine the accuracy of this claim."
        )

    # Hard quality gates: do not allow confident True verdicts from weak sources.
    if verdict == "True":
        if high_cred_supporting_sources == 0:
            verdict = "Unverifiable"
            raw_conf = min(raw_conf, 45)
            reasoning = (
                f"Found {supporting_sources} source(s) mentioning {entity_str}, but none "
                f"are from highly credible sources (Wikipedia, BBC, Reuters, etc.). "
                f"Cannot confidently verify without authoritative corroboration."
            )
        elif high_cred_contradicting_sources > 0 and contradict_score >= support_score * 0.7:
            verdict = "Partially True"
            raw_conf = min(raw_conf, 60)
            reasoning = (
                f"Credible sources provide mixed evidence about {entity_str}. "
                f"{high_cred_contradicting_sources} authoritative source(s) contradict aspects "
                f"of the claim while {high_cred_supporting_sources} support it."
            )
        elif low_cred_supporting_sources > high_cred_supporting_sources * 2 and high_cred_supporting_sources < 2:
            verdict = "Unverifiable"
            raw_conf = min(raw_conf, 50)
            reasoning = (
                f"Most sources supporting this claim about {entity_str} are from "
                f"low-credibility websites. Only {high_cred_supporting_sources} authoritative "
                f"source(s) corroborate it - insufficient for confident verification."
            )

    # ---- RL Reward-Model Scoring ----

    # 1. Evidence-verdict consistency reward
    consistency_reward = _evidence_verdict_consistency_reward(
        verdict, support_score, contradict_score,
        supporting_sources, contradicting_sources
    )

    # 2. Apply Platt calibration for raw confidence
    raw_normalized = raw_conf / 100.0
    calibrated_normalized = _platt_calibrate(raw_normalized)
    platt_conf = int(calibrated_normalized * 100)

    # 3. Combine: Platt base + consistency reward + diversity bonus
    confidence = platt_conf + int(consistency_reward) + int(diversity_bonus)

    # 4. Temporal decay: reduce confidence for time-sensitive claims
    if is_temporal:
        confidence = int(confidence * 0.85)  # 15% penalty for temporal uncertainty

    # Clamp final confidence
    confidence = max(5, min(97, confidence))

    # Append compound claim / specificity note if applicable
    if compound_note:
        reasoning += f" ⚠️ {compound_note}"

    # Append RL metadata (hidden from display, useful for debugging)
    reasoning += f" [RL Score: consistency={consistency_reward:+.0f}, diversity={diversity_bonus:+.0f}, Platt={raw_conf}→{platt_conf}]"

    # Append temporal caveat if applicable
    if is_temporal and temporal_caveat:
        reasoning += temporal_caveat

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
    }


# ============================================================
# Public API
# ============================================================

def extract_claims_local(text: str) -> list[str]:
    """Extract claims using local NLP (no LLM needed)."""
    return _extract_claims_nlp(text)


def generate_queries_local(claim: str) -> list[str]:
    """Generate search queries using local NLP (no LLM needed)."""
    return _generate_search_queries_nlp(claim)


def verify_claim_local(claim: str, evidence: list[dict]) -> dict:
    """Verify a claim against evidence using local NLP (no LLM needed)."""
    return _verify_claim_nlp(claim, evidence)
